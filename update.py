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

def scrape_libyan_rates():
    """جلب الأسعار مباشرة من مصادر السوق والبنك المركزي"""
    rates = {
        "usd_official": "4.85",
        "usd_parallel": "6.15",
        "eur": "6.60",
        "gold_18": "345",
        "gold_24": "460",
        "oil_brent": "74.50"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # 1. محاولة سحب السعر من عين ليبيا (أسعار الصرف)
    try:
        res = requests.get("https://www.eanlibya.com/exchangerate/", headers=headers, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            text_content = normalize_arabic_numbers(soup.get_text())
            
            # البحث عن سعر الدولار في الصفحة
            usd_match = re.search(r'الدولار.*?(\d{1,2}\.\d{2})', text_content)
            if usd_match:
                val = float(usd_match.group(1))
                if 5.0 <= val <= 10.0:
                    rates["usd_parallel"] = f"{val:.2f}"
                    print(from_ean := f"تم سحب سعر الدولار الموازي من عين ليبيا: {rates['usd_parallel']}")

            # البحث عن سعر اليورو
            eur_match = re.search(r'اليورو.*?(\d{1,2}\.\d{2})', text_content)
            if eur_match:
                val_eur = float(eur_match.group(1))
                if 5.0 <= val_eur <= 12.0:
                    rates["eur"] = f"{val_eur:.2f}"
    except Exception as e:
        print(f"خطأ في سحب عين ليبيا: {e}")

    # 2. سحب السعر الرسمي من مصرف ليبيا المركزي (أو API بديل موثوق يعكسه)
    try:
        res_cbl = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        if res_cbl.status_code == 200:
            data = res_cbl.json().get("rates", {})
            lyd = data.get("LYD")
            if lyd:
                rates["usd_official"] = f"{lyd:.2f}"
    except Exception as e:
        print(f"خطأ في السعر الرسمي: {e}")

    # 3. حساب أسعار الذهب محلياً بناءً على الأونصة العالمية وسعر الدولار الموازي المستخرج
    try:
        gold_res = requests.get("https://api.gold-api.com/price/XAU", timeout=10)
        if gold_res.status_code == 200:
            ounce_usd = float(gold_res.json().get("price", 2300))
            usd_p = float(rates["usd_parallel"])
            if usd_p > 0 and ounce_usd > 0:
                gram_24 = (ounce_usd / 31.1035) * usd_p
                gram_18 = gram_24 * (18 / 24)
                rates["gold_24"] = f"{gram_24:.1f}"
                rates["gold_18"] = f"{gram_18:.1f}"
    except Exception as e:
        print(f"خطأ في حساب الذهب: {e}")

    return rates

def main():
    final_rates = scrape_libyan_rates()
    
    with open("rates.json", "w", encoding="utf-8") as f:
        json.dump(final_rates, f, ensure_ascii=False, indent=4)
    
    print("النتائج النهائية المحدثة:", final_rates)

if __name__ == "__main__":
    main()
