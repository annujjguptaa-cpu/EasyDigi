"""
Prompt 8 — Consistency Checker & Fraud Flags
=============================================
Validates claim documents for consistency and raises flags for human review.

HARD RULES:
- Flags are for HUMAN REVIEW only — never automatic rejection
- LLM never sees raw amounts or unmasked data
- One consolidated query per claim (no drip requests)
- All check results are logged as ClaimEvents
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.db.insurance_models import (
    Claim, ClaimDocument, FraudFlag, ClaimEvent, Policy, ClaimStatus
)


def _fuzzy_similarity(a: str, b: str) -> float:
    """
    Simple character-overlap similarity (Dice coefficient).
    Returns 0.0–1.0. Replace with rapidfuzz in production for better accuracy.
    """
    a, b = a.lower().strip(), b.lower().strip()
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    set_a = set(a)
    set_b = set(b)
    intersection = set_a & set_b
    return 2 * len(intersection) / (len(set_a) + len(set_b))


class ConsistencyChecker:

    # ── Bill vs Discharge ────────────────────────────────────────

    async def check_bill_vs_discharge(
        self,
        claim_id: str,
        bill_amount: float,
        discharge_total: float,
    ) -> dict[str, Any]:
        """
        Flag BILL_DISCHARGE_MISMATCH if variance > 10%.
        Returns {consistent, variance_pct, flag_raised}.
        """
        max_val = max(bill_amount, discharge_total)
        variance_pct = abs(bill_amount - discharge_total) / max_val * 100 if max_val else 0.0
        flag_raised = variance_pct >= 10.0

        if flag_raised:
            await self._create_flag(
                claim_id=claim_id,
                flag_type="BILL_DISCHARGE_MISMATCH",
                severity="HIGH",
                evidence={
                    "bill_amount":      bill_amount,
                    "discharge_total":  discharge_total,
                    "variance_pct":     round(variance_pct, 2),
                },
            )

        return {
            "consistent":    not flag_raised,
            "variance_pct":  round(variance_pct, 2),
            "flag_raised":   flag_raised,
        }

    # ── Incident within policy period ────────────────────────────

    async def check_incident_within_policy(
        self,
        claim_id: str,
        incident_date: datetime,
        policy_start: datetime,
        policy_end: datetime,
    ) -> dict[str, Any]:
        """
        Flag DATE_OUTSIDE_POLICY (CRITICAL) if incident is outside policy period.
        """
        # Normalise to UTC-aware for comparison
        def _utc(dt: datetime) -> datetime:
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

        within = _utc(policy_start) <= _utc(incident_date) <= _utc(policy_end)
        if not within:
            await self._create_flag(
                claim_id=claim_id,
                flag_type="DATE_OUTSIDE_POLICY",
                severity="CRITICAL",
                evidence={
                    "incident_date":  incident_date.isoformat(),
                    "policy_start":   policy_start.isoformat(),
                    "policy_end":     policy_end.isoformat(),
                },
            )

        return {
            "within_period": within,
            "flag_raised":   not within,
        }

    # ── Nominee name match ───────────────────────────────────────

    async def check_nominee_name(
        self,
        claim_id: str,
        doc_nominee_name: str,
        policy_nominee_name: str,
    ) -> dict[str, Any]:
        """
        Flag NOMINEE_NAME_MISMATCH (HIGH) if similarity < 0.75.
        """
        score = _fuzzy_similarity(doc_nominee_name, policy_nominee_name)
        flag_raised = score < 0.75

        if flag_raised:
            await self._create_flag(
                claim_id=claim_id,
                flag_type="NOMINEE_NAME_MISMATCH",
                severity="HIGH",
                evidence={
                    "doc_nominee":    doc_nominee_name,
                    "policy_nominee": policy_nominee_name,
                    "match_score":    round(score, 3),
                },
            )

        return {
            "match_score": round(score, 3),
            "flag_raised": flag_raised,
        }

    # ── Run all checks ───────────────────────────────────────────

    async def run_all_checks(self, claim_id: str) -> dict[str, Any]:
        """
        Run all applicable checks for the claim.
        Returns {flags: [...], consolidated_query: str}.
        ONE consolidated query — never drip requests.
        """
        async with AsyncSessionLocal() as session:
            claim = await session.get(Claim, claim_id)
            if not claim:
                raise ValueError(f"Claim {claim_id} not found")

            policy = await session.get(Policy, claim.policy_id)

            # Gather existing masked_fields from documents
            docs_res = await session.execute(
                select(ClaimDocument).where(ClaimDocument.claim_id == claim_id)
            )
            docs = docs_res.scalars().all()

        issues: list[str] = []

        # Check incident within policy period
        if policy:
            result = await self.check_incident_within_policy(
                claim_id=claim_id,
                incident_date=claim.incident_date,
                policy_start=policy.start_date,
                policy_end=policy.end_date,
            )
            if result["flag_raised"]:
                issues.append("Incident date is outside the policy period")

        # Check nominee for life claims
        if claim.type == "life_death" and policy and policy.nominee_name:
            # Try to get nominee name from documents
            doc_nominee = None
            for doc in docs:
                if doc.masked_fields and "nominee_name" in doc.masked_fields:
                    doc_nominee = doc.masked_fields["nominee_name"]
                    break
            if doc_nominee:
                result = await self.check_nominee_name(
                    claim_id=claim_id,
                    doc_nominee_name=doc_nominee,
                    policy_nominee_name=policy.nominee_name,
                )
                if result["flag_raised"]:
                    issues.append("Nominee name in documents does not match policy records")

        # Check bill vs discharge for health reimbursement
        if claim.type == "health_reimbursement":
            bill_amount = None
            discharge_total = None
            for doc in docs:
                if doc.masked_fields:
                    if doc.doc_type in ("HOSPITAL_BILL", "FINAL_BILL") and "amount" in doc.masked_fields:
                        bill_amount = doc.masked_fields["amount"]
                    if doc.doc_type == "DISCHARGE_SUMMARY" and "amount" in doc.masked_fields:
                        discharge_total = doc.masked_fields["amount"]
            if bill_amount and discharge_total:
                result = await self.check_bill_vs_discharge(
                    claim_id=claim_id,
                    bill_amount=float(bill_amount),
                    discharge_total=float(discharge_total),
                )
                if result["flag_raised"]:
                    issues.append(
                        f"Hospital bill ({bill_amount}) vs discharge summary ({discharge_total}) "
                        f"shows {result['variance_pct']}% variance"
                    )

        # Get all flags
        flags = await self.get_fraud_flags(claim_id)

        # Single consolidated query
        consolidated_query = ""
        if issues:
            consolidated_query = (
                "The following issues require your attention before this claim can be processed:\n"
                + "\n".join(f"  {i+1}. {issue}" for i, issue in enumerate(issues))
            )

        # Log check event
        async with AsyncSessionLocal() as session:
            event = ClaimEvent(
                claim_id=claim_id,
                action="CONSISTENCY_CHECKS_RUN",
                actor="system",
                details={"flag_count": len(flags), "issues": len(issues)},
            )
            session.add(event)
            await session.commit()

        return {
            "flags":              flags,
            "consolidated_query": consolidated_query,
        }

    async def get_fraud_flags(self, claim_id: str) -> List[dict]:
        """Return all FraudFlag rows for a claim."""
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(FraudFlag).where(FraudFlag.claim_id == claim_id)
            )
            flags = res.scalars().all()
        return [
            {
                "id":               f.id,
                "flag_type":        f.flag_type,
                "severity":         f.severity,
                "evidence":         f.evidence,
                "resolved":         f.resolved,
                "resolution_notes": f.resolution_notes,
            }
            for f in flags
        ]

    async def ingest_insurer_response(
        self,
        claim_id: str,
        approved: bool,
        approved_amount: Optional[int],
        query_items: Optional[List[str]],
        notes: Optional[str],
    ) -> dict[str, Any]:
        """
        Process insurer/TPA response.
        NEVER auto-rejects — only humans can finalise rejection.
        """
        async with AsyncSessionLocal() as session:
            claim = await session.get(Claim, claim_id)
            if not claim:
                raise ValueError(f"Claim {claim_id} not found")

            if approved and approved_amount:
                claim.status = ClaimStatus.COVERAGE_ASSESSED
                claim.approved_amount = approved_amount
                action = "INSURER_RESPONSE_APPROVED"
            elif query_items:
                claim.status = ClaimStatus.QUERY_RAISED
                action = "INSURER_QUERY_RAISED"
            else:
                # Not approved, no query → leave for human review
                claim.status = ClaimStatus.IN_REVIEW
                action = "INSURER_RESPONSE_RECEIVED"

            event = ClaimEvent(
                claim_id=claim_id,
                action=action,
                actor="insurer",
                details={
                    "approved":         approved,
                    "approved_amount":  approved_amount,
                    "query_items":      query_items or [],
                    "notes":            (notes or "")[:200],  # truncate
                },
            )
            session.add(event)
            await session.commit()

        return {
            "claim_id": claim_id,
            "new_status": claim.status.value,
            "action": action,
        }

    # ── Internal helper ──────────────────────────────────────────

    async def _create_flag(
        self,
        claim_id: str,
        flag_type: str,
        severity: str,
        evidence: dict,
    ) -> None:
        """Create a FraudFlag row (for human review — never auto-reject)."""
        async with AsyncSessionLocal() as session:
            flag = FraudFlag(
                claim_id=claim_id,
                flag_type=flag_type,
                severity=severity,
                evidence=evidence,
                resolved=False,
            )
            session.add(flag)
            await session.commit()


consistency_checker = ConsistencyChecker()
