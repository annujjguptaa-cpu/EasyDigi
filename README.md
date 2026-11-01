# EasyDigi — AI-Powered Lending Document Platform

> Two clearly separate experiences, one seamless workflow.

---

## 2-Minute Demo Script

**Open two tabs (or two devices):**

### Tab 1 — Bank Dashboard
1. Go to **http://localhost:3000/bank/login**
2. Click **employee@apexbank-demo.com** from the quick-select list → Sign In
3. You land on the **Cases Dashboard** — see existing cases, notification bell in top-right
4. Click **NEW REQUEST** (top-right)
5. Fill in: Name = `Test Customer`, Phone = `XXXXXX9901`, Loan Type = `Home Loan`, tick all documents, Expiry = 24h
6. Click **Create Request** → a secure link appears with Copy, WhatsApp, and SMS buttons
7. **Copy the link** (or note it — it looks like `http://localhost:3000/c/xxxx...`)

### Tab 2 (Incognito) — Customer Link
1. Paste the copied link into the incognito tab
2. Read the consent screen → click **I AGREE & CONTINUE**
3. You see the **DEMO ONLY** DigiLocker page — pick **Rahul Verma (Clean profile)**
4. Watch documents appear with green status dots
5. Click **All looks good → Submit**
6. See **"Documents submitted successfully!"** with the case reference

### Back to Tab 1
- The **notification bell** shows a new badge (or a toast pops up)
- Open the notification panel — you see: "link opened", "consent given", "documents received"
- Click into the case → see the full **timeline**, **documents**, and **readiness score**
- Click **SEND TO DEPARTMENTS** → select all departments → confirm
- Navigate to **Departments** tab → see per-department status cards
- Log out → log in as `credit_head@apexbank-demo.com` → see the final eligibility result

---

## Architecture

```
apps/
  web/           Next.js 14 frontend  (port 3000)
    /bank/*      Bank dashboard (staff login required)
    /c/[token]   Customer link (no login, mobile-first)
    /vault        Document vault
    /design       Design system reference
  api/           FastAPI backend       (port 8000)
    /api/v1/bank/*      Bank staff endpoints (RBAC)
    /api/v1/c/*         Customer token endpoints (public)
    /api/v1/wishes/*    Djinn Wish Pack
    /api/v1/digilocker/ Mock DigiLocker OAuth2
packages/
  ui/            Shared React components
  contracts/     Shared TypeScript types & i18n
```

### State Machine
```
link_created → link_opened → consent_given → documents_received
→ ready_for_review → sent_to_departments → in_review
→ query_raised → decided
```
Every transition writes an **AuditLog** row and emits a **Notification** event to the relevant bank employee.

---

## Setup & Run (Local)

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### Backend
```powershell
cd apps/api
pip install -r requirements.txt
# (Optional) set PUBLIC_BASE_URL in .env
python scripts/seed.py        # seeds DB + staff + demo case
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Docs: http://127.0.0.1:8000/docs

### Frontend
```powershell
cd apps/web
npm install
npm run dev
```
App: http://localhost:3000

---

## Deploy Guide

### Environment Variables

**Backend** (create `apps/api/.env`):
```env
PUBLIC_BASE_URL=https://your-domain.com
ENVIRONMENT=production
DATABASE_URL=sqlite+aiosqlite:///./easydigi.db
VAULT_SECRET_KEY=<32-char-random-string>
DIGILOCKER_PROVIDER=mock
LLM_PROVIDER=mock
```

**Frontend** (create `apps/web/.env.local`):
```env
NEXT_PUBLIC_API_URL=https://your-api-domain.com/api/v1
```

### Option A — Localhost with a tunnel (quickest demo)
```powershell
# Install cloudflared or ngrok, then:
# Terminal 1: backend
cd apps/api; uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2: frontend  
cd apps/web; npm run dev

# Terminal 3: tunnel for the frontend
cloudflared tunnel --url http://localhost:3000
# or: ngrok http 3000

# Copy the tunnel URL (e.g. https://abc.trycloudflare.com)
# Set PUBLIC_BASE_URL=https://abc.trycloudflare.com in apps/api/.env
# Restart backend
```

### Option B — Vercel + Railway
1. **Backend → Railway**
   - Connect GitHub repo, select `apps/api` as root
   - Set env vars: `PUBLIC_BASE_URL`, `DATABASE_URL`, `VAULT_SECRET_KEY`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

2. **Frontend → Vercel**
   - Connect GitHub repo, select `apps/web` as root
   - Build command: `npm run build`
   - Output dir: `.next`
   - Set env var: `NEXT_PUBLIC_API_URL=https://<railway-url>/api/v1`

### Option C — Docker Compose
```yaml
# docker-compose.yml (place at repo root)
version: '3.9'
services:
  api:
    build: ./apps/api
    environment:
      - PUBLIC_BASE_URL=http://localhost:3000
    ports: ["8000:8000"]
  web:
    build: ./apps/web
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
    ports: ["3000:3000"]
    depends_on: [api]
```

---

## Seeded Demo Accounts

### Bank Staff
| Email | Role | Department | Password |
|-------|------|------------|---------|
| employee@apexbank-demo.com | Relationship Employee | KYC | demo1234 |
| kyc_officer@apexbank-demo.com | KYC Officer | KYC | demo1234 |
| credit_manager@apexbank-demo.com | Credit Manager | CREDIT | demo1234 |
| credit_head@apexbank-demo.com | Credit Head | CREDIT | demo1234 |
| risk_analyst@apexbank-demo.com | Risk Analyst | RISK | demo1234 |
| legal_officer@apexbank-demo.com | Legal Officer | LEGAL | demo1234 |
| tech_officer@apexbank-demo.com | Technical Officer | TECHNICAL | demo1234 |
| ops_specialist@apexbank-demo.com | Operations | OPERATIONS | demo1234 |

### Customer Profiles (Demo DigiLocker)
| Profile Key | Name | Scenario |
|------------|------|----------|
| clean_file | Rahul Verma | All documents present & verified |
| name_mismatch | Priya S. Sharma | Name differs between PAN and Aadhaar |
| missing_docs | Amit Patel | Only PAN present |

### Pre-seeded Demo Case
- Customer link: http://localhost:3000/c/demo-clean-token-00000001
- Reference: CASE-DEMO-0001

---

## Security Hard Rules (never violate)
1. Never collect real Aadhaar/OTP — only official aggregator redirect or clearly labeled DEMO ONLY
2. Never persist full Aadhaar — max last 4 digits in DB and logs
3. LLM never sees raw files, tokens, or full PII — masked JSON only
4. Chat guardrails strip 12-digit numbers and OTP strings before LLM
5. Code decides eligibility — LLM only explains/cites
6. Djinn vocabulary for titles/buttons/states only — consent and legal text stays plain literal

---

## Djinn Vocabulary Reference

| Standard term | Djinn term |
|---|---|
| Request | Wish |
| Create request | SUMMON YOUR DJINN |
| Shared link | /wish/{token} |
| Agent working | "Djinn is working..." |
| Completion | "Your wish is granted" |
| Home Loan | Foundation Wish |
| Education Loan | Scholar Wish |
| Personal Loan | Opportunity Wish |
| Business Loan | Growth Wish |
| 01 Consent | 01 WISH |
| 02 Documents | 02 DOCUMENTS |
| 03 Checks | 03 CHECKS |
| 04 Departments | 04 DEPARTMENTS |
| 05 Result | 05 VERDICT |

---

## Running Tests
```powershell
cd apps/api
python -m pytest tests/ -v
```

36 backend tests covering eligibility, PII logging, prompt injection, department workflow, wishes, consent slices, and the new bank/customer API.
