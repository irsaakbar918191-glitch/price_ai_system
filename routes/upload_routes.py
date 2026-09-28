from flask import Blueprint, request, jsonify, session
from services.file_parser import FileParser
from services.embedding_service import EmbeddingService
from database.supabase_client import get_supabase
from datetime import datetime

upload_bp = Blueprint("upload_bp", __name__)

def is_admin():
    return session.get("is_admin", False) is True

@upload_bp.route("/api/upload", methods=["POST"])
def upload_file():
    if not is_admin():
        return jsonify({"error": "Access Denied: Only admin can upload file."}), 403

    if "file" not in request.files:
        return jsonify({"error": "Upload the file."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    try:
        file_bytes = file.read()
        extracted_items = FileParser.parse_file(file.filename, file_bytes)

        if not extracted_items:
            return jsonify({"error": "Can't extract data from the file."}), 422

        supabase = get_supabase()
        user_id = session.get("user_id")

        inserted_records = []
        for item in extracted_items:
            product_name = item.get("product_name", "").strip()
            if not product_name:
                continue

            try:
                price = float(item.get("price", 0.0))
            except (ValueError, TypeError):
                price = 0.0

            model = item.get("model", "")
            supplier = item.get("supplier", "")
            currency = item.get("currency", "PKR")
            date_val = item.get("date") or datetime.utcnow().strftime("%Y-%m-%d")
            source_file = file.filename

            vector = EmbeddingService.get_embedding(f"{product_name} {model} {supplier} {currency} {price}")

            record = {
                "user_id": user_id,
                "product_name": product_name,
                "model": model,
                "supplier": supplier,
                "price": price,
                "currency": currency,
                "date": date_val,
                "source_file": source_file,
                "embedding": vector
            }

            res = supabase.table("products").insert([record]).execute()
            if res.data:
                prod = res.data[0]
                inserted_records.append(prod)
                supabase.table("price_history").insert([{
                    "product_id": prod["id"],
                    "price": price,
                    "currency": currency
                }]).execute()

        return jsonify({
            "message": f"{len(inserted_records)} products successfully processed and saved",
            "count": len(inserted_records),
            "products": inserted_records
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500