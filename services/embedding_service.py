import requests
import hashlib
from config import Config

class EmbeddingService:
    @staticmethod
    def get_embedding(text: str) -> list:
        if not text or not text.strip():
            return [0.0] * 384

        clean_text = text.replace("\n", " ").strip()
        hf_token = Config.HF_API_TOKEN
        model = Config.EMBEDDING_MODEL

        if hf_token:
            api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{model}"
            headers = {"Authorization": f"Bearer {hf_token}"}
            try:
                response = requests.post(
                    api_url,
                    headers=headers,
                    json={"inputs": clean_text, "options": {"wait_for_model": True}},
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        if len(data) > 0 and isinstance(data[0], list):
                            return data[0]
                        return data
            except Exception:
                pass

        return EmbeddingService._fallback_vector(clean_text)

    @staticmethod
    def _fallback_vector(text: str) -> list:
        vector = []
        for i in range(384):
            seed = f"{text}_{i}".encode("utf-8")
            val = int(hashlib.md5(seed).hexdigest(), 16) % 10000 / 10000.0
            vector.append(round(val * 2 - 1, 6))
        return vector