# -*- coding: utf-8 -*-
import json
import os
import re
import requests
from bs4 import BeautifulSoup

OILPRICEAPI_KEY = os.environ.get("OILPRICEAPI_KEY")  # يُقرأ من متغير بيئة على جهازك، لا يُكتب هنا أبداً

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
    """
    يحسب سعر الذهب محلياً انطلاقاً من سعر الأونصة العالمية (gold-api.com)
    وسعر الدولار الموازي (usd_parallel) بناءً على اختيارك: كثير من صاغة
    الذهب في ليبيا يسعّرون فعلياً حسب الدولار الموازي لا الرسمي.
    """
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
    يجلب سعر برنت الحي من oilpriceapi.com باستخدام مفتاح API حقيقي
    (مسار /v1/prices/latest، وليس /v1/demo/prices التجريبي الثابت).
    المفتاح يُقرأ من متغير البيئة OILPRICEAPI_KEY فقط — لا تكتبه هنا.
    إن لم يوجد مفتاح، تبقى القيمة الافتراضية كما هي دون محاولة الاتصال.
    """
    if not OILPRICEAPI_KEY:
        print("تنويه: لم يُعثر على OILPRICEAPI_KEY في متغيرات البيئة؛ سيُستخدم سعر النفط الافتراضي الثابت.")
        return rates
    try:
        res = requests.get(
            "https://api.oilpriceapi.com/v1/prices/latest",
            params={"by_code": "BRENT_CRUDE_USD"},
            headers={"Authorization": f"Token {OILPRICEAPI_KEY}"},
            timeout=10,
        )
        res.raise_for_status()
        price = res.json()["data"]["price"]
        rates["oil_brent"] = f"{float(price):.2f}"
    except Exception as e:
        print(f"تعذر جلب سعر النفط: {e}")
    return rates


def scrape_libyan_rates():
    # قيم افتراضية تُستخدم فقط إذا فشل الاتصال بجميع المصادر (محدَّثة ومؤكدة بتاريخ 14-15 نوفمبر 2026)
    rates = {
        "usd_official": "6.3759",  # آخر قرار تخفيض من مصرف ليبيا المركزي (يناير 2026)؛
                                     # يتغير نادراً بقرار إداري ولا يُنشر يومياً، فحدّثه يدوياً
                                     # عند صدور قرار جديد من المركزي
        "usd_parallel": "10.175",
        "eur": "11.245",
        "gold_18": "603.8",
        "gold_24": "805.0",
        "oil_brent": "93.00",  # قيمة تقريبية وقت الكتابة؛ ستُستبدل بسعر حي إذا توفر OILPRICEAPI_KEY
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
