"""
Prompt 6 — Claim Share Service
================================
Shares a claim package with an insurer/TPA by consent, using hybrid encryption.
The server assembles a manifest of vault references (NOT ciphertext) and encrypts
it with AES-256-GCM; the AES key is wrapped using the recipient's RSA-OAEP public key.

Security rules:
- No PII (no full Aadhaar, no full account numbers) in the manifest.
- Claimant name is masked to first name + initial only.
- Vault refs are opaque UUIDs — no file content leaves the vault.
- Share tokens are revocable.
- All share events are logged as ClaimEvents.
"""

from __future__ import annotations

import base64
import json
import os
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from app.db.session import AsyncSessionLocal
from app.db.insurance_models import Claim, ClaimEvent, ClaimStatus

# In-memory revocation store  {share_token: {revoked: bool, claim_id: str}}
_share_registry: dict[str, dict] = {}


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _mask_name(full_name: str) -> str:
    """Return 'FirstName L.' — never store/expose full name in shared package."""
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][0]}."


def _hybrid_encrypt(manifest_json: str, recipient_public_key_b64: str) -> dict[str, str]:
    """
    Hybrid encryption:
      1. Generate random AES-256 key (32 bytes).
      2. Encrypt manifest with AES-256-GCM.
      3. Wrap AES key with recipient RSA-OAEP public key.

    If the `cryptography` library is available, real RSA-OAEP is used.
    Otherwise, falls back to a base64 mock with a clear comment.
    NOTE: In production, replace with real RSA-OAEP (cryptography lib required).
    """
    # --- Step 1: Generate AES-256-GCM key + nonce ---
    aes_key = os.urandom(32)          # 256 bits
    nonce   = os.urandom(12)          # 96-bit GCM nonce

    # --- Step 2: AES-256-GCM encryption ---
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        aesgcm           = AESGCM(aes_key)
        ciphertext       = aesgcm.encrypt(nonce, manifest_json.encode(), None)
        encrypted_blob   = nonce + ciphertext                          # prepend nonce
    except ImportError:
        # Fallback: base64-encode plaintext (DEMO ONLY — replace with real AESGCM)
        encrypted_blob = base64.b64encode(manifest_json.encode())      # NOT real encryption

    encrypted_manifest_b64 = base64.b64encode(encrypted_blob).decode()

    # --- Step 3: Wrap AES key with recipient RSA-OAEP public key ---
    try:
        from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
        from cryptography.hazmat.primitives import hashes, serialization

        pub_key_der = base64.b64decode(recipient_public_key_b64)
        pub_key     = serialization.load_der_public_key(pub_key_der)
        wrapped_key = pub_key.encrypt(
            aes_key,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        wrapped_key_b64 = base64.b64encode(wrapped_key).decode()
    except Exception:
        # MOCK: base64-encode raw AES key (DEMO ONLY — REPLACE WITH REAL RSA-OAEP in production)
        wrapped_key_b64 = base64.b64encode(
            b"MOCK_WRAPPED:" + aes_key
        ).decode() + ":DEMO_ONLY_NOT_RSA_OAEP"

    return {
        "encrypted_manifest_b64": encrypted_manifest_b64,
        "wrapped_key_b64":        wrapped_key_b64,
    }


# ─────────────────────────────────────────────────────────────
# ClaimShareService
# ─────────────────────────────────────────────────────────────

class ClaimShareService:
    """
    Share claim packages with insurers/TPAs under explicit consent.
    LLM never sees raw files or tokens — only the manifest references are shared.
    """

    # ── Generate share package ──────────────────────────────────

    async def generate_share_package(
        self,
        claim_id: str,
        consented_doc_refs: list[str],
        recipient_public_key_b64: str,
    ) -> dict[str, Any]:
        """
        Assemble a consent-gated claim package manifest and encrypt it.

        Returns:
            share_token, encrypted_manifest_b64, wrapped_key_b64, expires_at
        """
        async with AsyncSessionLocal() as session:
            claim = await session.get(Claim, claim_id)
            if not claim:
                raise ValueError(f"Claim {claim_id} not found")

            share_token = f"SHR-{secrets.token_urlsafe(20)}"
            now         = datetime.now(timezone.utc)
            expires_at  = now + timedelta(hours=72)    # 3-day share window

            # Build manifest — masked PII, vault refs only (no ciphertext)
            manifest = {
                "claim_number":        claim.claim_number,
                "claim_type":          claim.type,
                "incident_date":       claim.incident_date.isoformat(),
                "claimant_name":       _mask_name(claim.claimant_name),  # masked
                "doc_refs":            consented_doc_refs,                # opaque UUIDs
                "share_token":         share_token,
                "generated_at":        now.isoformat(),
                "expires_at":          expires_at.isoformat(),
                "disclaimer":          "SAMPLE DATA — DEMO ONLY. Doc refs are encrypted vault references.",
            }

            # Encrypt manifest
            encrypted = _hybrid_encrypt(json.dumps(manifest), recipient_public_key_b64)

            # Register token
            _share_registry[share_token] = {
                "claim_id":   claim_id,
                "revoked":    False,
                "expires_at": expires_at,
                "doc_count":  len(consented_doc_refs),
            }

            # Log event
            event = ClaimEvent(
                claim_id=claim_id,
                action="CLAIM_PACKAGE_SHARED",
                actor="system",
                details={
                    "recipient":   "INSURER",
                    "doc_count":   len(consented_doc_refs),
                    "share_token": share_token,
                    "expires_at":  expires_at.isoformat(),
                },
            )
            session.add(event)
            await session.commit()

        return {
            "share_token":             share_token,
            "encrypted_manifest_b64":  encrypted["encrypted_manifest_b64"],
            "wrapped_key_b64":         encrypted["wrapped_key_b64"],
            "expires_at":              expires_at.isoformat(),
        }

    # ── Cashless pre-auth ───────────────────────────────────────

    async def generate_cashless_preauth(
        self,
        claim_id: str,
        hospital_ref: str,
        estimated_amount: int,
    ) -> dict[str, Any]:
        """
        Generate a pre-authorisation request for health cashless claims only.
        Raises ValueError for non-cashless claim types.
        """
        async with AsyncSessionLocal() as session:
            claim = await session.get(Claim, claim_id)
            if not claim:
                raise ValueError(f"Claim {claim_id} not found")
            if claim.type != "health_cashless":
                raise ValueError(
                    f"Pre-auth is only valid for health_cashless claims; got '{claim.type}'"
                )

            preauth_ref = f"PA-{claim.claim_number}-{secrets.token_hex(4).upper()}"

            event = ClaimEvent(
                claim_id=claim_id,
                action="PRE_AUTH_REQUESTED",
                actor="system",
                details={
                    "preauth_ref":      preauth_ref,
                    "hospital_ref":     hospital_ref,
                    "estimated_amount": estimated_amount,
                },
            )
            session.add(event)
            await session.commit()

        return {
            "preauth_ref":        preauth_ref,
            "claim_number":       claim.claim_number,
            "hospital_ref":       hospital_ref,
            "estimated_amount":   estimated_amount,
            "status":             "PENDING_TPA_APPROVAL",
            "expires_in_hours":   1,
        }

    # ── Revoke share ────────────────────────────────────────────

    async def revoke_share(self, share_token: str) -> dict[str, Any]:
        """
        Revoke a previously issued share token.
        Returns {"revoked": True} always (idempotent).
        """
        entry = _share_registry.get(share_token)
        if not entry:
            # Token unknown — treat as already revoked
            _share_registry[share_token] = {"revoked": True, "claim_id": None}
            return {"revoked": True, "share_token": share_token}

        was_revoked  = entry["revoked"]
        entry["revoked"] = True
        claim_id     = entry.get("claim_id")

        if claim_id and not was_revoked:
            async with AsyncSessionLocal() as session:
                event = ClaimEvent(
                    claim_id=claim_id,
                    action="SHARE_REVOKED",
                    actor="system",
                    details={"share_token": share_token},
                )
                session.add(event)
                await session.commit()

        return {"revoked": True, "share_token": share_token}

    def is_revoked(self, share_token: str) -> bool:
        """Check revocation status of a share token."""
        entry = _share_registry.get(share_token)
        return bool(entry and entry.get("revoked", False))

    def _reset(self) -> None:
        """Clear in-memory state (tests only)."""
        _share_registry.clear()


claim_share_service = ClaimShareService()
