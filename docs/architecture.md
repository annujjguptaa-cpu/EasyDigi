# DocFlow System Architecture

```mermaid
flowchart TD
    subgraph Borrower["Borrower Device (Client-Side Encrypted Vault)"]
        PWA["Next.js PWA App<br/>(Client Web Crypto API)"]
        Vault[("Local Device Vault<br/>AES-GCM Encrypted")]
        PWA <--> Vault
    end

    subgraph SecurityBoundary["Strict Security & Compliance Perimeter"]
        MockDL["Mock DigiLocker / Aggregator<br/><b>'DEMO ONLY, NOT REAL DIGILOCKER'</b><br/>PKCE OAuth 2.0 Flow<br/>Accepts dummy 12-digit & OTP 123456<br/>NEVER STORES FULL AADHAAR / OTP"]
        Filter["PII-Masking Filter<br/>Logs & Payloads Scrubbed<br/>(Max 4 digits of Aadhaar/PAN)"]
    end

    subgraph BackendAPI["DocFlow Backend API (FastAPI)"]
        AuthRouter["OAuth / Auth Router"]
        ConsentEngine["Consent & Scope Engine<br/>(consent_logs immutable trail)"]
        DocService["Document Ingestion<br/>Masked Metadata Only"]
        
        subgraph DeterministicEngine["Deterministic Engine (Pure Python Code)"]
            Rules["Deterministic Eligibility Engine<br/><b>CODE DECIDES ELIGIBILITY</b><br/>(Underwriting, Income, Cross-doc match)"]
        end

        subgraph LLMBoundary["LLM Provider (Gemini / Claude / Mock)"]
            LLM["LLM Explainer & Gap Assistant<br/><b>NEVER SEES RAW FILES OR TOKENS</b><br/><b>NEVER DECIDES ELIGIBILITY</b><br/>Explains code results with citations"]
        end
    end

    subgraph StorageLayer["Data & Persistence"]
        DB[(PostgreSQL / SQLite<br/>organisations, staff, docs, audit)]
        RedisCache[(Redis<br/>OAuth PKCE state, 10m TTL)]
    end

    subgraph BankPortals["Lender Bank Portal (Scoped Department Slices)"]
        KYCView["KYC Department Slice<br/>(Identity, Name Match, L4 Aadhaar)"]
        RiskView["Risk & Underwriting Slice<br/>(Income, Ratios, Deterministic Outcome)"]
        OpsView["Operations & Audit Slice<br/>(Immutable Consent & Approval Trail)"]
    end

    %% Flows
    PWA -- 1. Start Consent Link --> AuthRouter
    AuthRouter -- 2. Redirect with PKCE --> MockDL
    MockDL -- 3. Consent Granted / Denied --> AuthRouter
    AuthRouter -- Store Scope Decision --> ConsentEngine
    ConsentEngine --> DB
    ConsentEngine --> RedisCache

    PWA -- 4. Transmit Masked Extracted Fields --> DocService
    DocService --> DB
    
    DocService --> Rules
    Rules -- Deterministic Result --> LLM
    LLM -- Cited Explanation --> BankPortals

    ConsentEngine -- Scoped Documents Only --> KYCView
    ConsentEngine -- Scoped Documents Only --> RiskView
    ConsentEngine -- Audit Trail --> OpsView

    AuthRouter & DocService -.-> Filter
```

## Security & Compliance Invariants
1. **Never Collect Real Aadhaar/OTP in our UI**: Only redirected to official aggregator or explicit `DEMO ONLY` mock page.
2. **Never Persist Full Aadhaar / OTPs**: Only last 4 digits stored anywhere in database or memory logs.
3. **LLM Redaction Boundary**: The LLM provider only receives masked JSON schema dictionaries. Never passes raw files, tokens, or PII.
4. **Deterministic Decision Invariant**: Eligibility is 100% computed by Python business rules (`DeterministicEligibilityEngine`). LLM provides explanation and citations only.
5. **Departmental Scoping**: KYC, Risk, Credit, and Ops departments receive strictly partitioned slices of data.
