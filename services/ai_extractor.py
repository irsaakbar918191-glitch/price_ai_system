import json
import re
from typing import Any, Dict

import requests

from config import Config


class AIExtractor:
    def __init__(self, api_token: str | None = None, model: str | None = None, provider: str | None = None):
        self.provider = (provider or Config.LLM_PROVIDER or "groq").lower()
        self.api_token = api_token or (
            Config.GROQ_API_KEY if self.provider == "groq" else Config.HF_API_TOKEN
        )
        self.model = model or (
            Config.GROQ_MODEL if self.provider == "groq" else Config.HF_MODEL
        )

    def extract_product_data(self, raw_text: str) -> Dict[str, Any]:
        if not raw_text or not raw_text.strip():
            return {
                "product_name": "",
                "model": "",
                "supplier": "",
                "price": 0.0,
                "currency": "PKR",
                "date": "",
            }

        if not self.api_token:
            return self._fallback_parse(raw_text)

        system_prompt = (
            "You are an extractor for pricing documents. Return only valid JSON with exact fields: "
            "product_name, model, supplier, price, currency, date. "
            "Product_name must be a short product title. Model should be model number or product variant. "
            "Supplier is the provider or vendor. Price is numeric. Currency is alpha code like PKR or USD. "
            "Date must be YYYY-MM-DD, or empty string if unknown. "
            "Do not include markdown, comments, or extra text."
        )

        try:
            if self.provider == "groq":
                result = self._call_groq_api(system_prompt, raw_text)
            else:
                result = self._call_huggingface_api(system_prompt, raw_text)

            if not result:
                return self._fallback_parse(raw_text)
            return self._clean_json_response(result)
        except Exception:
            return self._fallback_parse(raw_text)

    def _call_groq_api(self, system_prompt: str, raw_text: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Extract from this document:\n{raw_text[:4000]}"},
            ],
            "temperature": 0.1,
            "max_tokens": 256,
        }

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message", {})
        content = message.get("content") or ""
        if isinstance(content, list):
            return " ".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
        return str(content)

    def _call_huggingface_api(self, system_prompt: str, raw_text: str) -> str:
        payload = {
            "inputs": f"{system_prompt}\n\nExtract from this document:\n{raw_text[:4000]}",
            "parameters": {
                "max_new_tokens": 256,
                "temperature": 0.1,
                "return_full_text": False,
            },
        }

        response = requests.post(
            f"https://api-inference.huggingface.co/models/{self.model}",
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        return self._extract_text_from_hf_response(result)

    def _extract_text_from_hf_response(self, result: Any) -> str:
        if isinstance(result, list):
            if result and isinstance(result[0], dict):
                return result[0].get("generated_text", "")
            if result and isinstance(result[0], str):
                return result[0]
        if isinstance(result, dict):
            if "generated_text" in result:
                return result["generated_text"]
            if "error" in result:
                return ""
        return ""

    def _clean_json_response(self, text: str) -> Dict[str, Any]:
        cleaned = text.strip()
        cleaned = re.sub(r"```json|```", "", cleaned, flags=re.IGNORECASE)
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start:end + 1]
        try:
            payload = json.loads(cleaned)
        except Exception:
            return self._fallback_parse(cleaned)

        return {
            "product_name": str(payload.get("product_name", "") or "").strip(),
            "model": str(payload.get("model", "") or "").strip(),
            "supplier": str(payload.get("supplier", "") or "").strip(),
            "price": float(payload.get("price", 0.0) or 0.0),
            "currency": str(payload.get("currency", "PKR") or "PKR").upper(),
            "date": str(payload.get("date", "") or ""),
        }

    def _fallback_parse(self, raw_text: str) -> Dict[str, Any]:
        text = raw_text or ""
        product_name_match = re.search(r"([A-Za-z0-9\- ]{4,60})\s*(?:Model|SKU|Code)", text, re.IGNORECASE)
        product_name = product_name_match.group(1).strip() if product_name_match else "Unknown Product"

        model_match = re.search(r"(?:Model|SKU|Code)\s*[:#-]?\s*([A-Za-z0-9\-_/]+)", text, re.IGNORECASE)
        model = model_match.group(1).strip() if model_match else ""

        supplier_match = re.search(r"(?:Supplier|Vendor|Dealer|Company)\s*[:#-]?\s*([A-Za-z0-9 &.,/-]+)", text, re.IGNORECASE)
        supplier = supplier_match.group(1).strip() if supplier_match else "Unknown Supplier"

        price_match = re.search(r'(?:PKR|USD|EUR|GBP|AED|SAR|INR|CAD|AUD|Rs\.?|Rs\s*)\s*([0-9,]+\.?[0-9]*)', text, re.IGNORECASE)
        price = float(price_match.group(1).replace(',', '')) if price_match else 0.0

        currency_match = re.search(r'\b(PKR|USD|EUR|GBP|AED|SAR|INR|CAD|AUD)\b', text, re.IGNORECASE)
        currency = currency_match.group(1).upper() if currency_match else "PKR"

        date_match = re.search(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{4}/\d{2}/\d{2})', text)
        date = ""
        if date_match:
            d = date_match.group(1)
            try:
                date = __import__('datetime').datetime.strptime(d, "%Y-%m-%d").strftime("%Y-%m-%d") if '-' in d else __import__('datetime').datetime.strptime(d, "%d/%m/%Y").strftime("%Y-%m-%d") if '/' in d and len(d.split('/')[0]) == 2 else __import__('datetime').datetime.strptime(d, "%Y/%m/%d").strftime("%Y-%m-%d")
            except Exception:
                date = ""

        return {
            "product_name": product_name,
            "model": model,
            "supplier": supplier,
            "price": price,
            "currency": currency,
            "date": date,
        }
