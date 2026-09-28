from flask import Blueprint, request, jsonify, session
from database.supabase_client import get_public_supabase

auth_bp = Blueprint("auth_bp", __name__)

def check_admin_status(user):
    if not user:
        return False
    user_meta = getattr(user, "user_metadata", {}) or {}
    app_meta = getattr(user, "app_metadata", {}) or {}
    return user_meta.get("role") == "admin" or app_meta.get("role") == "admin"

@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        supabase = get_public_supabase()
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            is_adm = check_admin_status(res.user)
            session["user_id"] = res.user.id
            session["user_email"] = res.user.email
            session["is_admin"] = is_adm

            return jsonify({
                "message": "Login successful",
                "user": {
                    "id": res.user.id,
                    "email": res.user.email,
                    "is_admin": is_adm
                }
            }), 200
        return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 401

@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    try:
        supabase = get_public_supabase()
        res = supabase.auth.sign_up({
            "email": email, 
            "password": password,
            "options": {"data": {"role": "user"}}
        })
        if res.user:
            session["user_id"] = res.user.id
            session["user_email"] = res.user.email
            session["is_admin"] = False
            return jsonify({
                "message": "Registration successful",
                "user": {"id": res.user.id, "email": res.user.email, "is_admin": False}
            }), 201
        return jsonify({"error": "Registration failed"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200

@auth_bp.route("/api/auth/me", methods=["GET"])
def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"authenticated": False, "is_admin": False}), 200
    return jsonify({
        "authenticated": True,
        "is_admin": session.get("is_admin", False),
        "user": {"id": user_id, "email": session.get("user_email")}
    }), 200