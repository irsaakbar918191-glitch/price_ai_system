import json
import base64
import re
from datetime import datetime
from groq import Groq
from config import Config

class AIExtractor:
    @staticmethod
    def extract_from_image(image_bytes: bytes, mime_type: str = "image/png", filename: str = "image_upload") -> list:
        today_date = datetime.utcnow().strftime("%Y-%m-%d")
        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        
        prompt = f"""You are an advanced Visual Document and OCR Intelligence system.
Analyze this image thoroughly, regardless of its design, orientation, or format (it could be an invoice, bill, inquiry sheet, cropped table, WhatsApp screenshot, or product tag).

Your goal: Identify EVERY product, part, material, or line item present in the visual.

Instructions:
1. "product_name": Extract the full item name or description (e.g. 'VMPA-KMS-H 533198', 'Filter Regulator Lubricator', 'Dell Inspiron').
2. "model": Extract part numbers, serial codes, or SKU numbers if visible. If not visible, leave as empty string.
3. "supplier": Extract any company name, brand, vendor, or make (e.g., 'Festo', 'Logitech', or general vendor). If none found, write 'Not Specified'.
4. "price": Find the unit cost, rate, or amount associated with the item. Remove currency symbols, commas, and spaces. Convert into a clean floating-point number. IF NO PRICE OR RATE IS SHOWN IN THE IMAGE, SET IT TO 0.0 (DO NOT SKIP THE ITEM).
5. "currency": Detect currency (e.g. 'PKR', 'USD', 'EUR'). If written as 'PAK RS' or 'Rs', convert to 'PKR'. Default is '{Config.DEFAULT_CURRENCY}'.
6. "date": Extract any inquiry, quotation, or invoice date found in the visual (YYYY-MM-DD format). If no date is found, use '{today_date}'.
7. "source_file": '{filename}'

Output Format:
Return ONLY a valid JSON array of objects. Never include markdown code fences or conversational text.
Example:
[
  {{
    "product_name": "Sample Item",
    "model": "SKU-123",
    "supplier": "Not Specified",
    "price": 0.0,
    "currency": "{Config.DEFAULT_CURRENCY}",
    "date": "{today_date}",
    "source_file": "{filename}"
  }}
]
"""
        client = None
        if Config.GROQ_API_KEY:
            try:
                client = Groq(api_key=Config.GROQ_API_KEY)
            except Exception:
                client = None

        if client:
            models_to_run = [
                "llama-3.2-11b-vision-preview",
                "llama-3.2-90b-vision-preview",
                Config.GROQ_VISION_MODEL
            ]
            for model_name in models_to_run:
                try:
                    res = client.chat.completions.create(
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_img}"}}
                                ]
                            }
                        ],
                        model=model_name,
                        temperature=0.1
                    )
                    content = res.choices[0].message.content
                    parsed = AIExtractor._clean_json(content, filename)
                    if parsed and len(parsed) > 0:
                        return parsed
                except Exception:
                    continue

        return []

    @staticmethod
    def _clean_price(val) -> float:
        if val is None:
            return 0.0
        cleaned = re.sub(r'[^0-9.]', '', str(val).replace(',', ''))
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    @staticmethod
    def _clean_json(text: str, filename: str) -> list:
        if not text:
            return []
        cleaned = text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        try:
            parsed = json.loads(cleaned)
            items = []
            if isinstance(parsed, list):
                items = parsed
            elif isinstance(parsed, dict):
                for val in parsed.values():
                    if isinstance(val, list):
                        items = val
                        break
                if not items:
                    items = [parsed]

            valid_items = []
            for item in items:
                name = item.get("product_name") or item.get("item") or item.get("name") or item.get("description")
                if not name:
                    continue

                raw_price = item.get("price") or item.get("cost_unit") or item.get("rate") or 0.0
                price = AIExtractor._clean_price(raw_price)

                valid_items.append({
                    "product_name": str(name).strip(),
                    "model": str(item.get("model", "")).strip(),
                    "supplier": str(item.get("supplier", "Not Specified")).strip(),
                    "price": price,
                    "currency": str(item.get("currency", Config.DEFAULT_CURRENCY)).replace("PAK RS", "PKR").strip(),
                    "date": item.get("date") or datetime.utcnow().strftime("%Y-%m-%d"),
                    "source_file": filename
                })
            return valid_items
        except Exception:
            return []

    @staticmethod
    def extract_products_from_text(raw_text: str, filename: str = "document") -> list:
        today_date = datetime.utcnow().strftime("%Y-%m-%d")
        prompt = f"""Extract all items, products, or supplier price quotes from the text into a clean JSON array with keys:
product_name, model, supplier, price (numeric float, no commas), currency (default {Config.DEFAULT_CURRENCY}), date, source_file.
Raw Text:
{raw_text[:8000]}
"""
        if Config.GROQ_API_KEY:
            try:
                client = Groq(api_key=Config.GROQ_API_KEY)
                completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a professional catalog parser. Output JSON array only."},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.1
                )
                return AIExtractor._clean_json(completion.choices[0].message.content, filename)
            except Exception:
                pass
        return []