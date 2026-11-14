# -*- coding: utf-8 -*-
import json
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def normalize_arabic_numbers(text):
    """تحويل الأرقام العربية الشرقية (٠-٩) إلى أرقام إنجليزية وتوحيد الفاصلة العشرية"""
    if not text:
        return ""
    arabic_nums = "٠١٢٣٤٥٦٧٨٩"
    english_nums = "0123456789"
    text = text.translate(str.maketrans(arabic_nums, english_nums))
    return text.replace("٫", ".")


def extract_price(cell_text):
    """يستخرج أول رقم عشري/صحيح من نص الخلية بعد التطبيع"""
    text = normalize_arabic_numbers(cell_text)
    match = re.search(r"\d+(\.\d+)?", text)
    return float(match.group()) if match else None


def scrape_parallel_market(rates):
    """
    يجلب أسعار السوق الموازي من عين ليبيا بالاعتماد على بنية الجدول نفسه
    (اسم العملة في الصف + آخر خلية = السعر) بدل نطاقات أرقام ثابتة.
    النطاقات الثابتة في الكود الأصلي (5.0-10.0 للدولار، 5.5-11.0 لليورو) كانت
    السبب الرئيسي في فشل الجلب: السعر الحالي للدولار تجاوز 10 دنانير فعلياً،
    فكان الفلتر يرفضه ويُبقي القيمة الافتراضية القديمة.
    """
    currency_map = {
        "الدولار": "usd_parallel",
        "اليورو": "eur",
    }
    try:
        res = requests.get("https://www.eanlibya.com/exchangerate/", headers=HEADERS, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            row_text = row.get_text(" ", strip=True)
            price = extract_price(cells[-1].get_text(strip=True))
            if price is None:
                continue
            for currency_name, key in currency_map.items():
                if currency_name in row_text:
                    rates[key] = f"{price:.3f}"
    except Exception as e:
        print(f"تعذر جلب أسعار السوق الموازي: {e}")
    return rates


def scrape_gold(rates):
    """يحسب سعر الذهب محلياً انطلاقاً من سعر الأونصة العالمية (gold-api.com) وسعر الدولار الموازي المستخرج أعلاه"""
    try:
        res = requests.get("https://api.gold-api.com/price/XAU", timeout=10)
        res.raise_for_status()
        ounce_usd = float(res.json()["price"])
        usd_p = float(rates["usd_parallel"])
        gram_24 = (ounce_usd / 31.1035) * usd_p
        gram_18 = gram_24 * (18 / 24)
        rates["gold_24"] = f"{gram_24:.1f}"
        rates["gold_18"] = f"{gram_18:.1f}"
    except Exception as e:
        print(f"تعذر حساب سعر الذهب: {e}")
    return rates


def scrape_oil(rates):
    """
    يجلب سعر برنت من نقطة نهاية تجريبية (demo) مجانية بلا مفتاح API.
    تنويه: هذه نقطة تجريبية وقد لا تعكس السعر اللحظي الدقيق. للحصول على
    سعر حي ودقيق يفضَّل إنشاء حساب مجاني في oilpriceapi.com والحصول على
    مفتاح API واستخدام مسار /v1/prices/latest بدلاً من /v1/demo/prices.
    """
    try:
        res = requests.get("https://api.oilpriceapi.com/v1/demo/prices", timeout=10)
        res.raise_for_status()
        for p in res.json().get("data", {}).get("prices", []):
            if p.get("code") == "BRENT_CRUDE_USD":
                rates["oil_brent"] = f"{float(p['price']):.2f}"
                break
    except Exception as e:
        print(f"تعذر جلب سعر النفط: {e}")
    return rates


def scrape_libyan_rates():
    # قيم افتراضية تُستخدم فقط إذا فشل الاتصال بجميع المصادر
    rates = {
        "usd_official": "6.40",   # ملاحظة: السعر الرسمي يحدَّد إدارياً من مصرف ليبيا
                                   # المركزي ولا يُنشر على صفحة يمكن سحبها يومياً بشكل
                                   # موثوق؛ يبقى ثابتاً هنا إلى أن تُحدّثه يدوياً عند
                                   # صدور قرار جديد من المركزي
        "usd_parallel": "10.20",
        "eur": "11.25",
        "gold_18": "345",
        "gold_24": "460",
        "oil_brent": "74.50",
    }
    rates = scrape_parallel_market(rates)
    rates = scrape_gold(rates)
    rates = scrape_oil(rates)
    return rates


def main():
    final_rates = scrape_libyan_rates()
    with open("rates.json", "w", encoding="utf-8") as f:
        json.dump(final_rates, f, ensure_ascii=False, indent=4)
    print("النتائج النهائية المحدثة:", final_rates)


if __name__ == "__main__":
    main()
