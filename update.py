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
    rates = {
        "usd_official": "4.85",
        "usd_parallel": "10.25",
        "eur": "11.25",
        "gold_18": "576.5",
        "gold_24": "768.7",
        "oil_brent": "74.50"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        res = requests.get("https://www.eanlibya.com/exchangerate/", headers=headers, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for el in soup.find_all(['td', 'span', 'strong', 'div', 'p']):
                text = normalize_arabic_numbers(el.get_text())
                
                # البحث عن الدولار
                if "دولار" in text or "USD" in text:
                    match = re.search(r'(\d{1,2}\.\d{2,3})', text)
                    if match:
                        val = float(match.group(1))
                        if 9.00 <= val <= 13.00:
                            rates["usd_parallel"] = f"{val:.2f}"

                # البحث عن اليورو (مع اشتراط أن يكون مختلفاً عن الدولار وأعلى منه بقليل)
                if "يورو" in text or "EUR" in text:
                    match = re.search(r'(\d{1,2}\.\d{2,3})', text)
                    if match:
                        val = float(match.group(1))
                        if 10.00 <= val <= 14.00:
                            rates["eur"] = f"{val:.2f}"
    except Exception as e:
        print(f"خطأ في السحب: {e}")

    # حساب أسعار الذهب محلياً بناءً على الأونصة العالمية والدولار الموازي
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

    rates["oil_brent"] = "74.50"
    return rates

def main():
    final_rates = scrape_libyan_rates()
    with open("rates.json", "w", encoding="utf-8") as f:
        json.dump(final_rates, f, ensure_ascii=False, indent=4)
    print("النتائج النهائية المحدثة:", final_rates)

if __name__ == "__main__":
    main()
