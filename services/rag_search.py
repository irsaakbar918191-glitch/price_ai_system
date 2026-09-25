from __future__ import annotations

from typing import Any, Dict, List

from database.supabase_client import SupabaseClient
from services.embedding_service import EmbeddingService


class RAGSearchService:
    def __init__(self, client=None):
        self.client = client or SupabaseClient.get_client()

    def generate_query_embedding(self, query: str) -> List[float]:
        return EmbeddingService.embed_text(query)

    def search_products(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        query_embedding = self.generate_query_embedding(query)
        response = self.client.rpc(
            "match_products",
            {
                "query_embedding": query_embedding,
                "match_count": limit,
            },
        ).execute()

        if hasattr(response, "data"):
            return response.data or []
        return response

    def get_product_history(self, product_id: int) -> List[Dict[str, Any]]:
        response = self.client.table("products").select("*").eq("id", product_id).execute()
        if hasattr(response, "data"):
            dataset = response.data or []
            if not dataset:
                return []
            result = dataset[0]
            product_name = result.get("product_name")
            records = self.client.table("products").select("*").eq("product_name", product_name).order("date", desc=False).execute()
            if hasattr(records, "data"):
                return records.data or []
        return []

    def build_answer(self, query: str, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not matches:
            return {
                "answer": "I couldn’t find a matching product in the catalog yet. Please upload fresh price data for the product.",
                "products": [],
            }

        best = matches[0]
        product_id = best.get("id")
        product_name = best.get("product_name", "Product")
        model = best.get("model") or ""
        supplier = best.get("supplier") or "Unknown Supplier"
        price = best.get("price", 0)
        currency = best.get("currency", "PKR")
        date = best.get("date") or "N/A"

        history = self.get_product_history(product_id)
        price_trend = [str(record.get("price")) for record in history[:5]]
        answer = (
            f"I found {product_name} {f'({model})' if model else ''}. "
            f"The latest listed price is {currency} {price:.2f} from {supplier}. "
            f"The latest record date is {date}. "
            f"Recent price history: {', '.join(price_trend) if price_trend else 'No prior prices available.'}"
        )

        return {
            "answer": answer,
            "products": [
                {
                    "id": product_id,
                    "product_name": product_name,
                    "model": model,
                    "supplier": supplier,
                    "price": price,
                    "currency": currency,
                    "date": date,
                    "history": history,
                }
            ],
        }
