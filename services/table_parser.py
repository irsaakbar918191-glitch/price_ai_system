import re
from datetime import datetime


class TableParser:
    """Deterministic heuristic table parser for structured quotation and inventory text."""

    KNOWN_BRANDS = ["VMPA", "LFR", "MA-50", "Filter", "Valve", "Festo"]
    EXCLUDED_TOKENS = {"festo", "no's", "nos", "set", "total", "qty", "item"}

    @classmethod
    def parse(cls, raw_text: str, filename: str) -> list[dict]:
        """Extract structured product items from text using pattern matching."""
        if not raw_text or not raw_text.strip():
            return []

        items = []
        global_date = cls._extract_date(raw_text)

        for line in raw_text.splitlines():
            line_str = line.strip()
            if not line_str or cls._is_header_row(line_str):
                continue

            price = cls._extract_price(line_str)
            if price is None:
                continue

            model = cls._extract_model(line_str)
            product_name = cls._extract_product_name(line_str)

            if product_name:
                items.append({
                    "product_name": product_name,
                    "model": model,
                    "supplier": "Festo",
                    "price": price,
                    "currency": "PKR",
                    "date": global_date,
                    "source_file": filename,
                })

        return items

    @classmethod
    def _extract_date(cls, text: str) -> str:
        """Extract ISO date or default to current date."""
        match = re.search(r"\b(202\d[-/]\d{2}[-/]\d{2})\b", text)
        if match:
            return match.group(1).replace("/", "-")
        return datetime.utcnow().strftime("%Y-%m-%d")

    @classmethod
    def _is_header_row(cls, line: str) -> bool:
        """Check if line corresponds to a table header."""
        lowered = line.lower()
        header_keywords = [
            "product name",
            "price (pkr)",
            "inquiry date",
            "cost unit",
            "unit price",
        ]
        return any(keyword in lowered for keyword in header_keywords)

    @classmethod
    def _extract_price(cls, line: str) -> float | None:
        """Extract unit price, ignoring four-digit calendar years."""
        candidates = re.findall(r"\b\d{4,6}(?:\.\d+)?\b", line)
        if not candidates:
            return None

        current_year = float(datetime.utcnow().year)
        valid_prices = [
            float(val) for val in candidates if float(val) != current_year
        ]
        return valid_prices[-1] if valid_prices else None

    @classmethod
    def _extract_model(cls, line: str) -> str:
        """Extract standard 6-digit manufacturer part/model code."""
        models = re.findall(r"\b\d{6}\b", line)
        return models[0] if models else ""

    @classmethod
    def _extract_product_name(cls, line: str) -> str:
        """Extract product title based on known prefix patterns or tokens."""
        for brand in cls.KNOWN_BRANDS:
            if brand.lower() in line.lower():
                pattern = (
                    r"((?:"
                    + brand
                    + r")[A-Za-z0-9_\-\.\s/]+(?:\d{6}|\d+/\d+)?)"
                )
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        tokens = [
            t.strip()
            for t in re.split(r"[\t|]+| {2,}", line)
            if t.strip()
        ]
        for token in tokens:
            cleaned = token.lower()
            if (
                len(token) > 4
                and not token.replace(".", "").isdigit()
                and not re.match(r"^202\d", token)
                and cleaned not in cls.EXCLUDED_TOKENS
            ):
                return token

        return ""