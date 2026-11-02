"""
Prompt 5 — Tests: Claim Vault Service
"""
import base64
import hashlib
import pytest
from datetime import datetime, timezone, timedelta

from app.services.claim_vault import (
    ClaimVaultService,
    SyncBlob,
    VaultDocStatus,
)


def _make_blob(content: bytes = b"encrypted-ciphertext-demo") -> tuple[str, str, int]:
    """Helper: returns (encrypted_b64, sha256, size_bytes) for given content."""
    b64   = base64.b64encode(content).decode()
    sha   = hashlib.sha256(content).hexdigest()
    return b64, sha, len(content)


@pytest.fixture
def vault():
    svc = ClaimVaultService()
    svc._reset()
    yield svc
    svc._reset()


# ── Test 1: store and retrieve ────────────────────────────────────────────────

def test_claim_vault_store_and_retrieve(vault):
    """Store encrypted bytes, retrieve by ref — no decryption on server."""
    b64, sha, size = _make_blob(b"hospital-bill-encrypted")

    ref = vault.store_claim_doc(
        claim_id        = "claim-abc",
        doc_type        = "HOSPITAL_BILL",
        encrypted_b64   = b64,
        size_bytes      = size,
        sha256          = sha,
        retention_hours = 2160,
    )

    assert ref.ref  # opaque UUID present
    assert ref.claim_id == "claim-abc"
    assert ref.doc_type == "HOSPITAL_BILL"
    assert ref.sha256 == sha
    assert ref.status == VaultDocStatus.UPLOADED
    assert ref.expires_at > datetime.now(timezone.utc)

    # Retrieve by ref
    fetched = vault.get_doc_by_ref(ref.ref)
    assert fetched is not None
    assert fetched.ref == ref.ref
    assert fetched.doc_type == "HOSPITAL_BILL"


# ── Test 2: originals checklist missing docs ──────────────────────────────────

def test_originals_checklist_shows_missing_docs(vault):
    """Given required=[A,B,C], only A uploaded → B,C are PENDING."""
    b64, sha, size = _make_blob()

    # Upload only doc A
    vault.store_claim_doc(
        claim_id="claim-xyz", doc_type="DISCHARGE_SUMMARY",
        encrypted_b64=b64, size_bytes=size, sha256=sha,
    )

    required = ["DISCHARGE_SUMMARY", "HOSPITAL_BILL", "PRESCRIPTION"]
    checklist = vault.get_originals_checklist("claim-xyz", required)

    status_map = {item.doc_type: item.status for item in checklist}
    assert status_map["DISCHARGE_SUMMARY"] == VaultDocStatus.UPLOADED
    assert status_map["HOSPITAL_BILL"]     == VaultDocStatus.PENDING
    assert status_map["PRESCRIPTION"]      == VaultDocStatus.PENDING
    assert len(checklist) == 3


# ── Test 3: policy wallet add and list ────────────────────────────────────────

def test_policy_wallet_add_and_list(vault):
    """Store a policy card; list returns it; delete removes it from list."""
    b64, sha, size = _make_blob(b"encrypted-policy-card")

    entry = vault.store_policy_wallet_entry(
        policy_number = "POL-2024-9988",
        encrypted_b64 = b64,
        size_bytes    = size,
        sha256        = sha,
    )

    assert entry.ref
    assert "9988" in entry.policy_number_masked  # last 4 present
    assert not entry.deleted

    wallet = vault.get_policy_wallet()
    assert len(wallet) == 1
    assert wallet[0].policy_number_masked == entry.policy_number_masked

    # Soft delete
    removed = vault.delete_policy_wallet_entry("POL-2024-9988")
    assert removed is True
    wallet_after = vault.get_policy_wallet()
    assert len(wallet_after) == 0  # filtered out


# ── Test 4: offline sync batch ────────────────────────────────────────────────

def test_offline_sync_batch(vault):
    """Batch of 3 blobs synced in one call; duplicate local_id is idempotent."""
    blobs = []
    for i in range(3):
        content = f"blob-{i}".encode()
        b64, sha, size = _make_blob(content)
        blobs.append(SyncBlob(
            local_id      = f"local-{i}",
            claim_id      = "claim-offline",
            doc_type      = f"DOC_{i}",
            encrypted_b64 = b64,
            size_bytes    = size,
            sha256        = sha,
        ))

    results = vault.sync_offline_blobs(blobs)
    assert len(results) == 3
    assert all(r.status == "stored" for r in results)
    assert all(r.ref for r in results)

    # Re-sync same blobs → all duplicates
    results2 = vault.sync_offline_blobs(blobs)
    assert all(r.status == "duplicate" for r in results2)

    # Docs are in vault
    docs = vault.list_claim_docs("claim-offline")
    assert len(docs) == 3


# ── Test 5: vault retention expiry ───────────────────────────────────────────

def test_claim_vault_retention_expiry(vault):
    """Items with retention_hours=0 are immediately expired."""
    b64, sha, size = _make_blob(b"ephemeral-doc")

    ref = vault.store_claim_doc(
        claim_id        = "claim-expire",
        doc_type        = "SCENE_PHOTO",
        encrypted_b64   = b64,
        size_bytes      = size,
        sha256          = sha,
        retention_hours = 0,   # expires immediately
    )

    fetched = vault.get_doc_by_ref(ref.ref)
    assert fetched is not None
    assert fetched.status == VaultDocStatus.EXPIRED
