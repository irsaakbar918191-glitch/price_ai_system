import json
import re
import requests
from datetime import datetime
from config import Config
from services.table_parser import TableParser


class AIExtractor:
    """Orchestrates structured product extraction from OCR text using deterministic parsing and LLM fallback."""

    last_error: str = ""

    @classmethod
    def parse_text_to_products(cls, raw_text: str, filename: str) -> list[dict]:
        """Parse raw document text into standardized product catalog items."""
        cls.last_error = ""

        if not raw_text or not raw_text.strip():
            cls.last_error = "No readable text content provided for extraction."
            print(f"[AIExtractor] {cls.last_error}")
            return []

        print(f"\n[AIExtractor] Processing input text ({len(raw_text)} chars) from: {filename}")

        # Stage 1: Deterministic heuristic table parsing
        direct_items = TableParser.parse(raw_text, filename)
        if direct_items:
            print(f"[AIExtractor] Direct table parser successfully extracted {len(direct_items)} items.")
            return direct_items

        print("[AIExtractor] Direct table parsing yielded no items. Delegating to LLM...")

        # Stage 2: LLM Fallback (Groq)
        return cls._extract_with_llm(raw_text, filename)

    @classmethod
    def _extract_with_llm(cls, raw_text: str, filename: str) -> list[dict]:
        """Invoke Groq LLM to parse complex or unstructured document text."""
        api_key = Config.GROQ_API_KEY
        if not api_key:
            cls.last_error = "GROQ_API_KEY is missing from environment configuration."
            print(f"[AIExtractor Error] {cls.last_error}")
            return []

        today_date = datetime.utcnow().strftime("%Y-%m-%d")
        prompt = f"""You are an industrial quote and catalog parser.
Extract all product lines from the provided text into a JSON array of objects.

Required Schema:
- product_name: Full item name/description (string)
- model: Part number or SKU (string)
- supplier: Manufacturer, vendor, or make (string)
- price: Clean numeric unit price without commas (float)
- currency: 'PKR' or detected currency (string)
- date: Mentioned invoice/quote date or '{today_date}' (string)
- source_file: '{filename}' (string)

Raw Text:
{raw_text[:7000]}

Return valid JSON array only with NO conversational text:
[
  {{
    "product_name": "Sample Product",
    "model": "123456",
    "supplier": "Festo",
    "price": 1000.0,
    "currency": "PKR",
    "date": "{today_date}",
    "source_file": "{filename}"
  }}
]
"""
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are a data extraction engine. Output valid JSON array only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code == 200:
                raw_json = response.json()["choices"][0]["message"]["content"]
                items = cls._sanitize_json(raw_json, filename)
                if items:
                    print(f"[AIExtractor] LLM successfully parsed {len(items)} items.")
                    return items
                cls.last_error = "LLM returned valid response, but no structured items were found."
            else:
                cls.last_error = f"Groq API returned HTTP {response.status_code}: {response.text}"
                print(f"[AIExtractor Error] {cls.last_error}")

        except requests.RequestException as exc:
            cls.last_error = f"Network communication error with Groq API: {str(exc)}"
            print(f"[AIExtractor Exception] {cls.last_error}")

        return []

    @classmethod
    def _sanitize_json(cls, text: str, filename: str) -> list[dict]:
        """Strip markdown fences and deserialize JSON into validated product records."""
        if not text:
            return []

        cleaned = text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start != -1 and end != -1:
            cleaned = cleaned[start : end + 1]

        try:
            parsed = json.loads(cleaned)
            records = parsed if isinstance(parsed, list) else [parsed]
            validated = []

            for record in records:
                name = record.get("product_name") or record.get("item")
                if not name:
                    continue

                raw_price = record.get("price", 0.0)
                price = float(re.sub(r"[^0-9.]", "", str(raw_price).replace(",", "")) or 0.0)

                validated.append({
                    "product_name": str(name).strip(),
                    "model": str(record.get("model", "")).strip(),
                    "supplier": str(record.get("supplier", "Festo")).strip(),
                    "price": price,
                    "currency": str(record.get("currency", Config.DEFAULT_CURRENCY)).replace("PAK RS", "PKR").strip(),
                    "date": record.get("date") or datetime.utcnow().strftime("%Y-%m-%d"),
                    "source_file": filename,
                })

            return validated

        except (json.JSONDecodeError, ValueError) as exc:
            cls.last_error = f"JSON deserialization failed: {str(exc)}"
            print(f"[AIExtractor Error] {cls.last_error}")
            return []