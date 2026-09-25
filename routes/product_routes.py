from flask import Blueprint, jsonify, request

from database.supabase_client import SupabaseClient

product_bp = Blueprint("products", __name__)


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


@product_bp.get("/api/history/<int:product_id>")
@login_required
def get_history(product_id: int):
    try:
        client = SupabaseClient.get_client()
        response = client.table("products").select("*").eq("id", product_id).execute()
        if not response.data:
            return jsonify({"error": "Product not found."}), 404

        product = response.data[0]
        name = product.get("product_name")
        history = client.table("products").select("*").eq("product_name", name).order("date", desc=False).execute()
        return jsonify({"product": product, "history": history.data or []}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
