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
    """سعر لحظي من Yahoo Finance"""
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        f"?interval=1d&range=1d"
    )
    data = _get_json(url, headers)
    result = data.get("chart", {}).get("result", [])
    if not result:
        return None
    return result[0].get("meta", {}).get("regularMarketPrice")


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

        if usd.get("tnd") and float(usd["tnd"]) > 0:
            # tnd هو: كم TND لكل 1 USD → نعكسها
            rates["tnd"] = f"{1.0 / float(usd['tnd']):.4f}"
            matched += 1

        if usd.get("egp") and float(usd["egp"]) > 0:
            rates["egp"] = f"{1.0 / float(usd['egp']):.4f}"
            matched += 1
    except Exception as e:
        print(f"[رسمي] تعذر: {e}")

    # ========== 2) النفط برنت من Yahoo Finance ==========
    try:
        oil = _yahoo_price("BZ=F", headers)
        if oil and 20.0 < oil < 300.0:
            rates["oil_brent"] = f"{oil:.2f}"
            matched += 1
            print(f"[برنت] {oil:.2f} USD")
    except Exception as e:
        print(f"[برنت] تعذر: {e}")

    # ========== 3) الذهب: من Yahoo ثم نحوله للدينار الليبي ==========
    try:
        gold_oz = _yahoo_price("GC=F", headers)
        if gold_oz and 1000.0 < gold_oz < 5000.0:
            usd_lyd = float(rates["usd_official"])
            gold_24 = (gold_oz / 31.1035) * usd_lyd
            rates["gold_24"] = f"{gold_24:.2f}"
            rates["gold_18"] = f"{gold_24 * (18.0 / 24.0):.2f}"
            matched += 2
            print(
                f"[ذهب] أونصة={gold_oz:.2f}$ → "
                f"ع24={rates['gold_24']} / ع18={rates['gold_18']}"
            )
    except Exception as e:
        print(f"[ذهب] تعذر: {e}")

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

        # جرّب عدة أنماط
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
    except Exception as e:
        print(f"[موازي] تعذر: {e}")
    return False
