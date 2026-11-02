"""
Prompt 10 — Settlement Service & Ombudsman Escalation
======================================================
Completes the claim lifecycle: settlement UTR generation and grievance escalation.

Security rules:
- Bank account stored as last-4 only (never full number)
- Grievance text is stripped of obvious PII before logging
- UTR is a mock random reference — replace with real payment gateway in production
"""
from __future__ import annotations

import random
import re
import secrets
import string
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.db.insurance_models import (
    Claim, Settlement, ClaimEvent, ClaimStatus
)


def _generate_utr() -> str:
    """Generate a mock UTR number (DEMO ONLY — not a real payment reference)."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    rand = "".join(random.choices(string.digits, k=6))
    return f"UTR{ts}{rand}"


def _strip_pii_from_text(text: str) -> str:
    """
    Basic PII stripping before logging grievance text.
    Removes patterns that look like Aadhaar (12 digits) or phone numbers.
    """
    # Remove 12-digit sequences (Aadhaar pattern)
    text = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[REDACTED]', text)
    # Remove 10-digit phone numbers
    text = re.sub(r'\b[6-9]\d{9}\b', '[PHONE_REDACTED]', text)
    # Truncate to 500 chars max
    return text[:500]


class SettlementService:

    async def initiate_settlement(
        self,
        claim_id: str,
        bank_account_last4: str,
        payment_mode: str = "NEFT",
    ) -> dict[str, Any]:
        """
        Initiate settlement for an APPROVED claim.
        Generates a mock UTR and marks claim as SETTLED.
        Only last-4 of bank account stored — never full number.
        """
        # Validate last4
        if not bank_account_last4.isdigit() or len(bank_account_last4) != 4:
            raise ValueError("bank_account_last4 must be exactly 4 digits")

        async with AsyncSessionLocal() as session:
            claim = await session.get(Claim, claim_id)
            if not claim:
                raise ValueError(f"Claim {claim_id} not found")
            if claim.status != ClaimStatus.APPROVED:
                raise ValueError(
                    f"Settlement can only be initiated for APPROVED claims, not '{claim.status.value}'"
                )

            # Get settlement row (created by approve_claim)
            res = await session.execute(
                select(Settlement).where(Settlement.claim_id == claim_id)
            )
            settlement = res.scalar_one_or_none()
            if not settlement:
                settlement = Settlement(
                    claim_id=claim_id,
                    amount=claim.approved_amount or 0,
                    status="INITIATED",
                )
                session.add(settlement)
                await session.flush()

            utr = _generate_utr()
            now = datetime.now(timezone.utc)
            settlement.utr_number = utr
            settlement.bank_account_last4 = bank_account_last4
            settlement.payment_mode = payment_mode
            settlement.status = "PROCESSED"
            settlement.settled_at = now

            claim.status = ClaimStatus.SETTLED

            event = ClaimEvent(
                claim_id=claim_id,
                action="SETTLEMENT_PROCESSED",
                actor="system",
                details={
                    "utr_number":          utr,
                    "bank_account_last4":  bank_account_last4,   # last 4 only
                    "payment_mode":        payment_mode,
                    "amount":              settlement.amount,
                },
            )
            session.add(event)
            await session.commit()

        return {
            "claim_id":           claim_id,
            "utr_number":         utr,
            "bank_account_last4": bank_account_last4,
            "payment_mode":       payment_mode,
            "amount":             settlement.amount,
            "status":             "PROCESSED",
            "settled_at":         now.isoformat(),
        }

    async def get_settlement_status(self, claim_id: str) -> Optional[dict[str, Any]]:
        """Return current settlement status."""
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(Settlement).where(Settlement.claim_id == claim_id)
            )
            s = res.scalar_one_or_none()
            if not s:
                return None
            return {
                "claim_id":           claim_id,
                "amount":             s.amount,
                "utr_number":         s.utr_number,
                "bank_account_last4": s.bank_account_last4,
                "payment_mode":       s.payment_mode,
                "status":             s.status,
                "settled_at":         s.settled_at.isoformat() if s.settled_at else None,
            }

    async def escalate_to_ombudsman(
        self,
        claim_id: str,
        grievance_text: str,
    ) -> dict[str, Any]:
        """
        Escalate to the Insurance Ombudsman.
        Only allowed if claim is REJECTED or QUERY_RAISED and not already SETTLED.
        Grievance text is stripped of PII before logging.
        """
        async with AsyncSessionLocal() as session:
            claim = await session.get(Claim, claim_id)
            if not claim:
                raise ValueError(f"Claim {claim_id} not found")

            if claim.status == ClaimStatus.SETTLED:
                raise ValueError("Cannot escalate a SETTLED claim to Ombudsman")

            allowed_statuses = [ClaimStatus.REJECTED, ClaimStatus.QUERY_RAISED, ClaimStatus.IN_REVIEW]
            if claim.status not in allowed_statuses:
                raise ValueError(
                    f"Ombudsman escalation not allowed for status '{claim.status.value}'. "
                    f"Allowed: {[s.value for s in allowed_statuses]}"
                )

            escalation_ref = f"OMB-{claim.claim_number}-{secrets.token_hex(4).upper()}"
            safe_text = _strip_pii_from_text(grievance_text)

            event = ClaimEvent(
                claim_id=claim_id,
                action="OMBUDSMAN_ESCALATED",
                actor="policyholder",
                details={
                    "escalation_ref":      escalation_ref,
                    "grievance_summary":   safe_text,   # PII-stripped
                },
            )
            session.add(event)
            await session.commit()

        return {
            "escalation_ref": escalation_ref,
            "message": (
                f"Your grievance has been registered. Reference: {escalation_ref}. "
                "The Insurance Ombudsman will respond within 30 working days "
                "(SAMPLE TIMELINE — demo only)."
            ),
        }


settlement_service = SettlementService()
