from database.supabase_client import get_supabase
from services.embedding_service import EmbeddingService
from groq import Groq
from config import Config
import requests

class RAGSearch:
    @staticmethod
    def ask_price_assistant(query: str, user_id: str = None) -> dict:
        supabase = get_supabase()
        query_vector = EmbeddingService.get_embedding(query)

        matched_products = []
        try:
            res = supabase.rpc("match_products", {
                "query_embedding": query_vector,
                "match_threshold": 0.05,
                "match_count": 6
            }).execute()
            matched_products = res.data or []
        except Exception:
            try:
                res = supabase.table("products").select("id, title, description, category, price, currency, stock").limit(6).execute()
                matched_products = res.data or []
            except Exception:
                matched_products = []

        context_items = []
        for p in matched_products:
            context_items.append(
                f"- Product: {p.get('title')} | Price: {p.get('currency', 'PKR')} {p.get('price')} | Stock: {p.get('stock')} | Category: {p.get('category')} | Info: {p.get('description', '')}"
            )
        context_str = "\n".join(context_items) if context_items else "No direct database match found."

        system_prompt = f"""You are a professional AI Price Intelligence Assistant for the marketplace.
Default Currency: {Config.DEFAULT_CURRENCY}
Provide accurate, actionable pricing comparisons, stock availability, and market insights based on the available inventory.
Keep your response clear, well-structured, and helpful.

Available Inventory Context:
{context_str}
"""

        answer = RAGSearch._call_llm(system_prompt, query)

        try:
            supabase.table("chat_history").insert([
                {"user_id": user_id, "role": "user", "content": query},
                {"user_id": user_id, "role": "assistant", "content": answer}
            ]).execute()
        except Exception:
            pass

        return {
            "answer": answer,
            "relevant_products": matched_products
        }

    @staticmethod
    def _call_llm(system_prompt: str, user_query: str) -> str:
        if Config.GROQ_API_KEY:
            client = Groq(api_key=Config.GROQ_API_KEY)
            models_to_try = [Config.GROQ_MODEL, "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
            for model_name in models_to_try:
                try:
                    completion = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_query}
                        ],
                        model=model_name,
                        temperature=0.3
                    )
                    return completion.choices[0].message.content
                except Exception:
                    continue

        if Config.HF_API_TOKEN:
            try:
                url = f"https://api-inference.huggingface.co/models/{Config.HF_MODEL}"
                headers = {"Authorization": f"Bearer {Config.HF_API_TOKEN}"}
                prompt = f"{system_prompt}\nUser: {user_query}\nAssistant:"
                res = requests.post(url, headers=headers, json={"inputs": prompt, "parameters": {"max_new_tokens": 512}}, timeout=20)
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list) and len(data) > 0:
                        return data[0].get("generated_text", "").split("Assistant:")[-1].strip()
            except Exception:
                pass

        return f"Found product match in database, but LLM connection unavailable!. Matching items:\n{system_prompt}"