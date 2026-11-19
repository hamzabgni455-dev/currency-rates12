from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup
import re

def normalize_arabic_numbers(text):
    """تحويل الأرقام العربية إلى إنجليزية (اختياري)"""
    arabic_to_english = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
    return text.translate(arabic_to_english)

def extract_near(text, anchor_pattern, value_pattern, window=120):
    """استخراج قيمة رقمية قريبة من نمط مرجعي"""
    match = re.search(anchor_pattern, text, re.IGNORECASE)
    if not match:
        return None
    start = max(0, match.start() - window)
    end = min(len(text), match.end() + window)
    segment = text[start:end]
    value_match = re.search(value_pattern, segment)
    if value_match:
        return value_match.group(1)
    return None

def scrape_market_rates_multi_source():
    """جلب الأسعار من مصادر بديلة متعددة مع إبقاء نفس مفاتيح rates.json"""
    rates = {
        "usd_official": "6.4277",   # قيمة احتياطية مبدئية
        "usd_parallel": "10.17",
        "tnd": "3.25",
        "egp": "0.1203",
        "gold_18": "602.54",
        "gold_24": "803.39",
        "oil_brent": "108.41",
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
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache"
    }

    matched = 0

    # 1. الدولار الرسمي: مصرف ليبيا المركزي (cbl.gov.ly) مع احتياطي من ncb.ly
    official_fetched = False
    try:
        res_cbl = requests.get("https://cbl.gov.ly/currency-exchange-rates/", headers=headers, timeout=20)
        res_cbl.raise_for_status()
        if not res_cbl.encoding or res_cbl.encoding.lower() == "iso-8859-1":
            res_cbl.encoding = res_cbl.apparent_encoding or "utf-8"

        soup_cbl = BeautifulSoup(res_cbl.text, "html.parser")
        for tag in soup_cbl(["script", "style", "noscript"]):
            tag.decompose()
        txt_cbl = normalize_arabic_numbers(soup_cbl.get_text(separator="\n"))

        # البحث عن سعر الدولار (غالباً يظهر كـ "الدولار الأمريكي" ثم رقم مثل 6.xxxx)
        val_off = extract_near(
            txt_cbl,
            r"الدولار\s*الأمريكي",
            r"\b(\d+\.\d{2,4})\b",
            window=150
        )
        if val_off:
            # التحقق من منطقية القيمة (النطاق الرسمي تقريباً بين 5 و 8)
            f_val = float(val_off)
            if 4.0 < f_val < 10.0:
                rates["usd_official"] = f"{f_val:.4f}"
                matched += 1
                official_fetched = True
    except Exception as e:
        print("تعذر جلب الدولار الرسمي من المركزي:", e)

    # مصدر احتياطي للدولار الرسمي من المصرف التجاري الوطني (ncb.ly)
    if not official_fetched:
        try:
            res_ncb = requests.get("https://www.ncb.ly/", headers=headers, timeout=15)
            res_ncb.raise_for_status()
            res_ncb.encoding = res_ncb.apparent_encoding or "utf-8"
            soup_ncb = BeautifulSoup(res_ncb.text, "html.parser")
            txt_ncb = normalize_arabic_numbers(soup_ncb.get_text(separator="\n"))
            # البحث عن نمط "الدولار الأمريكي" متبوعاً بسعر الشراء أو البيع
            val_ncb = extract_near(
                txt_ncb,
                r"الدولار\s*الأمريكي",
                r"(\d+\.\d{3,4})",
                window=100
            )
            if val_ncb:
                f_val = float(val_ncb)
                if 4.0 < f_val < 10.0:
                    rates["usd_official"] = f"{f_val:.4f}"
                    matched += 1
        except Exception as e:
            print("تعذر جلب الدولار الرسمي من NCB:", e)

    # 2. السوق الموازية للدولار من عين ليبيا (eanlibya.com)
    try:
        res_ean = requests.get("https://www.eanlibya.com/exchangerate/", headers=headers, timeout=20)
        res_ean.raise_for_status()
        if not res_ean.encoding or res_ean.encoding.lower() == "iso-8859-1":
            res_ean.encoding = res_ean.apparent_encoding or "utf-8"

        soup_ean = BeautifulSoup(res_ean.text, "html.parser")
        for tag in soup_ean(["script", "style", "noscript"]):
            tag.decompose()
        txt_ean = normalize_arabic_numbers(soup_ean.get_text(separator="\n"))

        # في صفحة eanlibya يظهر السعر مباشرة بعد كلمة "الدولار" في جدول السوق الموازي
        val_par = extract_near(
            txt_ean,
            r"الدولار",
            r"\b(\d{1,2}\.\d{2})\b",
            window=80
        )
        if val_par:
            f_val = float(val_par)
            # التحقق من منطقية سعر السوق الموازي (عادة أعلى من الرسمي)
            if f_val > 5.0:
                rates["usd_parallel"] = f_val
                matched += 1
    except Exception as e:
        print("تعذر جلب السوق الموازية:", e)

    # 3. الذهب في ليبيا (عيار 24 وعيار 18) من golden-meter.com
    try:
        res_gold = requests.get("https://golden-meter.com/gold-price/libya", headers=headers, timeout=20)
        res_gold.raise_for_status()
        if not res_gold.encoding or res_gold.encoding.lower() == "iso-8859-1":
            res_gold.encoding = res_gold.apparent_encoding or "utf-8"

        soup_gold = BeautifulSoup(res_gold.text, "html.parser")
        for tag in soup_gold(["script", "style", "noscript"]):
            tag.decompose()
        txt_gold = normalize_arabic_numbers(soup_gold.get_text(separator="\n"))

        # استخراج سعر عيار 24: يظهر كـ "عيار 24 ... 831.484 د.ل"
        val_g24 = extract_near(
            txt_gold,
            r"عيار\s*24",
            r"(\d{3}\.\d{3})",
            window=60
        )
        if val_g24:
            f_g24 = float(val_g24)
            if 200 < f_g24 < 2000:  # نطاق منطقي لسعر الجرام بالدينار الليبي
                rates["gold_24"] = f"{f_g24:.2f}"
                matched += 1

        # استخراج سعر عيار 18: يظهر كـ "عيار 18 ... 623.613 د.ل"
        val_g18 = extract_near(
            txt_gold,
            r"عيار\s*18",
            r"(\d{3}\.\d{3})",
            window=60
        )
        if val_g18:
            f_g18 = float(val_g18)
            if 150 < f_g18 < 1500:
                rates["gold_18"] = f"{f_g18:.2f}"
                matched += 1
        elif val_g24:
            # إذا لم يتم العثور على عيار 18، يتم حسابه من عيار 24
            f_g18_calc = float(val_g24) * (18.0 / 24.0)
            rates["gold_18"] = f"{f_g18_calc:.2f}"

    except Exception as e:
        print("تعذر جلب أسعار الذهب:", e)

    rates["matched_fields"] = matched
    rates["status"] = "محدث" if matched > 0 else "ثابتة"
    print("Matched fields:", matched)
    return rates
