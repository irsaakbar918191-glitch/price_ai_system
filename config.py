import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    PORT = int(os.getenv("PORT", 5000))
    DEBUG = os.getenv("DEBUG", "True").lower() in ("1", "true", "yes")

    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()

    HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")
    HF_MODEL = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")

    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "xlsx", "xls", "csv"}
    DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "PKR")
    TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")

    # If the app ever switches to a custom JWT flow, this controls token lifetime.
    # In this project, Supabase Auth manages the real JWT expiry by dashboard config.
    JWT_ACCESS_TOKEN_TTL_DAYS = int(os.getenv("JWT_ACCESS_TOKEN_TTL_DAYS", "1"))

    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
