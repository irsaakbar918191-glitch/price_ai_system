import os
import uuid
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request

from config import Config
from database.supabase_client import SupabaseClient
from services.ai_extractor import AIExtractor
from services.embedding_service import EmbeddingService
from services.file_parser import FileParser

upload_bp = Blueprint("upload", __name__)


def _read_auth_token():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]
    return None


def _get_user_role(user):
    metadata = getattr(user, "user_metadata", {}) or {}
    if isinstance(metadata, dict):
        role = metadata.get("role")
        if role:
            return str(role).lower()

    user_id = getattr(user, "id", None)
    if not user_id:
        return "user"

    try:
        service_client = SupabaseClient.get_service_client()
        role_response = service_client.table("user_roles").select("role").eq("user_id", str(user_id)).maybe_single().execute()
        data = getattr(role_response, "data", None) or {}
        if isinstance(data, dict):
            role = data.get("role")
            if role:
                return str(role).lower()
    except Exception:
        pass
    return "user"


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


def admin_required(func):
    def wrapper(*args, **kwargs):
        token = _read_auth_token()
        if not token:
            return jsonify({"error": "Authentication token required."}), 401
        try:
            user_response = SupabaseClient.get_client().auth.get_user(token)
            user = getattr(user_response, "user", None)
            if not user:
                return jsonify({"error": "Invalid or expired token."}), 401

            role = _get_user_role(user)
            if role != "admin":
                return jsonify({
                    "error": "Admin access required.",
                    "details": "Set the user's role to admin in Supabase Auth metadata or user_roles table."
                }), 403
            request.user = user
            return func(*args, **kwargs)
        except Exception as exc:
            return jsonify({"error": f"Admin access failed: {exc}"}), 403
    wrapper.__name__ = func.__name__
    return wrapper


@upload_bp.post("/api/upload")
@login_required
@admin_required
def upload_file():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded."}), 400

        uploaded = request.files["file"]
        if uploaded.filename == "":
            return jsonify({"error": "Empty filename."}), 400
        if not FileParser.allowed_file(uploaded.filename):
            return jsonify({"error": "Unsupported file type."}), 400

        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        filename = f"{uuid.uuid4()}_{uploaded.filename}"
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        uploaded.save(file_path)

        extracted_text = FileParser.extract_text(file_path)
        cleaned_text = FileParser.clean_text(extracted_text)
        if not cleaned_text:
            return jsonify({"error": "No extractable text found in the file."}), 400

        extractor = AIExtractor()
        product_data = extractor.extract_product_data(cleaned_text)
        if not product_data.get("product_name"):
            product_data["product_name"] = os.path.splitext(uploaded.filename)[0]

        product_payload = {
            "product_name": product_data.get("product_name") or os.path.splitext(uploaded.filename)[0],
            "model": product_data.get("model") or "",
            "supplier": product_data.get("supplier") or "Unknown Supplier",
            "price": float(product_data.get("price") or 0.0),
            "currency": (product_data.get("currency") or Config.DEFAULT_CURRENCY).upper(),
            "date": product_data.get("date") or datetime.utcnow().strftime("%Y-%m-%d"),
            "source_file": filename,
        }

        service_client = SupabaseClient.get_service_client()
        product_response = service_client.table("products").insert(product_payload).execute()
        if not product_response.data:
            return jsonify({"error": "Failed to store product record."}), 500

        product_id = product_response.data[0]["id"]
        embedding = EmbeddingService.embed_text(f"{product_payload['product_name']} {product_payload['model']} {product_payload['supplier']} {product_payload['currency']} {product_payload['price']}")
        service_client.table("product_embeddings").insert({
            "product_id": product_id,
            "content": cleaned_text[:2000],
            "embedding": embedding,
        }).execute()

        return jsonify({
            "message": "Product uploaded and indexed successfully.",
            "product": product_response.data[0],
            "extracted": product_data,
        }), 201
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
