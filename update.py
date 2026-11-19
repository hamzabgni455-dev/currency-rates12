import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo


def _get_json(url, headers=None, timeout=20):
    r = requests.get(url, headers=headers or {}, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _yahoo_price(symbol, headers):
    """سعر لحظي من Yahoo Finance (قد يفشل بدون كوكيز/crumb)"""
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        f"?interval=1d&range=1d"
    )
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            print(f"[yahoo:{symbol}] رمز استجابة غير متوقع: {r.status_code}")
            return None
        data = r.json()
    except Exception as e:
        print(f"[yahoo:{symbol}] فشل الطلب: {e}")
        return None

    result = data.get("chart", {}).get("result")
    if not result:
        err = data.get("chart", {}).get("error")
        print(f"[yahoo:{symbol}] لا توجد نتائج. error={err}")
        return None
    price = result[0].get("meta", {}).get("regularMarketPrice")
    if price is None:
        print(f"[yahoo:{symbol}] السعر غير موجود في meta")
    return price


def _stooq_price(symbol, headers):
    """بديل مستقر عن Yahoo: أسعار من stooq.com (CSV بسيط، بدون كوكيز خاصة)"""
    url = f"https://stooq.com/q/l/?s={symbol}&f=sd2t2ohlcv&h&e=csv"
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        lines = r.text.strip().splitlines()
        if len(lines) < 2:
            print(f"[stooq:{symbol}] لا توجد بيانات في الرد")
            return None
        fields = lines[1].split(",")
        # Symbol,Date,Time,Open,High,Low,Close,Volume
        close = fields[6]
        if close in ("N/D", ""):
            print(f"[stooq:{symbol}] القيمة غير متوفرة (N/D)")
            return None
        return float(close)
    except Exception as e:
        print(f"[stooq:{symbol}] فشل: {e}")
        return None


def _price_with_fallback(yahoo_symbol, stooq_symbol, headers, label):
    """يجرب Yahoo أولاً، وإذا فشل يجرب stooq"""
    price = _yahoo_price(yahoo_symbol, headers)
    if price is not None:
        print(f"[{label}] من Yahoo: {price}")
        return price
    price = _stooq_price(stooq_symbol, headers)
    if price is not None:
        print(f"[{label}] من stooq (بديل): {price}")
        return price
    print(f"[{label}] فشل من كل المصادر، سيُستخدم القيمة الثابتة")
    return None


def scrape_market_rates_multi_source():
    rates = {
        "usd_official": "6.4277",
        "usd_parallel": "10.17",
        "tnd": "3.25",
        "egp": "0.1203",
        "gold_18": "602.54",
        "gold_24": "803.39",
        "oil_brent": "108.41",
        "last_update": "",
        "status": "ثابتة",
        "matched_fields": 0,
    }

    libya_tz = ZoneInfo("Africa/Tripoli")
    rates["last_update"] = datetime.now(libya_tz).strftime("%Y-%m-%d %H:%M")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
        "Accept": "*/*",
        "Referer": "https://finance.yahoo.com/",
    }

    matched = 0

    # ========== 1) العملات الرسمية من API مجاني ==========
    try:
        data = _get_json(
            "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json",
            headers,
        )
        usd = data.get("usd", {})

        if usd.get("lyd") and 2.0 < float(usd["lyd"]) < 20.0:
            rates["usd_official"] = f"{float(usd['lyd']):.4f}"
            matched += 1
            print(f"[رسمي] USD/LYD = {rates['usd_official']}")
        else:
            print("[رسمي] قيمة lyd غير موجودة أو خارج النطاق المتوقع")

        if usd.get("tnd") and float(usd["tnd"]) > 0:
            rates["tnd"] = f"{1.0 / float(usd['tnd']):.4f}"
            matched += 1

        if usd.get("egp") and float(usd["egp"]) > 0:
            rates["egp"] = f"{1.0 / float(usd['egp']):.4f}"
            matched += 1
    except Exception as e:
        print(f"[رسمي] تعذر (المصدر الأساسي): {e}")
        # مصدر احتياطي لنفس الـ API (جافاسكريبت ديلفري أحياناً يحجب)
        try:
            data = _get_json(
                "https://latest.currency-api.pages.dev/v1/currencies/usd.json",
                headers,
            )
            usd = data.get("usd", {})
            if usd.get("lyd") and 2.0 < float(usd["lyd"]) < 20.0:
                rates["usd_official"] = f"{float(usd['lyd']):.4f}"
                matched += 1
                print(f"[رسمي-بديل] USD/LYD = {rates['usd_official']}")
        except Exception as e2:
            print(f"[رسمي] تعذر المصدر البديل أيضاً: {e2}")

    # ========== 2) النفط برنت: Yahoo ثم stooq كبديل ==========
    oil = _price_with_fallback("BZ=F", "cb.f", headers, "برنت")
    if oil and 20.0 < oil < 300.0:
        rates["oil_brent"] = f"{oil:.2f}"
        matched += 1

    # ========== 3) الذهب: Yahoo ثم stooq، ثم نحوله للدينار الليبي ==========
    # يُحسب على أساس سعر الدولار الموازي (وليس الرسمي) حسب الطلب السابق
    gold_oz = _price_with_fallback("GC=F", "xauusd", headers, "ذهب")
    if gold_oz and 1000.0 < gold_oz < 5000.0:
        usd_lyd_parallel = float(rates["usd_parallel"])
        gold_24 = (gold_oz / 31.1035) * usd_lyd_parallel
        rates["gold_24"] = f"{gold_24:.2f}"
        rates["gold_18"] = f"{gold_24 * (18.0 / 24.0):.2f}"
        matched += 2
        print(
            f"[ذهب] أونصة={gold_oz:.2f}$ (×سعر الموازي {usd_lyd_parallel}) → "
            f"ع24={rates['gold_24']} / ع18={rates['gold_18']}"
        )

    # ========== 4) السوق الموازي (eanlibya) ==========
    if _try_parallel_eanlibya(rates, headers):
        matched += 1

    rates["matched_fields"] = matched
    rates["status"] = "محدث" if matched > 0 else "ثابتة"
    print(f"[النتيجة] الحقول المطابقة: {matched}/8")
    return rates


def _try_parallel_eanlibya(rates, headers):
    """محاولة استخراج سعر الدولار الموازي من eanlibya"""
    try:
        r = requests.get(
            "https://www.eanlibya.com/exchangerate/",
            headers=headers,
            timeout=20,
        )
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        for t in soup(["script", "style", "noscript"]):
            t.decompose()
        txt = soup.get_text(separator="\n")

        patterns = [
            r"الدولار\s*الأمريكي[^\d]{0,80}(\d{1,2}\.\d{2})",
            r"USD[^\d]{0,80}(\d{1,2}\.\d{2})",
            r"(\d{1,2}\.\d{2})\s*دينار",
        ]
        for pat in patterns:
            m = re.search(pat, txt)
            if m:
                v = float(m.group(1))
                if 5.0 < v < 30.0:
                    rates["usd_parallel"] = f"{v:.2f}"
                    print(f"[موازي] {v:.2f} LYD/USD")
                    return True
        print("[موازي] لم يُطابق أي نمط regex مع نص الصفحة — ربما تغيّر تصميم الموقع")
    except Exception as e:
        print(f"[موازي] تعذر: {e}")
    return False


if __name__ == "__main__":
    result = scrape_market_rates_multi_source()
    print("\n--- النتيجة النهائية ---")
    for k, v in result.items():
        print(f"{k}: {v}")
