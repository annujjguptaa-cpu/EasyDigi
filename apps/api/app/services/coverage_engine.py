"""
Prompt 9 — Coverage Engine & Department Router
===============================================
Deterministic Python logic computes coverage — NO LLM for coverage decisions.
LLM only generates cited narrative summaries from masked data.

HARD RULES:
- Code decides coverage, not LLM
- Fraud flags are for HUMAN REVIEW — never auto-reject
- Human officers approve/reject via UI
- All decisions logged as ClaimEvents
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.db.insurance_models import (
    Claim, Policy, FraudFlag, CoverageResult, CoverageStatus,
    ClaimTask, ClaimEvent, Settlement, ClaimStatus, InsuranceDepartment
)

# Department routing table
DEPARTMENT_ROUTING: dict[str, list[str]] = {
    "health_cashless":      ["CLAIMS_INTAKE", "MEDICAL_TPA", "PAYMENTS"],
    "health_reimbursement": ["CLAIMS_INTAKE", "MEDICAL_TPA", "FRAUD_SIU", "PAYMENTS"],
    "motor_own_damage":     ["CLAIMS_INTAKE", "SURVEYOR", "PAYMENTS"],
    "motor_theft":          ["CLAIMS_INTAKE", "SURVEYOR", "FRAUD_SIU", "PAYMENTS"],
    "life_death":           ["CLAIMS_INTAKE", "FRAUD_SIU", "PAYMENTS"],
}

DEPT_ENUM_MAP = {
    "CLAIMS_INTAKE": InsuranceDepartment.CLAIMS_INTAKE,
    "MEDICAL_TPA":   InsuranceDepartment.MEDICAL_TPA,
    "SURVEYOR":      InsuranceDepartment.SURVEYOR,
    "FRAUD_SIU":     InsuranceDepartment.FRAUD_SIU,
    "PAYMENTS":      InsuranceDepartment.PAYMENTS,
}


def _mock_llm_summary(claim_type: str, dept: str, flag_count: int) -> str:
    """
    LLM generates an EXPLANATION (not a decision) from masked data.
    LLM never sees raw files, tokens, or unmasked identifiers.
    """
    flag_note = f" NOTE: {flag_count} flag(s) raised for human review." if flag_count else ""
    return (
        f"[DEMO SUMMARY] {dept.replace('_', ' ').title()} task for {claim_type.replace('_', ' ')} claim. "
        f"All documents have been classified and masked fields extracted.{flag_note} "
        f"Human officer review required before any decision."
    )


class CoverageEngine:

    async def compute_coverage(self, claim_id: str) -> dict[str, Any]:
        """
        Deterministic coverage computation. Code decides — not LLM.

        Checks (short-circuit on NOT_COVERED):
          1. policy_active
          2. incident_within_period
          3. waiting_period_met
          4. no_critical_unresolved_fraud_flags

        Returns CoverageResult dict.
        """
        async with AsyncSessionLocal() as session:
            claim = await session.get(Claim, claim_id)
            if not claim:
                raise ValueError(f"Claim {claim_id} not found")
            policy = await session.get(Policy, claim.policy_id)
            if not policy:
                raise ValueError(f"Policy for claim {claim_id} not found")

            flags_res = await session.execute(
                select(FraudFlag).where(
                    FraudFlag.claim_id == claim_id,
                    FraudFlag.resolved == False,
                )
            )
            unresolved_flags = flags_res.scalars().all()

        reason_codes: list[str] = []
        status = CoverageStatus.COVERED

        # ── Check 1: Policy active ──────────────────────────────
        if policy.status.value != "ACTIVE":
            reason_codes.append("POLICY_NOT_ACTIVE")
            status = CoverageStatus.NOT_COVERED
        else:
            reason_codes.append("POLICY_ACTIVE")

        # ── Check 2: Incident within policy period ──────────────
        if status == CoverageStatus.COVERED:
            inc = claim.incident_date
            start = policy.start_date
            end = policy.end_date

            def _utc(dt):
                return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

            if not (_utc(start) <= _utc(inc) <= _utc(end)):
                reason_codes.append("INCIDENT_OUTSIDE_POLICY_PERIOD")
                status = CoverageStatus.NOT_COVERED
            else:
                reason_codes.append("INCIDENT_WITHIN_PERIOD")

        # ── Check 3: Waiting period ─────────────────────────────
        if status == CoverageStatus.COVERED and policy.waiting_period_days > 0:
            inc = claim.incident_date
            start = policy.start_date

            def _utc(dt):
                return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

            days_elapsed = (_utc(inc) - _utc(start)).days
            if days_elapsed < policy.waiting_period_days:
                reason_codes.append("WAITING_PERIOD_NOT_MET")
                status = CoverageStatus.NOT_COVERED
            else:
                reason_codes.append("WAITING_PERIOD_MET")

        # ── Check 4: No critical unresolved fraud flags ──────────
        if status == CoverageStatus.COVERED:
            critical = [f for f in unresolved_flags if f.severity == "CRITICAL"]
            if critical:
                reason_codes.append("CRITICAL_FRAUD_FLAG_UNRESOLVED")
                status = CoverageStatus.NOT_COVERED
            else:
                reason_codes.append("NO_CRITICAL_FLAGS")

        # ── Compute payable amount ──────────────────────────────
        requested = claim.requested_amount or 0
        deductible = min(requested, policy.deductible or 0)
        after_deductible = requested - deductible
        co_pay_amount = after_deductible * (policy.co_pay_pct or 0) / 100
        payable = after_deductible - co_pay_amount
        payable = min(payable, policy.sum_insured)

        if status == CoverageStatus.COVERED and 0 < payable < requested:
            status = CoverageStatus.PARTLY_COVERED

        breakdown = {
            "requested_amount": requested,
            "deductible":       deductible,
            "after_deductible": after_deductible,
            "co_pay_pct":       policy.co_pay_pct or 0,
            "co_pay_amount":    round(co_pay_amount, 2),
            "payable_amount":   round(payable, 2),
            "sum_insured_cap":  policy.sum_insured,
        }

        # Save to DB
        async with AsyncSessionLocal() as session:
            coverage = CoverageResult(
                claim_id=claim_id,
                status=status,
                breakdown=breakdown,
                reason_codes=reason_codes,
            )
            session.add(coverage)
            event = ClaimEvent(
                claim_id=claim_id,
                action="COVERAGE_ASSESSED",
                actor="system",
                details={"status": status.value, "reason_codes": reason_codes},
            )
            session.add(event)
            await session.commit()

        return {
            "claim_id":     claim_id,
            "status":       status.value,
            "breakdown":    breakdown,
            "reason_codes": reason_codes,
        }

    async def route_to_departments(self, claim_id: str) -> List[dict]:
        """
        Create ClaimTask rows for all applicable departments.
        LLM generates narrative summary (explanation only, not decision).
        """
        async with AsyncSessionLocal() as session:
            claim = await session.get(Claim, claim_id)
            if not claim:
                raise ValueError(f"Claim {claim_id} not found")

            flags_res = await session.execute(
                select(FraudFlag).where(FraudFlag.claim_id == claim_id)
            )
            flag_count = len(flags_res.scalars().all())

            departments = DEPARTMENT_ROUTING.get(claim.type, ["CLAIMS_INTAKE"])
            created = []
            for dept_str in departments:
                dept_enum = DEPT_ENUM_MAP[dept_str]
                summary = _mock_llm_summary(claim.type, dept_str, flag_count)
                task = ClaimTask(
                    claim_id=claim_id,
                    department=dept_enum,
                    status="PENDING",
                    cited_summary=summary,
                )
                session.add(task)
                created.append({
                    "department":    dept_str,
                    "status":        "PENDING",
                    "cited_summary": summary,
                })
            await session.commit()

        return created

    async def approve_claim(
        self,
        claim_id: str,
        officer_id: str,
        approved_amount: int,
        notes: str = "",
    ) -> dict[str, Any]:
        """Human decision: officer approves claim with specified amount."""
        async with AsyncSessionLocal() as session:
            claim = await session.get(Claim, claim_id)
            if not claim:
                raise ValueError(f"Claim {claim_id} not found")
            claim.status = ClaimStatus.APPROVED
            claim.approved_amount = approved_amount
            event = ClaimEvent(
                claim_id=claim_id,
                action="CLAIM_APPROVED",
                actor=officer_id,
                details={"approved_amount": approved_amount, "notes": notes[:200]},
            )
            settlement = Settlement(
                claim_id=claim_id,
                amount=approved_amount,
                status="INITIATED",
            )
            session.add(event)
            session.add(settlement)
            await session.commit()
        return {"claim_id": claim_id, "status": "APPROVED", "approved_amount": approved_amount}

    async def reject_claim(
        self,
        claim_id: str,
        officer_id: str,
        reason_code: str,
        notes: str = "",
    ) -> dict[str, Any]:
        """Human decision: officer rejects claim with reason."""
        async with AsyncSessionLocal() as session:
            claim = await session.get(Claim, claim_id)
            if not claim:
                raise ValueError(f"Claim {claim_id} not found")
            claim.status = ClaimStatus.REJECTED
            event = ClaimEvent(
                claim_id=claim_id,
                action="CLAIM_REJECTED",
                actor=officer_id,
                details={"reason_code": reason_code, "notes": notes[:200]},
            )
            session.add(event)
            await session.commit()
        return {"claim_id": claim_id, "status": "REJECTED", "reason_code": reason_code}


coverage_engine = CoverageEngine()
