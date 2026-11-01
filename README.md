# DocFlow: Wish Pack of Djinn, the AI Action Agent

DocFlow is a privacy-first lending document verification platform and the first **Wish Pack** of **Djinn, the AI Action Agent**.

---

## What is Real vs. What is Mocked

| Component | Status | Details |
|---|---|---|
| **Deterministic Eligibility Engine** | **REAL** | Pure Python code evaluates loan parameters without LLM decision dependency. |
| **Cross-Check Engine** | **REAL** | Tokenized fuzzy name and initial matching across documents. |
| **Hybrid Crypto & Package Exchange** | **REAL** | Authenticated RSA-OAEP 2048 + AES-256-GCM encryption and digest verification. |
| **PII Scrubbing Logger** | **REAL** | Regex interceptor continuously redacting Aadhaar, PAN, tokens, and OTPs. |
| **Maker-Checker RBAC** | **REAL** | Department isolation and self-approval prevention enforced. |
| **Wish Link Engine & Ledger** | **REAL** | 24h signed single-use links, bulk summoning, and immutable ledger with hashed IPs. |
| **DigiLocker / Aggregator** | **MOCKED** | OAuth 2.0 PKCE flow labeled **DEMO ONLY**; `AggregatorProvider` stub ready for production keys. |
| **OCR Provider** | **MOCKED** | Synthetic field extractor matching seed profiles; interface ready for AWS Textract/Tesseract. |
| **LLM Provider** | **HYBRID** | MockLLMProvider with deterministic fallback + Gemini adapter ready when `GEMINI_API_KEY` is provided. |

---

## Production Deployment Guide (Step-by-Step)

### A. Environment Architecture
- **Apps**: FastAPI Backend (`/apps/api`) and Next.js PWA Frontend (`/apps/web`).
- **Data Layer**: PostgreSQL 16+ and Redis 7+.

### B. Manual Inputs Required for Production
1. **Domain Names & SSL**:
   - `api.yourdomain.com` (pointing to FastAPI)
   - `app.yourdomain.com` (pointing to Next.js)
2. **Environment Secrets (`.env`)**:
   - `DATABASE_URL`: `postgresql+asyncpg://<user>:<password>@<db-host>:5432/<dbname>`
   - `REDIS_URL`: `redis://<redis-host>:6379/0`
   - `VAULT_SECRET_KEY`: Generate a random 32-character key (`openssl rand -hex 16`)
   - `DIGILOCKER_PROVIDER`: Set to `real`
   - `DIGILOCKER_CLIENT_ID`: Issued by API Setu or TSP
   - `DIGILOCKER_CLIENT_SECRET`: Issued by API Setu or TSP
   - `DIGILOCKER_REDIRECT_URI`: `https://api.yourdomain.com/api/v1/auth/digilocker/callback`
   - `GEMINI_API_KEY` (or `ANTHROPIC_API_KEY`): Production LLM API key
   - `NEXT_PUBLIC_API_URL`: `https://api.yourdomain.com/api/v1`

### C. Deployment Options

#### Option 1: Docker Compose (VM or AWS EC2)
```bash
# 1. Clone repository
git clone <repo-url> EasyDigi && cd EasyDigi

# 2. Populate .env file in infra/
cp infra/.env.example infra/.env
# Edit infra/.env with your production secrets

# 3. Launch multi-container stack
docker compose -f infra/docker-compose.yml up -d --build
```

#### Option 2: Managed Cloud (Render / Railway / AWS ECS + Vercel)
1. **Database & Redis**: Deploy managed PostgreSQL (AWS RDS or Supabase) and Redis (AWS ElastiCache or Upstash).
2. **Backend API**:
   - Connect repository to Railway/Render/AWS App Runner pointing to `apps/api`.
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. **Frontend PWA**:
   - Connect repository to Vercel pointing to `apps/web`.
   - Set environment variable `NEXT_PUBLIC_API_URL=https://api.yourdomain.com/api/v1`.

---

## Quickstart & Local Testing
```bash
# Run FastAPI Backend
cd apps/api
pip install -e .
python scripts/seed.py
uvicorn app.main:app --reload --port 8000

# Run Next.js Frontend
cd ../../apps/web
npm install
npm run dev
```

### Running Test Suite
```bash
cd apps/api
pytest -v
```
All **36 tests** pass.
