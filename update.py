def scrape_ecolibya_exact_data():
    """استخراج البيانات من موقع اقتصاد ليبيا مع التحقق من كل حقل"""
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

    try:
        res = requests.get("https://ecolibya.com/", headers=headers, timeout=20)
        res.raise_for_status()
        if not res.encoding or res.encoding.lower() == "iso-8859-1":
            res.encoding = res.apparent_encoding or "utf-8"

        soup = BeautifulSoup(res.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        raw_text = soup.get_text(separator="\n")
        clean_text = normalize_arabic_numbers(raw_text)

        # 1. الدولار الرسمي
        val_off = extract_near(
            clean_text,
            r"الدولار\s*الأمريكي[^\n]*?(?:السعر\s*الرسمي|الرسمي)",
            r"(\d+\.\d{2,4})",
            window=160
        )
        if val_off:
            rates["usd_official"] = f"{float(val_off):.4f}" if len(val_off.split(".")[1]) >= 4 else val_off
            matched += 1

        # 2. السوق الموازية للدولار
        val_par = extract_near(
            clean_text,
            r"(?:السوق\s*الموازية|الموازي)[^\n]*?(?:الدولار)?",
            r"\b(\d{1,2}\.\d{2,4})\b",
            window=140
        )
        if val_par:
            rates["usd_parallel"] = val_par
            matched += 1

        # 3. الذهب غرام عيار 24 وعيار 18
        val_gold = extract_near(
            clean_text,
            r"الذهب[^\n]*?(?:عيار\s*24|سعر\s*الغرام|الغرام)",
            r"\b(\d{2,4}\.\d{2})\b",
            window=160
        )
        if val_gold:
            g24 = float(val_gold)
            rates["gold_24"] = f"{g24:.2f}"
            rates["gold_18"] = f"{g24 * (18.0 / 24.0):.2f}"
            matched += 1

        # 4. خام برنت العالمي
        val_brent = extract_near(
            clean_text,
            r"خام\s*برنت[^\n]*?(?:السعر\s*العالمي|العالمي)?",
            r"\b(\d{2,3}\.\d{2})\b",
            window=150
        )
        if val_brent:
            rates["oil_brent"] = val_brent
            matched += 1

        # 5. الجنيه المصري
        val_egp = extract_near(
            clean_text,
            r"الجنيه\s*المصري",
            r"\b(\d+\.\d{2,4})\b",
            window=140
        )
        if val_egp:
            rates["egp"] = val_egp
            matched += 1

        # 6. الدينار التونسي
        val_tnd = extract_near(
            clean_text,
            r"الدينار\s*التونسي",
            r"\b(\d+\.\d{2,4})\b",
            window=140
        )
        if val_tnd:
            rates["tnd"] = val_tnd
            matched += 1

        rates["matched_fields"] = matched
        rates["status"] = "محدث" if matched > 0 else "ثابتة"

        print("HTTP Status:", res.status_code, "| Text length:", len(clean_text), "| Matched:", matched)
        if matched == 0:
            print("Sample text:\n", clean_text[:600])

    except Exception as e:
        print(f"خطأ أثناء سحب البيانات: {e}")
        rates["status"] = "ثابتة"

    return rates
