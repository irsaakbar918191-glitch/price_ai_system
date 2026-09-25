import csv
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pdfplumber
import pytesseract
from PIL import Image


def _resolve_tesseract_cmd() -> str | None:
    configured = os.getenv("TESSERACT_CMD", "").strip()
    if configured:
        return configured

    resolved = shutil.which("tesseract")
    if resolved:
        return resolved

    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


pytesseract.pytesseract.tesseract_cmd = _resolve_tesseract_cmd() or "tesseract"


class FileParser:
    @staticmethod
    def allowed_file(filename: str) -> bool:
        ext = Path(filename).suffix.lower().lstrip('.')
        return ext in {"pdf", "png", "jpg", "jpeg", "xlsx", "xls", "csv"}

    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        text_chunks: List[str] = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    text_chunks.append(text)
        except Exception:
            return ""
        return "\n".join(text_chunks)

    @staticmethod
    def extract_text_from_image(file_path: str) -> str:
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text
        except Exception:
            return ""

    @staticmethod
    def extract_text_from_excel(file_path: str) -> str:
        try:
            df = pd.read_excel(file_path)
            return df.to_string(index=False)
        except Exception:
            try:
                df = pd.read_csv(file_path)
                return df.to_string(index=False)
            except Exception:
                return ""

    @staticmethod
    def extract_text_from_csv(file_path: str) -> str:
        try:
            with open(file_path, newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)
                return "\n".join([",".join(row) for row in rows])
        except Exception:
            return ""

    @staticmethod
    def extract_text(file_path: str) -> str:
        file_ext = Path(file_path).suffix.lower()
        if file_ext == ".pdf":
            return FileParser.extract_text_from_pdf(file_path)
        if file_ext in {".png", ".jpg", ".jpeg"}:
            return FileParser.extract_text_from_image(file_path)
        if file_ext in {".xlsx", ".xls"}:
            return FileParser.extract_text_from_excel(file_path)
        if file_ext == ".csv":
            return FileParser.extract_text_from_csv(file_path)
        return ""

    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        text = text.replace('\r', '\n')
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @staticmethod
    def parse_price_data(raw_text: str) -> Dict[str, Any]:
        normalized = raw_text or ""
        date_match = re.search(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{4}/\d{2}/\d{2})', normalized)
        date_value = ""
        if date_match:
            date_text = date_match.group(1)
            try:
                if '-' in date_text:
                    date_value = datetime.strptime(date_text, '%Y-%m-%d').strftime('%Y-%m-%d')
                elif '/' in date_text and len(date_text.split('/')[0]) == 2:
                    date_value = datetime.strptime(date_text, '%d/%m/%Y').strftime('%Y-%m-%d')
                elif '/' in date_text and len(date_text.split('/')[0]) == 4:
                    date_value = datetime.strptime(date_text, '%Y/%m/%d').strftime('%Y-%m-%d')
            except Exception:
                date_value = ""

        price_match = re.search(r'(?:PKR|USD|EUR|GBP|AED|SAR|INR|CAD|AUD|TAX|Rs\.?|Rs\s*)\s*([0-9,]+\.?[0-9]*)', normalized, re.IGNORECASE)
        price_value = 0.0
        if price_match:
            cleaned = price_match.group(1).replace(',', '')
            try:
                price_value = float(cleaned)
            except ValueError:
                price_value = 0.0

        currency_match = re.search(r'\b(PKR|USD|EUR|GBP|AED|SAR|INR|CAD|AUD)\b', normalized, re.IGNORECASE)
        currency = "PKR"
        if currency_match:
            currency = currency_match.group(1).upper()

        return {
            "price": price_value,
            "currency": currency,
            "date": date_value,
        }
