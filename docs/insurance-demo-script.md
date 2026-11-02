# EasyDigi DocFlow Insurance: 6-Minute Live Pitch & Demo Script

**Role:** Solution Architect / Product Lead  
**Tone:** Technical, confident, precision-oriented, compliance-first  
**Target Audience:** CIO / Head of Digital Transformation / TPA Operations Head  

---

## Act 1: The Insurance Claim Friction (0:00 - 1:00)
- **Problem Statement:** In India, filing an insurance claim today requires repetitive physical scanning, dripping document requests from TPAs over WhatsApp or email, and unencrypted transfer of Aadhaar numbers and medical reports.
- **EasyDigi Solution:** A deterministic, privacy-first claim orchestration platform built alongside mock DigiLocker identity verification and device-side encrypted vaults.
- **Screen:** Open Bank Desk at `http://localhost:3000/insurance`. Show the 5 pre-seeded scenarios covering clean cashless, bill mismatch, lapsed policy, missing police untraceable reports, and nominee name disputes.

---

## Act 2: Intimate Claim & Mobile Device Vault (1:00 - 2:30)
- **Demo Action:** Enter Claim `#CLM-HLT-2024-8801` (Rajan Nair) and generate a signed, expiring customer intake link.
- **Mobile Experience:** Navigate to `http://localhost:3001/claim/{token}`.
- **Agent Chat:** Show conversational guidance in Hindi/Hinglish/English. The agent explains required documents for `health_cashless` (pre-auth form, hospital ID, diagnostic report).
- **Hard Rule #1 & #3 in Action:** Notice the agent never accepts full Aadhaar numbers in chat.
- **Device Vault:** Click "📁 Vault" (`/claim/{token}/vault`).
  - Demonstrate WebCrypto **AES-256-GCM** client-side encryption. The server receives ciphertext only; metadata contains opaque UUIDs.
  - Show the "Works Offline" banner and queue synchronization.

---

## Act 3: Hybrid Encrypted Share & Pre-Auth SLA (2:30 - 3:45)
- **Bank View:** Return to `http://localhost:3000/insurance/claims/{token}/share`.
- **Hybrid Encryption:** Click "Assemble & Encrypt Package". Manifest is sealed with AES-256-GCM, and the AES key wrapped via RSA-OAEP with the insurer's public key.
- **Pre-Auth Trigger:** Click "Request Cashless Pre-Auth". An instantaneous 1-hour regulatory SLA deadline is initialized.
- **Timeline Engine:** Navigate to `/timeline`. Demonstrate how SLAs (`pre_auth_decision`, `survey_report`, `settlement`) transition from `RUNNING` to `AT_RISK` and `BREACHED`.

---

## Act 4: Deterministic Coverage & Fraud Guardrails (3:45 - 5:00)
- **Navigation:** Open `/review`.
- **Consistency Checks:** Click "Run Consistency & Fraud Checks".
  - Show Scenario B (`CLM-HLT-2024-8802`): Detects 10% discrepancy between hospital bill and discharge summary.
  - **Hard Rule #4 & #5 in Action:** Flags are surfaced for human review only—**never automatic AI rejection**. Notice the single consolidated query prompt instead of drip requests.
- **Deterministic Python Engine:** Click "Compute Deterministic Coverage".
  - Code (not LLM) evaluates policy status, incident date range, waiting periods, and deductible/co-pay caps.
  - Shows clear calculation: `₹50,000 Requested - ₹5,000 Deductible - 10% Co-Pay = ₹40,500 Final Payable`.
- **Human Decision:** Click "Approve Claim" as an authorized human officer.

---

## Act 5: Settlement, Ombudsman & Wrap-up (5:00 - 6:00)
- **Navigation:** Open `/settlement`.
- **NEFT Payout:** Input bank account last-4 (`5678`). Click "Process NEFT Payout". Instant mock UTR (`UTR202611...`) generated; claim moves to `SETTLED`.
- **Grievance Handling:** Show that rejected claimants (e.g. Scenario C: Lapsed policy) can directly register a grievance with the Insurance Ombudsman with full PII scrubbing before audit logging.
- **Closing:** DocFlow Insurance delivers regulatory compliance, zero raw PII leakage, and end-to-end cryptographic proof from bedside to bank payout.
