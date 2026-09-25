from flask import Blueprint, jsonify, request

from database.supabase_client import SupabaseClient
from services.rag_search import RAGSearchService

search_bp = Blueprint("search", __name__)


def _read_auth_token():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]
    return None


def login_required(func):
    def wrapper(*args, **kwargs):
        token = _read_auth_token()
        if not token:
            return jsonify({"error": "Authentication token required."}), 401
        try:
            user_response = SupabaseClient.get_client().auth.get_user(token)
            if not user_response or not getattr(user_response, "user", None):
                return jsonify({"error": "Invalid or expired token."}), 401
            request.user = user_response.user
            return func(*args, **kwargs)
        except Exception as exc:
            return jsonify({"error": f"Authentication failed: {exc}"}), 401
    wrapper.__name__ = func.__name__
    return wrapper


@search_bp.post("/api/search")
@login_required
def search():
    try:
        data = request.get_json(silent=True) or {}
        query = (data.get("query") or "").strip()
        if not query:
            return jsonify({"error": "Search query is required."}), 400

        rag = RAGSearchService()
        matches = rag.search_products(query, limit=5)
        result = rag.build_answer(query, matches)
        return jsonify({"query": query, **result}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
