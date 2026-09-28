from flask import Blueprint, request, jsonify, session
from services.rag_search import RAGSearch

search_bp = Blueprint("search_bp", __name__)

@search_bp.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"error": "Query required"}), 400

    try:
        user_id = session.get("user_id")
        result = RAGSearch.ask_price_assistant(query, user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500