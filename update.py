import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# ---------- دوال مساعدة ----------
def _safe_get_json(url, headers=None, timeout=20):
    """جلب JSON مع معالجة الأخطاء وإرجاع None عند الفشل"""
    try:
        r = requests.get(url, headers=headers or {}, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  ⚠️ فشل الاتصال بـ {url}: {e}")
        return None

def _to_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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
        "Accept": "application/json, text/plain, */*",
    }

    matched = 0

    # ============================================================
    # 1) سعر الصرف الرسمي USD/LYD من currency-api (بدون مفتاح)
    # ============================================================
    try:
        data = _safe_get_json(
            "https://cdn.jsdelivr.net/gh/NemesisX1/currency-api@main/v1/currencies/usd.json",
            headers,
        )
        if data:
            # البنية متوقعة: {"usd": {"lyd": 6.43, "tnd": 3.1, "egp": 48.5, ...}}
            usd_block = data.get("usd", {})
            lyd = _to_float(usd_block.get("lyd"))
            if lyd and 4.0 < lyd < 12.0:
                rates["usd_official"] = f"{lyd:.4f}"
                matched += 1
                print(f"✅ [رسمي] USD/LYD = {lyd:.4f}")

            # العملات الأخرى (اختياري)
            tnd = _to_float(usd_block.get("tnd"))
            if tnd and 1.0 < tnd < 6.0:
                rates["tnd"] = f"{1.0 / tnd:.4f}"  # نعكس لأن القيمة هي TND لكل USD
            egp = _to_float(usd_block.get("egp"))
            if egp and 10.0 < egp < 100.0:
                rates["egp"] = f"{1.0 / egp:.4f}"
    except Exception as e:
        print(f"❌ [رسمي] خطأ غير متوقع: {e}")

    # ============================================================
    # 2) السوق الموازي من fulusly (بدون مفتاح)
    # ============================================================
    try:
        data = _safe_get_json(
            "https://fulusly.soft9.us/api/rates?from=USD&to=LYD",
            headers,
        )
        if data:
            # البنية المحتملة: {"rate": 10.63} أو {"result": 10.63} أو {"rates": {"LYD": 10.63}}
            parallel = (
                _to_float(data.get("rate"))
                or _to_float(data.get("result"))
                or _to_float(data.get("rates", {}).get("LYD"))
            )
            if parallel and 5.0 < parallel < 30.0:
                rates["usd_parallel"] = f"{parallel:.2f}"
                matched += 1
                print(f"✅ [موازي] USD/LYD = {parallel:.2f}")
    except Exception as e:
        print(f"❌ [موازي] خطأ غير متوقع: {e}")

    # ============================================================
    # 3) الذهب: سعر الأونصة بالدولار ثم التحويل للدينار
    # ============================================================
    gold_oz_usd = None
    try:
        data = _safe_get_json(
            "https://api.goldprice.dev/v1/prices?symbol=XAU-USD-SPOT",
            headers,
        )
        if data:
            # البنية المحتملة: {"price": 2650.4} أو {"data": {"price": 2650.4}}
            gold_oz_usd = (
                _to_float(data.get("price"))
                or _to_float(data.get("data", {}).get("price"))
                or _to_float(data.get("spot_usd_oz"))  # من xaus-api
            )
    except Exception as e:
        print(f"❌ [ذهب] تعذر جلب سعر الأونصة: {e}")

    # إذا فشل goldprice.dev، جرّب xaus-api كاحتياطي
    if not gold_oz_usd:
        try:
            data = _safe_get_json("https://xaus.com/api/v1/spot", headers)
            if data:
                gold_oz_usd = _to_float(data.get("spot_usd_oz"))
        except Exception as e:
            print(f"❌ [ذهب-احتياطي] تعذر: {e}")

    if gold_oz_usd and 1000.0 < gold_oz_usd < 6000.0:
        try:
            usd_lyd = float(rates["usd_official"])
            gold_24 = (gold_oz_usd / 31.1035) * usd_lyd
            rates["gold_24"] = f"{gold_24:.2f}"
            rates["gold_18"] = f"{gold_24 * (18.0 / 24.0):.2f}"
            matched += 2
            print(f"✅ [ذهب] أونصة={gold_oz_usd:.2f}$ → ع24={rates['gold_24']} / ع18={rates['gold_18']}")
        except Exception as e:
            print(f"❌ [ذهب] خطأ في الحساب: {e}")

    # ============================================================
    # 4) نفط برنت من AmericasOilWatch (بدون مفتاح)
    # ============================================================
    try:
        data = _safe_get_json(
            "https://americasoilwatch.com/api/v1/brent",
            headers,
        )
        if data:
            # البنية المحتملة: {"price": 87.33} أو {"brent": 87.33} أو {"value": 87.33}
            brent = (
                _to_float(data.get("price"))
                or _to_float(data.get("brent"))
                or _to_float(data.get("value"))
            )
            if brent and 20.0 < brent < 200.0:
                rates["oil_brent"] = f"{brent:.2f}"
                matched += 1
                print(f"✅ [برنت] {brent:.2f} USD")
    except Exception as e:
        print(f"❌ [برنت] خطأ غير متوقع: {e}")

    # ============================================================
    # النتيجة النهائية
    # ============================================================
    rates["matched_fields"] = matched
    rates["status"] = "محدث" if matched > 0 else "ثابتة"
    print(f"\n📊 الحقول المطابقة: {matched} / 8")
    return rates


# للاختبار المحلي فقط:
if __name__ == "__main__":
    result = scrape_market_rates_multi_source()
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
