# DocFlow Insurance: 10 Antigravity Build Prompts

Build this after the bank (loan) version is done. It runs inside the same DocFlow project and reuses the vault, mock DigiLocker, consent share, agent chat and audit log from the bank build.

## Insurance Master Context

**Project:** DocFlow Insurance, a module inside the existing DocFlow monorepo (Next.js PWA + FastAPI + Postgres/SQLite + Redis). A policyholder files a claim through a consent link; an AI agent guides evidence and document collection in Hindi/English/Hinglish; documents live in the user's encrypted device vault; the insurer or TPA receives only the documents the user consents to; departments get their slice with a cited summary; coverage is decided by deterministic code; humans decide claims.

**REUSE, DO NOT REBUILD:** DigiLockerProvider (mock), LLMProvider, OCRProvider, StorageProvider, vault (WebCrypto AES-256-GCM), consent share with hybrid encryption, RBAC, maker-checker, audit log, retention job.

**HARD RULES (every prompt):**
1. Never collect real Aadhaar/OTP in our UI; official or mock-labelled DEMO ONLY pages only. No scraping or automation of DigiLocker.
2. Never store full Aadhaar, passwords, PINs, OTPs, or full bank account numbers (mask to last 4).
3. The LLM never sees raw files, tokens, or unmasked identifiers.
4. The LLM never decides coverage or approves/rejects a claim. Code computes coverage; humans decide. Fraud signals are FLAGS for human review, never automatic rejection.
5. Insurer must ask for all missing documents in ONE consolidated query, not in drips.
6. All policy rules, timelines and sample values are SAMPLE CONFIG for the demo, not any insurer's real terms.
7. Medical and accident data is sensitive: minimum necessary sharing, consent per claim, masked logs, auto-retention.
8. Every prompt: tests, README update, then STOP and wait for my approval.

---

## Prompt 1: Claim domain model, claim types and seed data
**GOAL:** Extend the data model and config for insurance claims.

**TASKS:**
1. New tables: `policies` (number, holder, product type, start/end dates, sum_insured, deductible, co_pay_pct, waiting_period_days, status), `claims` (type, status, incident_date, intimation_at, policy_id), `claim_documents`, `claim_events` (timeline), `deadlines`, `coverage_results`, `fraud_flags`, `claim_tasks`, `settlements`.
2. Claim types in YAML config: `health_cashless`, `health_reimbursement`, `motor_own_damage`, `motor_theft`, `life_death`. For each: required documents, optional documents, departments involved, and deadlines (SAMPLE VALUES: health intimation 48h, reimbursement docs 15 days after discharge, motor docs 15 days, motor survey report 15 days, settlement 30 days).
3. Seed 5 fictional policyholders and policies:
   - (a) clean health cashless
   - (b) health reimbursement with itemised bill total not matching discharge summary
   - (c) motor claim with incident date outside policy period
   - (d) motor claim with missing FIR and photos
   - (e) life death claim with nominee name mismatch
4. Seed sample PDFs/images and JSON metadata for each.
5. Update the architecture diagram in `/docs/architecture.md` with the insurance module.

**ACCEPTANCE:** migrations run; seed loads; claim-type config validates with a schema test; README updated.

---

## Prompt 2: Mock policy provider and identity sources
**GOAL:** Provide policy data and identity documents through swappable providers.
- PolicyProvider interface: `get_policy(policy_number, holder_ref)`
- MockPolicyProvider from seed data, InsurerApiProvider stub with TODOs
- Reuse MockDigiLockerProvider for ID proof (PAN, masked Aadhaar, DL, RC)
- Policy verification: belongs to holder, active, incident within policy period
- Failure modes: lapsed policy, wrong holder, policy not found

---

## Prompt 3: Claim intake agent
**GOAL:** A tool-calling agent that guides intimation and document collection by chat (`/claim/{token}`).
- Mobile-first chat, signed expiring link
- Agent tools: `get_claim_status`, `detect_claim_type`, `get_required_documents`, etc.
- Multi-scenario checklists: Motor 20-30 photos guide, Health cashless vs reimbursement, Death claim sensitive tone.

---

## Prompt 4: Evidence capture and document processing
**GOAL:** Capture good evidence and turn claim documents into structured, masked data.
- Camera overlays (blur/crop detection), multi-page PDF merger, 19 document classifiers.
- OCR metadata extraction & prompt injection guard.

---

## Prompt 5: Claim vault (device-side)
**GOAL:** Extend the encrypted vault for claims, including use at the scene.
- 'Claims' vault folder, offline-first sync, 'Originals checklist', Policy wallet.

---

## Prompt 6: Insurer request, consent and claim package
**GOAL:** Share a claim with the insurer or TPA by consent, in one encrypted package.
- `/share/claim/{token}`, hybrid encryption (AES-256-GCM + RSA-OAEP), pre-auth for cashless.

---

## Prompt 7: Deadline and timeline engine
**GOAL:** Track every claim deadline and make delays visible.
- Timelines driven by YAML: cashless pre-auth (1 hr), final authorization (3 hrs), surveyor (24h/15d), settlement (30d).

---

## Prompt 8: Insurer ingestion, consistency checks and fraud flags
**GOAL:** Decrypt, validate and flag claim files for human review.
- Bill vs summary cross-checks, fraud flags (never auto-reject), one-shot consolidated query.

---

## Prompt 9: Departments, coverage engine and approvals
**GOAL:** Route claim slices to departments, compute coverage in code, and let humans decide.
- Departments: Claims Intake, Medical/TPA, Surveyor, Fraud/SIU, Payments.
- Deterministic coverage engine in Python with YAML rules. Cited summaries with source references.

---

## Prompt 10: Settlement, grievance, security, demo and pitch
**GOAL:** Finish the loop and make the insurance module demo-ready and credible.
- Settlement UTR, Ombudsman escalation, threat model, 6-minute demo script, pitch assets.
