import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo

def fetch_page_text(url, headers):
    """دالة مساعدة لجلب نص الصفحة مع التعامل مع الترميز"""
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        if not response.encoding or response.encoding.lower() in ('iso-8859-1', 'ascii'):
            response.encoding = response.apparent_encoding or 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        for tag in soup(['script', 'style', 'noscript']):
            tag.decompose()
        return soup.get_text(separator='\n')
    except Exception as e:
        print(f"خطأ في جلب {url}: {e}")
        return None

def scrape_market_rates_multi_source():
    """جلب الأسعار من مصادر بديلة متعددة مع إبقاء نفس مفاتيح rates.json"""
    rates = {
        "usd_official": "6.4700",   # قيمة احتياطية
        "usd_parallel": "10.6500",
        "tnd": "2.11",              # من نفس مصدر السوق الرسمي
        "egp": "0.1203",            # قيمة احتياطية
        "gold_18": "565.80",
        "gold_24": "754.40",
        "oil_brent": "108.41",      # قيمة احتياطية
        "last_update": "",
        "status": "ثابتة",
        "matched_fields": 0
    }

    libya_tz = ZoneInfo("Africa/Tripoli")
    rates["last_update"] = datetime.now(libya_tz).strftime("%Y-%m-%d %H:%M")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
    }

    matched = 0

    # 1. جلب سعر السوق الموازي من مقال حديث في alwasat.ly
    try:
        # استخدام مقال بتاريخ 2026-11-18 (أحدث مقال متاح في البحث)
        url_parallel = "https://alwasat.ly/news/485524"
        txt = fetch_page_text(url_parallel, headers)
        if txt:
            # البحث عن النمط: "سجل 10.65 دينار" (السعر الموازي)
            # نأخذ أول ظهور لرقم عشري يتبع كلمة "سجل" أو "دينار" في سياق السوق الموازي
            match = re.search(r'سجل\s+(\d{1,2}\.\d{2})\s+دينار', txt)
            if not match:
                # نمط بديل: "الدولار ... 10.65 دينار"
                match = re.search(r'الدولار[^.]*?(\d{1,2}\.\d{2})\s+دينار', txt)
            if match:
                val = float(match.group(1))
                if 5.0 < val < 20.0:  # نطاق منطقي
                    rates["usd_parallel"] = f"{val:.2f}"
                    matched += 1
    except Exception as e:
        print("تعذر جلب السوق الموازي:", e)

    # 2. جلب سعر السوق الرسمي من مقال حديث في alwasat.ly (بيانات مصرف ليبيا المركزي)
    try:
        # استخدام مقال بتاريخ 2026-11-19 (أحدث مقال متاح)
        url_official = "https://alwasat.ly/news/485571"
        txt = fetch_page_text(url_official, headers)
        if txt:
            # نمط: "ارتفع سعر الدولار ... إلى 6.47 دينار"
            match = re.search(r'الدولار[^.]*?(\d+\.\d{2})\s+دينار', txt)
            if match:
                val = float(match.group(1))
                if 4.0 < val < 10.0:  # النطاق الرسمي المنطقي
                    rates["usd_official"] = f"{val:.4f}"
                    matched += 1
            # محاولة استخراج سعر الدينار التونسي من نفس المقال (لأنه مذكور)
            match_tnd = re.search(r'الدينار\s+التونسي[^.]*?(\d+\.\d{2})\s+دينار', txt)
            if match_tnd:
                val_tnd = float(match_tnd.group(1))
                if 1.0 < val_tnd < 5.0:
                    rates["tnd"] = f"{val_tnd:.2f}"
                    # لا نزيد matched هنا لتجنب التضخيم، لكن يمكننا ذلك
                    # matched += 1
    except Exception as e:
        print("تعذر جلب السوق الرسمي:", e)

    # 3. جلب أسعار الذهب (عيار 24 و18) من exchange-rates.org
    try:
        url_gold = "https://www.exchange-rates.org/fr/metaux-precieux/or/libye"
        txt = fetch_page_text(url_gold, headers)
        if txt:
            # نمط عيار 24: "Prix de l'or 24K par gramme | 754,40 LYD"
            match_24 = re.search(r'24K\s+par\s+gramme\s*\|\s*([\d\s,]+)\s*LYD', txt, re.IGNORECASE)
            if match_24:
                raw = match_24.group(1).replace(' ', '').replace(',', '.')
                try:
                    val_24 = float(raw)
                    if 200 < val_24 < 2000:  # نطاق منطقي لسعر الجرام بالدينار
                        rates["gold_24"] = f"{val_24:.2f}"
                        matched += 1
                except ValueError:
                    pass

            # نمط عيار 18: "Prix de l'or 18K par gramme | 565,80 LYD"
            match_18 = re.search(r'18K\s+par\s+gramme\s*\|\s*([\d\s,]+)\s*LYD', txt, re.IGNORECASE)
            if match_18:
                raw = match_18.group(1).replace(' ', '').replace(',', '.')
                try:
                    val_18 = float(raw)
                    if 150 < val_18 < 1500:
                        rates["gold_18"] = f"{val_18:.2f}"
                        matched += 1
                except ValueError:
                    pass
    except Exception as e:
        print("تعذر جلب أسعار الذهب:", e)

    # إذا لم يتم العثور على عيار 18، نحسبه من عيار 24
    if rates["gold_18"] == "565.80" and rates["gold_24"] != "754.40":
        try:
            calculated = float(rates["gold_24"]) * (18.0 / 24.0)
            rates["gold_18"] = f"{calculated:.2f}"
        except:
            pass

    rates["matched_fields"] = matched
    rates["status"] = "محدث" if matched > 0 else "ثابتة"
    print("Matched fields:", matched)
    return rates
