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
    
    # 1. السعر الرسمي
    try:
        res = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        if res.status_code == 200:
            rates = res.json().get("rates", {})
            lyd = rates.get("LYD")
            if lyd:
                data["usd_official"] = f"{lyd:.2f}"
    except Exception as e:
        print(f"خطأ في السعر الرسمي: {e}")

    # 2. سعر الذهب العالمي
    try:
        gold_res = requests.get("https://api.gold-api.com/price/XAU", timeout=10)
        if gold_res.status_code == 200:
            data["gold_24_usd"] = gold_res.json().get("price", 2300)
    except Exception as e:
        print(f"خطأ في الذهب العالمي: {e}")

    return data

def scrape_libyan_parallel_market():
    """سحب وقراءة أسعار السوق الموازي مع دعم الأرقام العربية الشرقية"""
    parallel_rates = {
        "usd_parallel": "6.15",
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
        
        for item in items[:10]:
            # تطبيع النص وتحويل الأرقام الشرقية إلى غربية لتسهيل القراءة
            title = normalize_arabic_numbers(item.title.text)
            
            # البحث عن سعر الدولار المنطقي في السوق (مثلاً بين 5 و 10 دينار)
            usd_match = re.search(r'(\d{1}\.\d{2})', title)
            if usd_match and parallel_rates["usd_parallel"] == "6.15":
                val = float(usd_match.group(1))
                if 5.0 < val < 10.0:  # نطاق منطقي لسعر الدولار في ليبيا
                    parallel_rates["usd_parallel"] = f"{val:.2f}"
                    
            eur_match = re.search(r'اليورو.*?(\d{1}\.\d{2})', title)
            if eur_match and parallel_rates["eur"] == "6.60":
                val_eur = float(eur_match.group(1))
                if 5.0 < val_eur < 12.0:
                    parallel_rates["eur"] = f"{val_eur:.2f}"
    except Exception as e:
        print(f"خطأ في السحب: {e}")

    return parallel_rates

def main():
    official_data = fetch_global_and_official_rates()
    parallel_data = scrape_libyan_parallel_market()

    # حساب أسعار الذهب محلياً بناءً على الأونصة وسعر الموازي
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
    except Exception:
        pass

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
    
    print("تم التحديث بنجاح:", final_rates)

if __name__ == "__main__":
    main()
