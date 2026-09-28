import json
import base64
import requests
from datetime import datetime
from groq import Groq
from config import Config

class AIExtractor:
    @staticmethod
    def extract_products_from_text(raw_text: str, filename: str = "document") -> list:
        today_date = datetime.utcnow().strftime("%Y-%m-%d")
        prompt = f"""Extract all items, products, or supplier price quotes from the text into a clean JSON array.
Return ONLY valid JSON matching this schema:
[
  {{
    "product_name": "Product Name",
    "model": "Model or SKU number",
    "supplier": "Supplier or Vendor Name",
    "price": 0.0,
    "currency": "{Config.DEFAULT_CURRENCY}",
    "date": "{today_date}",
    "source_file": "{filename}"
  }}
]

Raw Text:
{raw_text[:8000]}
"""
        response_text = AIExtractor._call_llm(prompt)
        return AIExtractor._clean_json(response_text, filename)

    @staticmethod
    def extract_from_image(image_bytes: bytes, mime_type: str = "image/jpeg", filename: str = "image_upload") -> list:
        today_date = datetime.utcnow().strftime("%Y-%m-%d")
        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        if Config.GROQ_API_KEY:
            client = Groq(api_key=Config.GROQ_API_KEY)
            models_to_try = [
                Config.GROQ_VISION_MODEL,
                "llama-3.2-11b-vision-preview",
                "llama-3.2-90b-vision-preview"
            ]
            for model_name in models_to_try:
                try:
                    chat_completion = client.chat.completions.create(
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text", 
                                        "text": f"Extract all products, price tags, or catalog items from this image as a valid JSON array with keys: product_name, model, supplier, price (float), currency (default {Config.DEFAULT_CURRENCY}), date ({today_date}), source_file ({filename}). Output pure JSON array only."
                                    },
                                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_img}"}}
                                ]
                            }
                        ],
                        model=model_name,
                        temperature=0.1
                    )
                    return AIExtractor._clean_json(chat_completion.choices[0].message.content, filename)
                except Exception:
                    continue
        return []

    @staticmethod
    def _call_llm(prompt: str) -> str:
        if Config.GROQ_API_KEY:
            client = Groq(api_key=Config.GROQ_API_KEY)
            models_to_try = [Config.GROQ_MODEL, "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
            for model_name in models_to_try:
                try:
                    completion = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": "You are a professional price intelligence catalog parser. Output valid JSON array only."},
                            {"role": "user", "content": prompt}
                        ],
                        model=model_name,
                        temperature=0.1
                    )
                    return completion.choices[0].message.content
                except Exception:
                    continue

        if Config.HF_API_TOKEN:
            try:
                url = f"https://api-inference.huggingface.co/models/{Config.HF_MODEL}"
                headers = {"Authorization": f"Bearer {Config.HF_API_TOKEN}"}
                payload = {"inputs": prompt, "parameters": {"max_new_tokens": 1024, "return_full_text": False}}
                res = requests.post(url, headers=headers, json=payload, timeout=20)
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list) and len(data) > 0:
                        return data[0].get("generated_text", "")
            except Exception:
                pass

        return "[]"

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
                p_name = item.get("product_name") or item.get("name") or item.get("title")
                try:
                    price = float(item.get("price", 0))
                except (ValueError, TypeError):
                    price = 0.0

                if p_name and price > 0:
                    valid_items.append({
                        "product_name": str(p_name).strip(),
                        "model": str(item.get("model", "")).strip(),
                        "supplier": str(item.get("supplier", "")).strip(),
                        "price": price,
                        "currency": str(item.get("currency", Config.DEFAULT_CURRENCY)).strip(),
                        "date": item.get("date") or datetime.utcnow().strftime("%Y-%m-%d"),
                        "source_file": filename
                    })
            return valid_items
        except Exception:
            return []