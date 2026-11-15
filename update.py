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

def scrape_ecolibya_rates():
    """جلب وتحليل الأسعار من موقع اقتصاد ليبيا"""
    rates = {
        "usd_official": "4.85",
        "usd_parallel": "10.25",  # القيمة الاحتياطية الآمنة
        "eur": "11.25",
        "gold_18": "576.5",
        "gold_24": "768.7",
        "oil_brent": "74.50"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        # سحب البيانات من موقع اقتصاد ليبيا
        res = requests.get("https://ecolibya.com/", headers=headers, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # البحث في عناوين المقالات والنصوص والفقرات عن أسعار الصرف
            for el in soup.find_all(['h1', 'h2', 'h3', 'p', 'span', 'div', 'td']):
                text = normalize_arabic_numbers(el.get_text())
                
                # البحث عن سعر الدولار ضمن النطاق المنطقي الحالي
                if "دولار" in text or "USD" in text:
                    match = re.search(r'(\d{1,2}\.\d{2,3})', text)
                    if match:
                        val = float(match.group(1))
                        if 9.00 <= val <= 13.00:
                            rates["usd_parallel"] = f"{val:.2f}"

                # البحث عن سعر اليورو
                if "يورو" in text or "EUR" in text:
                    match = re.search(r'(\d{1,2}\.\d{2,3})', text)
                    if match:
                        val = float(match.group(1))
                        if 10.00 <= val <= 14.00:
                            rates["eur"] = f"{val:.2f}"
                            
    except Exception as e:
        print(f"خطأ في السحب من موقع اقتصاد ليبيا: {e}")

    # السعر الرسمي من البنك المركزي العالمي
    try:
        res_cbl = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        if res_cbl.status_code == 200:
            data = res_cbl.json().get("rates", {})
            lyd = data.get("LYD")
            if lyd:
                rates["usd_official"] = f"{lyd:.2f}"
    except Exception as e:
        print(f"خطأ في السعر الرسمي: {e}")

    # حساب أسعار الذهب محلياً بناءً على الأونصة العالمية والدولار الموازي المستخرج
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
    final_rates = scrape_ecolibya_rates()
    
    with open("rates.json", "w", encoding="utf-8") as f:
        json.dump(final_rates, f, ensure_ascii=False, indent=4)
    
    print("النتائج النهائية المحدثة من اقتصاد ليبيا:", final_rates)

if __name__ == "__main__":
    main()
