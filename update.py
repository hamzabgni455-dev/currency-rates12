from bs4 import BeautifulSoup


def normalize_digits(text):
    if not text:
        return ""
    trans = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵٦۷۸٩", "01234567890123456789")
    return text.translate(trans).replace("٫", ".").replace(",", ".")


def get_parallel_rate(session):
    url = "https://prices.ly/usd/"

    try:
        response = session.get(url, timeout=20)
        response.raise_for_status()
        if not response.encoding or response.encoding.lower() == "iso-8859-1":
            response.encoding = response.apparent_encoding or "utf-8"

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = normalize_digits(re.sub(r"\s+", " ", soup.get_text(" ", strip=True)))

        pattern = (
            r"الدولار\s+نقداً\s*-\s*طرابلس"
            r".{0,80}?أعلى\s*(\d{1,2}\.\d+)"
            r"\s*[·•|/-]?\s*أدنى\s*(\d{1,2}\.\d+)"
            r".{0,40}?(\d{1,2}\.\d+)"
        )

        match = re.search(pattern, text)

        if not match:
            print("[الموازي] تعذر استخراج السعر")
            return None, None

        high = float(match.group(1))
        low = float(match.group(2))
        current = float(match.group(3))

        if not (5 < current < 30):
            print(f"[الموازي] السعر خارج النطاق المتوقع: {current}")
            return None, None

        if low > current or current > high:
            print(f"[الموازي] ترتيب القيم غير منطقي (أدنى={low}, حالي={current}, أعلى={high})")
            return None, None

        print(f"[الموازي] طرابلس: {current:.2f} دينار (أدنى: {low:.2f} | أعلى: {high:.2f})")
        return current, "Prices.ly - طرابلس نقداً"

    except Exception as error:
        print(f"[الموازي] خطأ: {error}")
        return None, None
