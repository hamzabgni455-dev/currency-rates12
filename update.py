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

def scrape_ecolibya_exact_data():
    """استخراج البيانات بدقة مطابقة لموقع اقتصاد ليبيا (بدون يورو، مع برنت العالمي)"""
    rates = {
        "usd_official": "6.4277",
        "usd_parallel": "10.17",
        "gold_18": "602.54",
        "gold_24": "803.39",
        "oil_brent": "108.41"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        res = requests.get("https://ecolibya.com/", headers=headers, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            full_text = normalize_arabic_numbers(soup.get_text())

            # 1. استخراج السعر الرسمي للدولار
            match_off = re.search(r'الدولار الأمريكي.*?السعر الرسمي.*?(?:\d{2}/\d{2}/\d{4})?\s*(\d+\.\d{4})', full_text, re.DOTALL)
            if match_off:
                rates["usd_official"] = match_off.group(1)

            # 2. استخراج السوق الموازية للدولار
            match_par = re.search(r'السوق الموازية.*?(\d{1,2}\.\d{2})', full_text, re.DOTALL)
            if match_par:
                rates["usd_parallel"] = match_par.group(1)

            # 3. استخراج سعر الذهب للغرام (عيار 24)
            match_gold = re.search(r'الذهب.*?سعر الغرام.*?(\d{2,4}\.\d{2})', full_text, re.DOTALL)
            if match_gold:
                g24 = float(match_gold.group(1))
                rates["gold_24"] = f"{g24:.2f}"
                rates["gold_18"] = f"{g24 * (18/24):.2f}"

            # 4. استخراج خام برنت السعر العالمي
            match_brent = re.search(r'خام برنت.*?السعر العالمي.*?(\d{2,3}\.\d{2})', full_text, re.DOTALL)
            if match_brent:
                rates["oil_brent"] = match_brent.group(1)

    except Exception as e:
        print(f"خطأ أثناء سحب البيانات من اقتصاد ليبيا: {e}")

    return rates

def main():
    final_rates = scrape_ecolibya_exact_data()
    
    with open("rates.json", "w", encoding="utf-8") as f:
        json.dump(final_rates, f, ensure_ascii=False, indent=4)
    
    print("النتائج النهائية المحدثة:", final_rates)

if __name__ == "__main__":
    main()
