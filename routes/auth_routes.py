from flask import Blueprint, jsonify, request

from database.supabase_client import SupabaseClient

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/api/auth/register")
def register():
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip()
        password = data.get("password") or ""
        if not email or not password:
            return jsonify({"error": "Email and password are required."}), 400

        client = SupabaseClient.get_client()
        response = client.auth.sign_up({"email": email, "password": password})
        return jsonify({"message": "Registration successful", "user": response.user.model_dump() if response.user else None}), 201
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@auth_bp.post("/api/auth/login")
def login():
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip()
        password = data.get("password") or ""
        if not email or not password:
            return jsonify({"error": "Email and password are required."}), 400

        client = SupabaseClient.get_client()
        response = client.auth.sign_in_with_password({"email": email, "password": password})
        token = response.session.access_token if response.session else None
        return jsonify({
            "message": "Login successful",
            "token": token,
            "user": response.user.model_dump() if response.user else None,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
