def scrape_market_rates_multi_source():
    """جلب الأسعار من مصادر بديلة متعددة مع إبقاء نفس مفاتيح rates.json"""
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
        "matched_fields": 0
    }

    libya_tz = ZoneInfo("Africa/Tripoli")
    rates["last_update"] = datetime.now(libya_tz).strftime("%Y-%m-%d %H:%M")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache"
    }

    matched = 0

    # 1. الدولار الرسمي من مصرف ليبيا المركزي (أو احتياطي API)
    try:
        res_cbl = requests.get("https://cbl.gov.ly/currency-exchange-rates/", headers=headers, timeout=20)
        res_cbl.raise_for_status()
        if not res_cbl.encoding or res_cbl.encoding.lower() == "iso-8859-1":
            res_cbl.encoding = res_cbl.apparent_encoding or "utf-8"

        soup_cbl = BeautifulSoup(res_cbl.text, "html.parser")
        for tag in soup_cbl(["script", "style", "noscript"]):
            tag.decompose()
        txt_cbl = normalize_arabic_numbers(soup_cbl.get_text(separator="\n"))

        val_off = extract_near(
            txt_cbl,
            r"الدولار\s*الأمريكي",
            r"\b(\d+\.\d{2,4})\b",
            window=120
        )
        if val_off:
            rates["usd_official"] = f"{float(val_off):.4f}"
            matched += 1
    except Exception as e:
        print("تعذر جلب الدولار الرسمي من المركزي:", e)

    # 2. السوق الموازية للدولار من عين ليبيا
    try:
        res_ean = requests.get("https://www.eanlibya.com/exchangerate/", headers=headers, timeout=20)
        res_ean.raise_for_status()
        if not res_ean.encoding or res_ean.encoding.lower() == "iso-8859-1":
            res_ean.encoding = res_ean.apparent_encoding or "utf-8"

        soup_ean = BeautifulSoup(res_ean.text, "html.parser")
        for tag in soup_ean(["script", "style", "noscript"]):
            tag.decompose()
        txt_ean = normalize_arabic_numbers(soup_ean.get_text(separator="\n"))

        val_par = extract_near(
            txt_ean,
            r"(?:السوق\s*الموازية|الدولار)",
            r"\b(\d{1,2}\.\d{2})\b",
            window=120
        )
        if val_par:
            rates["usd_parallel"] = val_par
            matched += 1
    except Exception as e:
        print("تعذر جلب السوق الموازية:", e)

    # 3. الذهب في ليبيا (عيار 24 وعيار 18 بالدينار الليبي) من GoldBursa
    try:
        res_gold = requests.get("https://www.goldbursa.com/gold/libya", headers=headers, timeout=20)
        res_gold.raise_for_status()
        if not res_gold.encoding or res_gold.encoding.lower() == "iso-8859-1":
            res_gold.encoding = res_gold.apparent_encoding or "utf-8"

        soup_gold = BeautifulSoup(res_gold.text, "html.parser")
        for tag in soup_gold(["script", "style", "noscript"]):
            tag.decompose()
        txt_gold = normalize_arabic_numbers(soup_gold.get_text(separator="\n"))

        val_g24 = extract_near(txt_gold, r"1\s*جرام\s*-\s*عيار\s*24", r"(\d{2,4}\.\d{2})", window=80)
        val_g18 = extract_near(txt_gold, r"1\s*جرام\s*-\s*عيار\s*18", r"(\d{2,4}\.\d{2})", window=80)

        if val_g24:
            rates["gold_24"] = f"{float(val_g24):.2f}"
            matched += 1
        if val_g18:
            rates["gold_18"] = f"{float(val_g18):.2f}"
            matched += 1
        elif val_g24:
            rates["gold_18"] = f"{float(val_g24) * (18.0 / 24.0):.2f}"
    except Exception as e:
        print("تعذر جلب أسعار الذهب:", e)

    rates["matched_fields"] = matched
    rates["status"] = "محدث" if matched > 0 else "ثابتة"
    print("Matched fields:", matched)
    return rates
