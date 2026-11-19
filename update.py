
def get_parallel_rate(session):

    url = "https://prices.ly/usd/"

    try:
        response = session.get(url, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        text = soup.get_text(" ", strip=True)

        pattern = (
            r"الدولار\s+نقداً\s*-\s*طرابلس"
            r"\s+أعلى\s*(\d{1,2}\.\d+)"
            r"\s*[·•]\s*أدنى\s*(\d{1,2}\.\d+)"
            r"\s+(\d{1,2}\.\d+)"
        )

        match = re.search(pattern, text)

        if not match:
            print("[الموازي] تعذر استخراج السعر")
            return None, None

        high = float(match.group(1))
        low = float(match.group(2))
        current = float(match.group(3))

        if not (5 < current < 30):
            return None, None

        if not (5 < low <= current <= high < 30):
            return None, None

        print(f"[الموازي] طرابلس: {current:.2f} دينار")

        return current, "Prices.ly - طرابلس نقداً"

    except Exception as error:

        print(f"[الموازي] خطأ: {error}")

        return None, None
