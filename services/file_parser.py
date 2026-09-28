import csv
import io
import re
from datetime import datetime
from PyPDF2 import PdfReader
import openpyxl
from docx import Document
from services.ai_extractor import AIExtractor

class FileParser:
    @staticmethod
    def parse_file(filename: str, file_bytes: bytes) -> list:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if ext == "csv":
            return FileParser._parse_csv(file_bytes, filename)
        elif ext in ("xlsx", "xls"):
            return FileParser._parse_excel(file_bytes, filename)
        elif ext == "pdf":
            return FileParser._parse_pdf(file_bytes, filename)
        elif ext in ("docx", "doc"):
            return FileParser._parse_docx(file_bytes, filename)
        elif ext in ("txt", "json"):
            return FileParser._parse_text(file_bytes, filename)
        elif ext in ("jpg", "jpeg", "png", "webp"):
            mime = "image/png" if ext == "png" else "image/jpeg"
            return AIExtractor.extract_from_image(file_bytes, mime, filename)
        else:
            return FileParser._parse_text(file_bytes, filename)

    @staticmethod
    def _normalize_key(key: str) -> str:
        return re.sub(r'[^a-z0-9]', '', str(key).lower().strip())

    @staticmethod
    def _extract_price(val) -> float:
        if val is None:
            return 0.0
        cleaned = re.sub(r'[^\d.]', '', str(val).replace(',', ''))
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    @staticmethod
    def _parse_csv(file_bytes: bytes, filename: str) -> list:
        content = file_bytes.decode("utf-8", errors="ignore")
        stream = io.StringIO(content)
        reader = csv.reader(stream)
        rows = list(reader)
        if not rows:
            return []

        headers = [FileParser._normalize_key(h) for h in rows[0]]
        items = []

        for row in rows[1:]:
            if not row or not any(row):
                continue
            row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
            item = FileParser._map_row(row_dict, filename)
            if item.get("product_name") and item.get("price") > 0:
                items.append(item)

        return items

    @staticmethod
    def _parse_excel(file_bytes: bytes, filename: str) -> list:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        sheet = wb.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return []

        headers = [FileParser._normalize_key(h) for h in rows[0] if h is not None]
        items = []

        for row in rows[1:]:
            if not row or not any(row):
                continue
            row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
            item = FileParser._map_row(row_dict, filename)
            if item.get("product_name") and item.get("price") > 0:
                items.append(item)

        return items

    @staticmethod
    def _map_row(row_dict: dict, filename: str) -> dict:
        name = ""
        for k in ("productname", "product", "item", "itemname", "title", "name", "description"):
            if k in row_dict and row_dict[k]:
                name = str(row_dict[k]).strip()
                break

        model = ""
        for k in ("model", "modelno", "modelnumber", "sku", "partno", "code"):
            if k in row_dict and row_dict[k]:
                model = str(row_dict[k]).strip()
                break

        supplier = ""
        for k in ("supplier", "vendor", "brand", "source", "company", "seller"):
            if k in row_dict and row_dict[k]:
                supplier = str(row_dict[k]).strip()
                break

        price = 0.0
        for k in ("price", "cost", "rate", "amount", "unitprice"):
            if k in row_dict and row_dict[k]:
                price = FileParser._extract_price(row_dict[k])
                break

        currency = "PKR"
        for k in ("currency", "curr", "cur"):
            if k in row_dict and row_dict[k]:
                currency = str(row_dict[k]).strip()
                break

        date_val = datetime.utcnow().strftime("%Y-%m-%d")
        for k in ("date", "invoicedate", "entrydate", "createdat"):
            if k in row_dict and row_dict[k]:
                try:
                    raw_d = str(row_dict[k]).split(" ")[0].strip()
                    date_val = raw_d
                except Exception:
                    pass
                break

        return {
            "product_name": name,
            "model": model,
            "supplier": supplier,
            "price": price,
            "currency": currency,
            "date": date_val,
            "source_file": filename
        }

    @staticmethod
    def _parse_pdf(file_bytes: bytes, filename: str) -> list:
        reader = PdfReader(io.BytesIO(file_bytes))
        full_text = ""
        for page in reader.pages:
            full_text += (page.extract_text() or "") + "\n"
        return AIExtractor.extract_products_from_text(full_text, filename)

    @staticmethod
    def _parse_docx(file_bytes: bytes, filename: str) -> list:
        doc = Document(io.BytesIO(file_bytes))
        full_text = "\n".join([p.text for p in doc.paragraphs])
        return AIExtractor.extract_products_from_text(full_text, filename)

    @staticmethod
    def _parse_text(file_bytes: bytes, filename: str) -> list:
        text = file_bytes.decode("utf-8", errors="ignore")
        return AIExtractor.extract_products_from_text(text, filename)