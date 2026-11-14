# -*- coding: utf-8 -*-
import json
import re
import requests
from bs4 import BeautifulSoup

def normalize_arabic_numbers(text):
    """تحويل الأرقام العربية الشرقية (٠-٩) إلى أرقام إنجليزية وتوحيد الفواصل"""
    if not text:
        return ""
    arabic_nums = "٠١٢٣٤٥٦٧٨٩"
    english_nums = "0123456789"
    trans = str.maketrans(arabic_nums, english_nums)
    text = text.translate(trans)
    text = text.replace("٫", ".").replace(",", ".")
    return text

def fetch_global_and_official_rates():
    """جلب السعر الرسمي للدولار والذهب العالمي من مصادر موثوقة وحية"""
    data = {
        "usd_official": "4.85",
        "oil_brent": "74.50",
        "gold_24_usd": 2300
    }
    
    # 1. السعر الرسمي من المصارف العالمية
    try:
        res = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        if res.status_code == 200:
            rates = res.json().get("rates", {})
            lyd = rates.get("LYD")
            if lyd:
                data["usd_official"] = f"{lyd:.2f}"
    except Exception as e:
        print(f"خطأ في السعر الرسمي: {e}")

    # 2. سعر الذهب العالمي للأونصة
    try:
        gold_res = requests.get("https://api.gold-api.com/price/XAU", timeout=10)
        if gold_res.status_code == 200:
            data["gold_24_usd"] = gold_res.json().get("price", 2300)
    except Exception as e:
        print(f"خطأ في الذهب العالمي: {e}")

    return data

def scrape_libyan_parallel_market():
    """سحب وقراءة أسعار السوق الموازي مع طباعة العناوين للتشخيص"""
    parallel_rates = {
        "usd_parallel": "6.15", # قيمة احتياطية منطقية
        "eur": "6.60"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    search_url = "https://news.google.com/rss/search?q=سعر+الدولار+السوق+الموازي+ليبيا+اليوم&hl=ar&gl=LY&ceid=LY:ar"
    
    try:
        res = requests.get(search_url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, "xml")
        items = soup.find_all("item")
        print(f"--- تم العثور على {len(items)} خبراً في البحث ---")
        
        for item in items[:10]:
            raw_title = item.title.text
            title = normalize_arabic_numbers(raw_title)
            print(f"-> فحص العنوان: {title}")
            
            # البحث عن أي رقم عشري يقع ضمن النطاق المنطقي لسعر الدولار في ليبيا (بين 5.00 و 10.00)
            matches = re.findall(r'(\d{1,2}\.\d{1,2})', title)
            for match in matches:
                val = float(match)
                if 5.0 <= val <= 10.0:
                    parallel_rates["usd_parallel"] = f"{val:.2f}"
                    print(f"*** تم العثور على سعر دولار موازي مقبول: {parallel_rates['usd_parallel']} ***")
                    break
            else:
                continue
            break
            
    except Exception as e:
        print(f"خطأ في عملية السحب: {e}")

    return parallel_rates

def main():
    official_data = fetch_global_and_official_rates()
    parallel_data = scrape_libyan_parallel_market()

    # حساب أسعار الذهب محلياً بناءً على الأونصة وسعر الموازي المستخرج
    gold_24_lyd = "460"
    gold_18_lyd = "345"
    
    try:
        usd_p = float(parallel_data["usd_parallel"])
        ounce_usd = float(official_data["gold_24_usd"])
        if usd_p > 0 and ounce_usd > 0:
            gram_24 = (ounce_usd / 31.1035) * usd_p
            gram_18 = gram_24 * (18 / 24)
            gold_24_lyd = f"{gram_24:.1f}"
            gold_18_lyd = f"{gram_18:.1f}"
    except Exception as e:
        print(f"خطأ في حساب الذهب: {e}")

    final_rates = {
        "usd_official": official_data["usd_official"],
        "usd_parallel": parallel_data["usd_parallel"],
        "eur": parallel_data["eur"],
        "gold_18": gold_18_lyd,
        "gold_24": gold_24_lyd,
        "oil_brent": "74.50"
    }

    with open("rates.json", "w", encoding="utf-8") as f:
        json.dump(final_rates, f, ensure_ascii=False, indent=4)
    
    print("النتيجة النهائية المحفوظة في rates.json:", final_rates)

if __name__ == "__main__":
    main()
