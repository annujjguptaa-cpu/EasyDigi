# DocFlow Threat Model & Security Architecture

## 1. Trust Boundaries & Principles
- **Customer Device Vault**: Documents reside in the user's client-side encrypted vault. Raw files are never stored unencrypted on servers.
- **Simulated Aggregator Boundary**: Clearly labelled **"DEMO ONLY, not the real DigiLocker"**. Accepts synthetic inputs without persistence.
- **LLM Isolation Boundary**: The LLM provider (Gemini/Claude) only sees masked JSON fields. Never receives raw document bytes, full tokens, or unmasked identifiers.
- **Deterministic Code Invariant**: Code decides eligibility; LLM explains and cites code output.

---

## 2. Threat Scenarios & Mitigations

| Threat Vector | Severity | Mitigation Implemented |
|---|---|---|
| **Aadhaar / PII Harvesting in UI** | Critical | Real flow redirects to official aggregator. Mock UI is clearly labeled DEMO ONLY. Full Aadhaar / OTPs are discarded immediately without saving. |
| **Token Theft & Replay** | High | Single-use authorization codes. Replayed or expired codes are rejected immediately. Tokens are kept in memory and filtered from all log output. |
| **Cross-Department Data Exposure** | High | Strict RBAC and routing tables. KYC staff cannot access income documents; Credit cannot access unneeded identity blobs. |
| **Prompt Injection via Uploaded Documents** | High | Adversarial instructions (`ignore previous instructions`) are sanitized via `ThreatModelSecurityAudit`. Extracted text is treated strictly as data, never as prompt instructions. |
| **Maker Self-Approval (Fraud / Collusion)** | High | Maker-checker state machine strictly prevents the maker from approving their own task. |
| **Package Tampering in Transit** | High | Authenticated AES-256-GCM + RSA-OAEP hybrid encryption. Mismatched SHA-256 digests trigger immediate package rejection. |
