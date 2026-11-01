# DocFlow Privacy, Data Minimization & DPDP Compliance Guide

> [!IMPORTANT]
> **Legal Notice**: This document outlines the technical privacy architecture of the DocFlow platform. Production deployment requires formal compliance review by certified data protection officers and legal counsel under the Digital Personal Data Protection (DPDP) Act, 2023.

---

## 1. DPDP Principles Implemented

### Data Minimization
- Lenders only receive documents that the customer explicitly consents to.
- Lenders receive departmental slices: KYC gets identity; Credit gets income.

### Purpose Limitation
- Every verification request is bound to a specific purpose text and product category.

### Right to Revoke Consent
- The customer can revoke consent at any time via `BankPackageExchangeService.revoke_consent()`, initiating an automated retention countdown.

### Storage Limitation & Auto-Deletion
- `DocumentStorageService.run_retention_job()` deletes all encrypted files and access tokens after a configurable retention window (e.g. 24 hours).
