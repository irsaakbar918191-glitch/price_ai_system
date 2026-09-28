from flask import Blueprint, request, jsonify, session
from database.supabase_client import get_supabase
from services.embedding_service import EmbeddingService
from datetime import datetime

product_bp = Blueprint("product_bp", __name__)

def is_admin():
    return session.get("is_admin", False) is True

@product_bp.route("/api/products", methods=["GET"])
def list_products():
    try:
        supabase = get_supabase()
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 50))
        offset = (page - 1) * limit
        supplier = request.args.get("supplier")

        query = supabase.table("products").select("id, product_name, model, supplier, price, currency, date, source_file, created_at")
        if supplier:
            query = query.eq("supplier", supplier)

        res = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return jsonify({"products": res.data or []}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@product_bp.route("/api/products", methods=["POST"])
def create_product():
    if not is_admin():
        return jsonify({"error": "Access Denied: Only admin can add inventory."}), 403

    data = request.get_json() or {}
    product_name = data.get("product_name", "").strip()
    price = data.get("price")

    if not product_name or price is None:
        return jsonify({"error": "Product_name and Price are required."}), 400

    try:
        price_val = float(price)
        model = data.get("model", "").strip()
        supplier = data.get("supplier", "").strip()
        currency = data.get("currency", "PKR").strip()
        date_val = data.get("date") or datetime.utcnow().strftime("%Y-%m-%d")
        source_file = data.get("source_file", "manual_entry").strip()

        embed_text = f"{product_name} {model} {supplier} {currency} {price_val}"
        vector = EmbeddingService.get_embedding(embed_text)

        payload = {
            "user_id": session.get("user_id"),
            "product_name": product_name,
            "model": model,
            "supplier": supplier,
            "price": price_val,
            "currency": currency,
            "date": date_val,
            "source_file": source_file,
            "embedding": vector
        }

        supabase = get_supabase()
        res = supabase.table("products").insert([payload]).execute()
        new_prod = res.data[0] if res.data else payload

        if res.data:
            supabase.table("price_history").insert([{
                "product_id": res.data[0]["id"],
                "price": price_val,
                "currency": currency
            }]).execute()

        return jsonify({"message": "Product created", "product": new_prod}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@product_bp.route("/api/products/<product_id>", methods=["DELETE"])
def delete_product(product_id):
    if not is_admin():
        return jsonify({"error": "Access Denied: Only admin can delete products"}), 403

    try:
        supabase = get_supabase()
        supabase.table("products").delete().eq("id", product_id).execute()
        return jsonify({"message": "Product deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@product_bp.route("/api/stats", methods=["GET"])
def get_stats():
    try:
        supabase = get_supabase()
        res = supabase.table("products").select("price, supplier").execute()
        items = res.data or []

        total_items = len(items)
        total_value = sum(float(i.get("price") or 0.0) for i in items)
        avg_price = (total_value / total_items) if total_items > 0 else 0
        suppliers = list(set(i.get("supplier") for i in items if i.get("supplier")))

        return jsonify({
            "total_products": total_items,
            "total_inventory_value": round(total_value, 2),
            "average_price": round(avg_price, 2),
            "suppliers_count": len(suppliers)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500