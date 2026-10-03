import re
import requests
from groq import Groq
from config import Config
from database.supabase_client import get_supabase
from services.embedding_service import EmbeddingService

class RAGSearch:
    @staticmethod
    def ask_price_assistant(query: str, user_id: str = None) -> dict:
        supabase = get_supabase()
        matched_products = []

        # 1. Step 1: Query se Model/Code nikaal kar Direct Match karein (e.g. 533347, LFR-D-MIDI, Fast Cables)
        tokens = re.findall(r'[A-Za-z0-9_\-\.]{3,}', query)
        stopwords = {"show", "details", "for", "model", "price", "what", "find", "item", "rate", "the", "hai", "kya", "btao"}
        search_terms = [t for t in tokens if t.lower() not in stopwords]

        for term in search_terms:
            try:
                res = supabase.table("products").select("*").or_(
                    f"model.ilike.%{term}%,product_name.ilike.%{term}%,supplier.ilike.%{term}%"
                ).limit(6).execute()

                if res.data:
                    for item in res.data:
                        if not any(p.get("id") == item.get("id") for p in matched_products):
                            matched_products.append(item)
            except Exception:
                pass

        # 2. Step 2: Agar direct match na mile, tab Vector Similarity Search chalayein
        if not matched_products:
            try:
                query_vector = EmbeddingService.get_embedding(query)
                res = supabase.rpc("match_products", {
                    "query_embedding": query_vector,
                    "match_threshold": 0.05,
                    "match_count": 6
                }).execute()
                matched_products = res.data or []
            except Exception:
                try:
                    res = supabase.table("products").select("*").limit(6).execute()
                    matched_products = res.data or []
                except Exception:
                    matched_products = []

        # 3. Step 3: Sahi Column Names ke sath Context banayein
        context_items = []
        for p in matched_products:
            p_name = p.get('product_name') or 'Unknown'
            p_model = p.get('model') or '-'
            p_supplier = p.get('supplier') or 'Unknown'
            p_price = p.get('price', 0)
            p_currency = p.get('currency', 'PKR')
            p_date = p.get('date', '')

            context_items.append(
                f"- Product: {p_name} | Model: {p_model} | Supplier: {p_supplier} | Price: {p_currency} {p_price:,.2f} | Date: {p_date}"
            )

        context_str = "\n".join(context_items) if context_items else "No direct database match found."

        system_prompt = f"""You are a professional AI Price Intelligence Assistant for industrial equipment and cables marketplace.
Default Currency: {Config.DEFAULT_CURRENCY}
Provide accurate, actionable pricing comparisons, supplier details, and model specifications based on available inventory.
Keep your response concise, clear, and helpful.

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
                        temperature=0.2
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

        return f"Found product match in database, but LLM connection unavailable!\nMatching Context:\n{system_prompt}"