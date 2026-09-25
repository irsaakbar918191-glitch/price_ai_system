# AI-Powered Smart Price Database & RAG Search System

A zero-cost, multi-tenant Flask-based price intelligence system that:
- ingests product documents (PDF, image, Excel, CSV),
- extracts product metadata with a local OCR + LLM pattern,
- stores embeddings locally with SentenceTransformers,
- searches with Supabase pgvector cosine similarity,
- serves authenticated admin/user flows via Flask and Supabase Auth.

## Stack
- Backend: Python 3.10+, Flask
- Frontend: HTML5 + Tailwind CDN + Vanilla JavaScript
- Database: Supabase PostgreSQL with pgvector
- Auth: Supabase Auth + JWT
- OCR: Tesseract + Pillow + pdfplumber
- Embedding model: sentence-transformers/all-MiniLM-L6-v2
- LLM extraction: free Hugging Face Inference API (token-based, no OpenAI dependency)

## Folder Structure
See the generated project layout under the root folder.

## 1) Create Virtual Environment

Windows (PowerShell):
```powershell
cd path\to\price-ai-system
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Linux/macOS:
```bash
cd /path/to/price-ai-system
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 2) Install Tesseract OCR

Windows:
- Download and install Tesseract OCR from: https://github.com/UB-Mannheim/tesseract/wiki
- Add the install folder such as `C:\Program Files\Tesseract-OCR` to PATH.
- Verify with:
```powershell
tesseract --version
```
- If `tesseract` is not recognized, set the exact path in `.env`:
```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

Linux (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr
```

macOS:
```bash
brew install tesseract
```

If Tesseract is already installed and available on PATH, you do not need to set `TESSERACT_CMD` at all.

## 3) Configure Environment

Copy the example file:
```bash
copy .env.example .env
```

For testing without setting `TESSERACT_CMD`, first verify the binary exists system-wide:
```powershell
where.exe tesseract
```
If it prints a valid path, the app will auto-detect it. If not, configure the full path manually as shown above.

Then fill in your actual values.

Example:
```env
SECRET_KEY=super_secure_key
FLASK_ENV=development
PORT=5000
DEBUG=True

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

HF_API_TOKEN=your_huggingface_token
HF_MODEL=mistralai/Mistral-7B-Instruct-v0.2

UPLOAD_FOLDER=uploads
DEFAULT_CURRENCY=PKR
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## 4) Supabase Setup

1. Create a new Supabase project.
2. Go to SQL Editor and run the contents of `database/schema.sql`.
3. Enable `pgvector` in your project.
4. Ensure `auth.users` trigger exists for default role insertion.
5. Set table permissions or RLS as in the provided SQL.
6. Create a Supabase Auth user for testing your admin account.

## 5) Run Database Migration / Setup

Open the SQL editor in Supabase and execute:
```sql
-- execute the contents of database/schema.sql
```

If you use a local PostgreSQL instance, you can also run the file with psql.

## 6) Launch the App

From the project root:
```bash
python app.py
```

Then open:
- http://localhost:5000/
- http://localhost:5000/login

## 7) API Overview

### Login
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"secret"}'
```

### Upload Product (Admin Only)
```bash
curl -X POST http://localhost:5000/api/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@sample.pdf"
```

### Search Product (Authenticated User)
```bash
curl -X POST http://localhost:5000/api/search \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"Samsung 55 inch TV ki price kya hai?"}'
```

### Product History
```bash
curl http://localhost:5000/api/history/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Notes
- This app avoids all OpenAI dependencies and uses local embeddings plus free Hugging Face inference API keys.
- The vector search is performed with pgvector cosine similarity.
- The OCR and extraction logic is resilient and will gracefully return safe fallback values.
