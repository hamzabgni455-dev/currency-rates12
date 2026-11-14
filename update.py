# -*- coding: utf-8 -*-
import json
import re
import requests
from bs4 import BeautifulSoup

def fetch_global_and_official_rates():
    """جلب السعر الرسمي للدولار والذهب العالمي من مصادر حية ومجانية"""
    data = {
        "usd_official": "4.85",
        "oil_brent": "74.50",
        "gold_24_usd": 2300
    }
    
    # 1. جلب السعر الرسمي للدينار الليبي مقابل الدولار
    try:
        res = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        if res.status_code == 200:
            rates = res.json().get("rates", {})
            lyd = rates.get("LYD")
            if lyd:
                data["usd_official"] = f"{lyd:.2f}"
    except Exception as e:
        print(f"خطأ في جلب السعر الرسمي: {e}")

    # 2. جلب سعر الذهب العالمي للأونصة بالدولار
    try:
        gold_res = requests.get("https://api.gold-api.com/price/XAU", timeout=10)
        if gold_res.status_code == 200:
            data["gold_24_usd"] = gold_res.json().get("price", 2300)
    except Exception as e:
        print(f"خطأ في جلب الذهب العالمي: {e}")

    return data

def scrape_libyan_parallel_market():
    """سحب أسعار السوق الموازي في ليبيا من العناوين الإخبارية"""
    parallel_rates = {
        "usd_parallel": "6.15",
        "eur": "6.60"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    search_url = "https://news.google.com/rss/search?q=أسعار+العملات+في+السوق+الموازي+ليبيا+اليوم&hl=ar&gl=LY&ceid=LY:ar"
    
    try:
        res = requests.get(search_url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, "xml")
        items = soup.find_all("item")
        
        for item in items[:5]:
            title = item.title.text
            usd_match = re.search(r'الدولار.*?(\d+\.\d{2})', title)
            if usd_match:
                parallel_rates["usd_parallel"] = usd_match.group(1)
                
            eur_match = re.search(r'اليورو.*?(\d+\.\d{2})', title)
            if eur_match:
                parallel_rates["eur"] = eur_match.group(1)
    except Exception as e:
        print(f"خطأ في سحب السوق الموازي: {e}")

    return parallel_rates

def main():
    official_data = fetch_global_and_official_rates()
    parallel_data = scrape_libyan_parallel_market()

    # حساب سعر غرام الذهب عيار 24 و 18 بالدينار الليبي تلقائياً
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
    
    print("تم إنشاء وتحديث rates.json بنجاح:", final_rates)

if __name__ == "__main__":
    main()
