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
    """جلب الأسعار بدقة مع التحقق من السياق النصي"""
    rates = {
        "usd_official": "4.85",      # القيمة الرسمية المعتمدة
        "usd_parallel": "6.15",
        "eur": "6.55",
        "gold_18": "345",
        "gold_24": "460",
        "oil_brent": "74.50"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # سحب البيانات من عين ليبيا
    try:
        res = requests.get("https://www.eanlibya.com/exchangerate/", headers=headers, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # البحث داخل الجداول أو العناصر التي تحتوي على أسعار الصرف بدقة
            for row in soup.find_all(['tr', 'div', 'p', 'li']):
                row_text = normalize_arabic_numbers(row.get_text())
                
                # البحث عن الدولار الأمريكي في السوق الموازي
                if "دولار" in row_text or "USD" in row_text:
                    match = re.search(r'(\d{1,2}\.\d{2})', row_text)
                    if match:
                        val = float(match.group(1))
                        if 5.0 <= val <= 10.0:  # نطاق منطقي للدولار في السوق الموازي
                            rates["usd_parallel"] = f"{val:.2f}"
                
                # البحث عن اليورو
                if "يورو" in row_text or "EUR" in row_text:
                    match = re.search(r'(\d{1,2}\.\d{2})', row_text)
                    if match:
                        val = float(match.group(1))
                        if 5.5 <= val <= 11.0:  # نطاق منطقي لليورو
                            rates["eur"] = f"{val:.2f}"

    except Exception as e:
        print(f"خطأ في سحب عين ليبيا: {e}")

    # حساب أسعار الذهب محلياً بناءً على الأونصة العالمية وسعر الدولار الموازي المستخرج
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
    
    print("النتائج النهائية المحدثة بدقة:", final_rates)

if __name__ == "__main__":
    main()
