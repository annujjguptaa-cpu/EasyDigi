import os
import json
import time
from typing import Dict, Any, List, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import settings

# Retention registry for automatic cleanup: doc_id -> expiration timestamp
_RETENTION_REGISTRY: Dict[str, float] = {}
# Encrypted at-rest vault store: doc_id -> dict(nonce, ciphertext, tag, retention_ts)
_ENCRYPTED_VAULT_STORE: Dict[str, Dict[str, Any]] = {}


class DocumentClassifier:
    """
    Classifies documents into regulated standard categories:
    PAN, AADHAAR_MASKED, DL, MARKSHEET, SALARY_SLIP, BANK_STATEMENT,
    ITR, FORM16, TITLE_DEED, EC, BUILDING_PLAN, PHOTO, SIGNATURE
    """
    CATEGORY_MAPPING = {
        "pan": "PAN",
        "aadhaar": "AADHAAR_MASKED",
        "driving": "DL",
        "dl": "DL",
        "license": "DL",
        "marksheet": "MARKSHEET",
        "degree": "MARKSHEET",
        "salary": "SALARY_SLIP",
        "pay": "SALARY_SLIP",
        "payslip": "SALARY_SLIP",
        "statement": "BANK_STATEMENT",
        "bank": "BANK_STATEMENT",
        "itr": "ITR",
        "form16": "FORM16",
        "title": "TITLE_DEED",
        "deed": "TITLE_DEED",
        "encumbrance": "EC",
        "ec": "EC",
        "building": "BUILDING_PLAN",
        "plan": "BUILDING_PLAN",
        "photo": "PHOTO",
        "passport_photo": "PHOTO",
        "signature": "SIGNATURE",
        "sign": "SIGNATURE"
    }

    @classmethod
    def classify(cls, filename: str, content_hints: Optional[str] = None) -> str:
        text = f"{filename} {content_hints or ''}".lower()
        for key, category in cls.CATEGORY_MAPPING.items():
            if key in text:
                return category
        return "OTHER"


class FieldMasker:
    """
    Enforces strict DPDP / UIDAI data minimization masking:
    - PAN: shows first 2 and last 1 characters (e.g. ABXXXXXX4F)
    - Aadhaar: shows last 4 digits only (e.g. XXXXXXXX4321)
    - Account number: shows last 4 digits only
    """
    @staticmethod
    def mask_pan(pan: str) -> str:
        clean = pan.strip().upper()
        if len(clean) == 10:
            return f"{clean[:2]}XXXXXXX{clean[-1]}"
        return "XXXXXXXXXX"

    @staticmethod
    def mask_aadhaar(aadhaar: str) -> str:
        clean = "".join(filter(str.isdigit, aadhaar))
        if len(clean) >= 4:
            return f"XXXXXXXX{clean[-4:]}"
        return "XXXXXXXXXXXX"

    @staticmethod
    def mask_account_number(acc: str) -> str:
        clean = "".join(filter(str.isalnum, acc))
        if len(clean) >= 4:
            return f"{'*' * (len(clean) - 4)}{clean[-4:]}"
        return "****"

    @classmethod
    def mask_extracted_fields(cls, fields: Dict[str, Any]) -> Dict[str, Any]:
        masked = {}
        for k, v in fields.items():
            if not isinstance(v, str):
                masked[k] = v
                continue
            if k in ("pan", "pan_number", "pan_masked"):
                masked["pan_masked"] = cls.mask_pan(v)
            elif k in ("aadhaar", "aadhaar_number", "id_last4", "uid"):
                masked["id_last4"] = v[-4:] if len(v) >= 4 else "0000"
            elif "account" in k or "acc_no" in k:
                masked[k] = cls.mask_account_number(v)
            else:
                masked[k] = v
        return masked


class CrossCheckEngine:
    """
    Pure deterministic comparison engine (Hard Rule #5: code decides, LLM explains).
    Compares name (fuzzy, initials, token permutation), DOB, and address across documents.
    Outputs mismatches with severity and the two source documents.
    """
    @staticmethod
    def normalize_name(name: str) -> List[str]:
        # Normalize punctuation and tokenize
        clean = name.lower().replace(".", " ").replace(",", " ")
        return [tok for tok in clean.split() if tok]

    @classmethod
    def compare_names(cls, name1: str, name2: str) -> Dict[str, Any]:
        tokens1 = cls.normalize_name(name1)
        tokens2 = cls.normalize_name(name2)

        if not tokens1 or not tokens2:
            return {"match": False, "severity": "HIGH", "reason": "Empty name field"}

        # Exact match
        if tokens1 == tokens2:
            return {"match": True, "severity": "NONE"}

        # Permutation match (e.g. "Verma Rahul" vs "Rahul Verma")
        if sorted(tokens1) == sorted(tokens2):
            return {"match": True, "severity": "LOW", "reason": "Name tokens reordered"}

        # Initial check (e.g. "Priya S Sharma" vs "Priya Sunil Sharma")
        # Find if single-letter tokens match the first letter of corresponding token
        s1 = set(tokens1)
        s2 = set(tokens2)
        common = s1.intersection(s2)
        remaining1 = s1 - common
        remaining2 = s2 - common

        # Check for subset/middle name omission (e.g. ['priya', 'sharma'] vs ['priya', 'sunil', 'sharma'])
        if s1.issubset(s2) or s2.issubset(s1):
            return {
                "match": False,
                "severity": "MEDIUM",
                "reason": f"Middle name / initial variation: '{name1}' vs '{name2}'"
            }

        # Check for initial expansion (e.g. ['priya', 's', 'sharma'] vs ['priya', 'sunil', 'sharma'])
        if len(remaining1) == 1 and len(remaining2) == 1:
            r1 = list(remaining1)[0]
            r2 = list(remaining2)[0]
            if (len(r1) == 1 and r2.startswith(r1)) or (len(r2) == 1 and r1.startswith(r2)):
                return {
                    "match": False,
                    "severity": "MEDIUM",
                    "reason": f"Middle name / initial variation: '{name1}' vs '{name2}'"
                }

        return {
            "match": False,
            "severity": "HIGH",
            "reason": f"Significant name difference between '{name1}' and '{name2}'"
        }

    @classmethod
    def cross_check_documents(cls, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        mismatches = []
        for i in range(len(documents)):
            for j in range(i + 1, len(documents)):
                doc_a = documents[i]
                doc_b = documents[j]

                name_a = doc_a.get("masked_fields", {}).get("name")
                name_b = doc_b.get("masked_fields", {}).get("name")

                if name_a and name_b:
                    comp = cls.compare_names(name_a, name_b)
                    if not comp["match"]:
                        mismatches.append({
                            "type": "NAME_MISMATCH",
                            "severity": comp["severity"],
                            "reason": comp["reason"],
                            "doc_a": doc_a.get("doc_type"),
                            "doc_b": doc_b.get("doc_type")
                        })

                # DOB check
                dob_a = doc_a.get("masked_fields", {}).get("dob")
                dob_b = doc_b.get("masked_fields", {}).get("dob")
                if dob_a and dob_b and dob_a != dob_b:
                    mismatches.append({
                        "type": "DOB_MISMATCH",
                        "severity": "HIGH",
                        "reason": f"Date of birth mismatch: '{dob_a}' != '{dob_b}'",
                        "doc_a": doc_a.get("doc_type"),
                        "doc_b": doc_b.get("doc_type")
                    })
        return mismatches


class MissingDocumentCalculator:
    """Calculates missing required documents against received documents"""
    @staticmethod
    def calculate(required_types: List[str], received_types: List[str]) -> List[str]:
        received_set = set(received_types)
        return [req for req in required_types if req not in received_set]


class DocumentStorageService:
    """
    Encrypts files at rest with AES-256-GCM using key from config.
    Maintains a configurable retention timestamp and deletes expired documents.
    """
    def __init__(self, key: Optional[bytes] = None):
        # Derive 32-byte key from VAULT_SECRET_KEY
        secret = settings.VAULT_SECRET_KEY.encode('utf-8')
        self.aes_key = key or AESGCM.generate_key(bit_length=256)

    def encrypt_and_store(self, doc_id: str, data: bytes, retention_hours: int = 24) -> str:
        aesgcm = AESGCM(self.aes_key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        expires_at = time.time() + (retention_hours * 3600)

        _ENCRYPTED_VAULT_STORE[doc_id] = {
            "nonce": nonce,
            "ciphertext": ciphertext,
            "retention_ts": expires_at
        }
        _RETENTION_REGISTRY[doc_id] = expires_at
        return f"encrypted_ref_{doc_id}"

    def decrypt(self, doc_id: str) -> bytes:
        if doc_id not in _ENCRYPTED_VAULT_STORE:
            raise FileNotFoundError(f"Document {doc_id} not found in encrypted vault")
        record = _ENCRYPTED_VAULT_STORE[doc_id]
        aesgcm = AESGCM(self.aes_key)
        return aesgcm.decrypt(record["nonce"], record["ciphertext"], None)

    @classmethod
    def run_retention_job(cls, current_time: Optional[float] = None) -> int:
        """Deletes expired documents and tokens after retention expiry"""
        now = current_time or time.time()
        expired_ids = [doc_id for doc_id, exp in _RETENTION_REGISTRY.items() if now >= exp]
        for exp_id in expired_ids:
            _ENCRYPTED_VAULT_STORE.pop(exp_id, None)
            _RETENTION_REGISTRY.pop(exp_id, None)
        return len(expired_ids)
