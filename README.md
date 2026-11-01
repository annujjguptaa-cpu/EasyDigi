# EasyDigi — Three Web Apps + Shared Backend Architecture

> Seamless AI-Powered Lending Verification distributed across three dedicated Next.js applications and a FastAPI backend.

---

## Architecture Overview

```
apps/
  bank/            Port 3000 — Bank Staff Dashboard & Maker-Checker RBAC
  customer/        Port 3001 — Customer "Wish" Portal (Zero bank UI visible)
  mock-digilocker/ Port 3002 — Simulated DigiLocker (Labelled "DEMO ONLY" on every screen)
  api/             Port 8000 — Shared FastAPI Engine & Event Bus
```

### Environment Variables
All apps and generated links are config-driven via four core variables:
- `BANK_URL` (default: `http://localhost:3000`)
- `CUSTOMER_URL` (default: `http://localhost:3001`)
- `DIGILOCKER_URL` (default: `http://localhost:3002`)
- `API_URL` (default: `http://localhost:8000/api/v1`)

---

## 2-Minute Demo Script

Follow this step-by-step walkthrough to demonstrate the full end-to-end flow:

### Tab 1 — Bank Dashboard (Port 3000)
1. Open **http://localhost:3000/login**
2. Select **employee@apexbank-demo.com** (Relationship Employee) &rarr; **Sign In**.
3. You start with a **clean slate** (zero cases).
   *(Note: Bank admins have a red "Reset Demo Data" button to clear cases at any time).*
4. Click **`+ NEW REQUEST`** in the top right.
5. Fill in:
   - **Customer Name:** `Rahul Verma`
   - **Masked Mobile:** `XXXXXX9921`
   - **Product:** `Home Loan`
   - **Required Documents:** Select PAN, Aadhaar, Salary Slip, Bank Statement.
6. Click **`SUMMON SECURE LINK`**.
7. Click **`COPY LINK`** (the link is generated as `http://localhost:3001/w/{token}`).

### Tab 2 — Customer Wish Page (Port 3001)
1. Open a new or incognito browser tab and paste the customer link: `http://localhost:3001/w/{token}`.
2. Note that **zero bank or staff screens are visible**; the borrower sees only their bank branding and requested document checklist.
3. Mandatory documents (PAN & Aadhaar) are locked; optional documents are selectable.
4. Click the primary action: **`SUMMON THE DJINN →`**.
5. The customer is redirected seamlessly to the Mock DigiLocker consent gateway.

### Tab 3 — Mock DigiLocker Sandbox (Port 3002)
1. You land on the **DEMO ONLY** consent screen (`http://localhost:3002/consent?...`).
2. Notice the universal red **`⚠ DEMO ONLY, NOT THE REAL DIGILOCKER`** banner on top of the page.
3. Click **`Allow Access`**.
4. You are redirected back to **Tab 2** (Customer App) displaying:
   - **`Your Wish is Granted`**
   - Verified digital records retrieved with timestamps and issuers
   - Monospace case reference code
   - Option to "Save to My Vault"

### Live Real-Time Updates
- **Return to Tab 1 (Bank Dashboard):**
  - The notification bell flashes with a new unread badge: **`Wish granted: 3 documents received`**.
  - Open the case &rarr; review the timeline, readiness score, and masked fields.
  - Click **`SEND TO DEPARTMENTS`** to dispatch scoped slices to KYC, Credit, Risk, and Operations.
- **Return to Tab 3 (Mock DigiLocker):**
  - Visit `http://localhost:3002/activity` &rarr; observe the new entry: **`Apex Mutual Bank accessed 3 documents`**.
  - In "Active Institutional Consents", click **`Revoke Consent`** &rarr; instantly notifies the bank dashboard and starts the 24-hour retention deletion clock.

---

## Running the Entire System Locally

### Option 1: One-Command Startup
Make sure dependencies are installed, then run from the repository root:
```powershell
npm run dev:all
```
This boots all four services simultaneously:
- FastAPI Backend: `http://localhost:8000`
- Bank Dashboard: `http://localhost:3000`
- Customer Portal: `http://localhost:3001`
- Mock DigiLocker: `http://localhost:3002`

### Option 2: Individual Terminals
```powershell
# Terminal 1: API
cd apps/api; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Bank Dashboard
cd apps/bank; npm run dev -- -p 3000

# Terminal 3: Customer App
cd apps/customer; npm run dev -- -p 3001

# Terminal 4: Mock DigiLocker
cd apps/mock-digilocker; npm run dev -- -p 3002
```

### Option 3: Docker Compose
```powershell
docker compose up --build
```

---

## Multi-Domain Deployment Notes
When deploying to 3 distinct domains (e.g. `bank.yourbank.com`, `verify.yourbank.com`, `digilocker-mock.yourbank.com`):

1. **Backend (`apps/api/.env`)**:
   ```env
   BANK_URL=https://bank.yourbank.com
   CUSTOMER_URL=https://verify.yourbank.com
   DIGILOCKER_URL=https://digilocker-mock.yourbank.com
   API_URL=https://api.yourbank.com/api/v1
   ```
2. **Bank Frontend (`apps/bank/.env.local`)**:
   ```env
   NEXT_PUBLIC_BANK_URL=https://bank.yourbank.com
   NEXT_PUBLIC_CUSTOMER_URL=https://verify.yourbank.com
   NEXT_PUBLIC_DIGILOCKER_URL=https://digilocker-mock.yourbank.com
   NEXT_PUBLIC_API_URL=https://api.yourbank.com/api/v1
   ```
3. **Customer Frontend (`apps/customer/.env.local`)**:
   ```env
   NEXT_PUBLIC_API_URL=https://api.yourbank.com/api/v1
   NEXT_PUBLIC_DIGILOCKER_URL=https://digilocker-mock.yourbank.com
   ```
4. **Mock DigiLocker (`apps/mock-digilocker/.env.local`)**:
   ```env
   NEXT_PUBLIC_API_URL=https://api.yourbank.com/api/v1
   ```

---

## Automated Test Suite
To verify the full end-to-end integration across all applications and modules:
```powershell
cd apps/api
python -m pytest tests/ -v
```
All **56 tests** pass, covering:
- Clean slate validation (zero initial cases)
- Single-use and 24h link expiration (410 Gone)
- Selective document granting & consent locking
- Inter-app notification dispatch on `wish_granted` and `wish_partial`
- DigiLocker consent revocation and retention clock trigger
- Department maker-checker RBAC isolation
- Insurance claim domain models & schema validation
- 5 fictional policyholder insurance claim seed scenarios
- MockPolicyProvider verification, failure modes, and swappable provider interface
- Claim intake conversational agent (/claim/{token}), tool calling, Aadhaar stripping guardrails, and single-shot consolidated queries



---

## DocFlow Insurance Module
The insurance module operates alongside the loan verification flow, sharing the core zero-knowledge vault, mock DigiLocker identity provider, and deterministic processing engine.

### 5 Supported Claim Types
1. **Health Cashless (`health_cashless`)**: Emergency/planned hospitalization with 1h pre-auth & 3h final authorization.
2. **Health Reimbursement (`health_reimbursement`)**: Post-discharge claims with cross-checks between bills and discharge summaries.
3. **Motor Own Damage (`motor_own_damage`)**: Accident claims with scene photos, driving license, and surveyor dispatch.
4. **Motor Theft (`motor_theft`)**: Total loss claims requiring certified FIR and Untraceable Final Report.
5. **Life Insurance Death Claim (`life_death`)**: Nominee identity verification, bank mandate, and death certificate validation.

### Seed Scenarios
Seed files are located in `seed_data/insurance/`:
- `policy_clean_health`: Rajan Nair — valid cashless claim with matching identity.
- `policy_reimburse_mismatch`: Sunita Rao — itemized bill total mismatch vs discharge summary.
- `policy_motor_outside_period`: Vikram Malhotra — incident occurred outside policy coverage window.
- `policy_motor_missing_fir`: Ananya Sen — motor theft claim missing mandatory FIR and Untraceable report.
- `policy_life_nominee_mismatch`: Ramesh Gupta / Kavita Sharma — surname mismatch requiring human review.

