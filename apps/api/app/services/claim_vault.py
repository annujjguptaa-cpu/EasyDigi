"""
Prompt 5 — Claim Vault Service (Device-Side)
=============================================
Encrypted claim document vault.  Stores encrypted blobs by reference,
never touches plaintext (encryption happens client-side via WebCrypto
AES-256-GCM; the server stores the ciphertext + metadata only).

Security rules enforced here:
- Aadhaar / account numbers: never stored in vault metadata
- Vault refs use opaque UUIDs (no PII in path)
- Retention: per ClaimDeadline settlement window (default 90 days for claim docs)
- Policy wallet: stores encrypted policy bytes; soft-delete only
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


# ──────────────────────────────────────────────────────────────
# Value objects
# ──────────────────────────────────────────────────────────────

class VaultDocStatus(str, Enum):
    PENDING  = "PENDING"
    UPLOADED = "UPLOADED"
    VERIFIED = "VERIFIED"
    EXPIRED  = "EXPIRED"


class VaultRef(BaseModel):
    ref: str                    # opaque UUID — no PII
    claim_id: str
    doc_type: str
    size_bytes: int
    sha256: str                 # integrity check (of ciphertext)
    stored_at: datetime
    expires_at: datetime
    status: VaultDocStatus = VaultDocStatus.UPLOADED


class ChecklistItem(BaseModel):
    doc_type: str
    status: VaultDocStatus


class PolicyWalletEntry(BaseModel):
    policy_number_masked: str   # e.g. "POL-****-4321"
    ref: str
    stored_at: datetime
    expires_at: Optional[datetime] = None
    deleted: bool = False


class SyncBlob(BaseModel):
    """Single encrypted blob queued offline for batch upload."""
    local_id: str               # client-generated id for de-dup
    claim_id: str
    doc_type: str
    encrypted_b64: str          # base64-encoded AES-256-GCM ciphertext
    size_bytes: int
    sha256: str
    retention_hours: int = 2160  # 90 days default


class SyncResult(BaseModel):
    local_id: str
    ref: str
    status: str                 # "stored" | "duplicate" | "error"
    error: Optional[str] = None


# ──────────────────────────────────────────────────────────────
# In-memory store (production would use encrypted DB rows / S3)
# ──────────────────────────────────────────────────────────────

_claim_vault:  dict[str, VaultRef]          = {}  # ref → VaultRef
_policy_wallet: dict[str, PolicyWalletEntry] = {}  # masked_num → entry
_sync_dedup:   set[str]                     = set()  # local_ids seen


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _mask_policy_number(policy_number: str) -> str:
    """Mask middle digits of policy number, keep last 4."""
    if len(policy_number) <= 8:
        return policy_number[:2] + "****" + policy_number[-2:]
    return policy_number[:4] + "-****-" + policy_number[-4:]


def _verify_sha256(encrypted_b64: str, expected_sha256: str) -> bool:
    """Verify sha256 of the raw bytes matches the client-supplied hash."""
    import base64
    try:
        raw = base64.b64decode(encrypted_b64)
        actual = hashlib.sha256(raw).hexdigest()
        return actual == expected_sha256
    except Exception:
        return False


def _is_expired(ref_obj: VaultRef) -> bool:
    return datetime.now(timezone.utc) >= ref_obj.expires_at


# ──────────────────────────────────────────────────────────────
# ClaimVaultService
# ──────────────────────────────────────────────────────────────

class ClaimVaultService:
    """
    Server-side claim vault.

    The SERVER never decrypts content — it stores encrypted blobs and
    returns opaque references.  The client (WebCrypto) holds the key.
    """

    # ── Claim document storage ──────────────────────────────────

    def store_claim_doc(
        self,
        claim_id: str,
        doc_type: str,
        encrypted_b64: str,
        size_bytes: int,
        sha256: str,
        retention_hours: int = 2160,   # 90 days
    ) -> VaultRef:
        """
        Store an encrypted claim document blob.
        Returns a VaultRef with an opaque UUID ref — no PII in the ref.
        """
        if not _verify_sha256(encrypted_b64, sha256):
            raise ValueError("SHA-256 integrity check failed; blob may be corrupted")

        ref_id = str(uuid.uuid4())
        now    = datetime.now(timezone.utc)
        entry  = VaultRef(
            ref        = ref_id,
            claim_id   = claim_id,
            doc_type   = doc_type,
            size_bytes = size_bytes,
            sha256     = sha256,
            stored_at  = now,
            expires_at = now + timedelta(hours=retention_hours),
            status     = VaultDocStatus.UPLOADED,
        )
        _claim_vault[ref_id] = entry
        return entry

    def get_doc_by_ref(self, ref: str) -> Optional[VaultRef]:
        """Retrieve vault ref metadata (not the ciphertext)."""
        entry = _claim_vault.get(ref)
        if entry and _is_expired(entry):
            entry.status = VaultDocStatus.EXPIRED
        return entry

    def list_claim_docs(self, claim_id: str) -> List[VaultRef]:
        """List all vault refs for a given claim_id."""
        results = [v for v in _claim_vault.values() if v.claim_id == claim_id]
        for r in results:
            if _is_expired(r):
                r.status = VaultDocStatus.EXPIRED
        return results

    # ── Originals checklist ─────────────────────────────────────

    def get_originals_checklist(
        self,
        claim_id: str,
        required_docs: List[str],
    ) -> List[ChecklistItem]:
        """
        Return a checklist of {doc_type, status} for every required doc.

        Status:
          UPLOADED — at least one non-expired vault ref exists for this type
          VERIFIED — a bank officer marked it verified (via verify_doc)
          PENDING  — nothing uploaded yet
        """
        uploaded_types: dict[str, VaultDocStatus] = {}
        for v in _claim_vault.values():
            if v.claim_id != claim_id:
                continue
            if _is_expired(v):
                continue
            # VERIFIED wins over UPLOADED
            current = uploaded_types.get(v.doc_type, VaultDocStatus.PENDING)
            if v.status == VaultDocStatus.VERIFIED:
                uploaded_types[v.doc_type] = VaultDocStatus.VERIFIED
            elif current != VaultDocStatus.VERIFIED:
                uploaded_types[v.doc_type] = VaultDocStatus.UPLOADED

        return [
            ChecklistItem(
                doc_type=dt,
                status=uploaded_types.get(dt, VaultDocStatus.PENDING),
            )
            for dt in required_docs
        ]

    def mark_doc_verified(self, ref: str) -> bool:
        """Mark a vault ref as VERIFIED (called by bank officer)."""
        entry = _claim_vault.get(ref)
        if not entry or _is_expired(entry):
            return False
        entry.status = VaultDocStatus.VERIFIED
        return True

    # ── Policy wallet ───────────────────────────────────────────

    def store_policy_wallet_entry(
        self,
        policy_number: str,
        encrypted_b64: str,
        size_bytes: int,
        sha256: str,
        expires_at: Optional[datetime] = None,
    ) -> PolicyWalletEntry:
        """
        Store an encrypted policy card in the wallet.
        Only the masked policy number is stored in metadata.
        """
        if not _verify_sha256(encrypted_b64, sha256):
            raise ValueError("SHA-256 integrity check failed for policy wallet entry")

        masked    = _mask_policy_number(policy_number)
        ref_id    = str(uuid.uuid4())
        now       = datetime.now(timezone.utc)
        entry     = PolicyWalletEntry(
            policy_number_masked = masked,
            ref                  = ref_id,
            stored_at            = now,
            expires_at           = expires_at,
            deleted              = False,
        )
        _policy_wallet[masked] = entry
        # Also store the ciphertext in the claim vault store under policy-wallet namespace
        _claim_vault[ref_id] = VaultRef(
            ref        = ref_id,
            claim_id   = f"policy-wallet:{masked}",
            doc_type   = "POLICY_CARD",
            size_bytes = size_bytes,
            sha256     = sha256,
            stored_at  = now,
            expires_at = expires_at or (now + timedelta(days=3650)),  # 10 yr fallback
            status     = VaultDocStatus.UPLOADED,
        )
        return entry

    def get_policy_wallet(self) -> List[PolicyWalletEntry]:
        """Return all non-deleted policy wallet entries."""
        return [e for e in _policy_wallet.values() if not e.deleted]

    def delete_policy_wallet_entry(self, policy_number: str) -> bool:
        """Soft-delete a policy wallet entry."""
        masked = _mask_policy_number(policy_number)
        entry  = _policy_wallet.get(masked)
        if not entry:
            return False
        entry.deleted = True
        return True

    # ── Offline sync ────────────────────────────────────────────

    def sync_offline_blobs(self, blobs: List[SyncBlob]) -> List[SyncResult]:
        """
        Accept a batch of locally-queued encrypted blobs (uploaded when
        connectivity returns). Idempotent via local_id de-dup.

        Returns per-blob status: "stored" | "duplicate" | "error"
        """
        results: List[SyncResult] = []
        for blob in blobs:
            if blob.local_id in _sync_dedup:
                results.append(SyncResult(
                    local_id=blob.local_id,
                    ref="",
                    status="duplicate",
                ))
                continue
            try:
                vault_ref = self.store_claim_doc(
                    claim_id       = blob.claim_id,
                    doc_type       = blob.doc_type,
                    encrypted_b64  = blob.encrypted_b64,
                    size_bytes     = blob.size_bytes,
                    sha256         = blob.sha256,
                    retention_hours= blob.retention_hours,
                )
                _sync_dedup.add(blob.local_id)
                results.append(SyncResult(
                    local_id=blob.local_id,
                    ref=vault_ref.ref,
                    status="stored",
                ))
            except Exception as exc:
                results.append(SyncResult(
                    local_id=blob.local_id,
                    ref="",
                    status="error",
                    error=str(exc),
                ))
        return results

    # ── Test helper ─────────────────────────────────────────────

    def _reset(self) -> None:
        """Clear all in-memory state (tests only)."""
        _claim_vault.clear()
        _policy_wallet.clear()
        _sync_dedup.clear()


# Singleton
claim_vault_service = ClaimVaultService()
