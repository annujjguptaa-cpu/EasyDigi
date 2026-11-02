"""
Prompt 9 — Tests: Coverage Engine & Department Router
"""
import pytest
from datetime import datetime, timezone, timedelta


async def _seed_scenario(session, claim_number, claim_type, policy_status, co_pay=0, deductible=0, waiting_days=0):
    from app.db.insurance_models import Claim, Policy, PolicyStatus
    status_map = {
        "ACTIVE":  PolicyStatus.ACTIVE,
        "LAPSED":  PolicyStatus.LAPSED,
        "EXPIRED": PolicyStatus.EXPIRED,
    }
    policy = Policy(
        number=f"POL-CE-{claim_number}",
        holder_name="Test Holder",
        holder_id=f"CUST_CE_{claim_number}",
        product_type="HEALTH",
        start_date=datetime.now(timezone.utc) - timedelta(days=180),
        end_date=datetime.now(timezone.utc) + timedelta(days=185),
        sum_insured=500000,
        deductible=deductible,
        co_pay_pct=co_pay,
        waiting_period_days=waiting_days,
        status=status_map.get(policy_status, PolicyStatus.ACTIVE),
    )
    session.add(policy)
    await session.flush()
    claim = Claim(
        claim_number=claim_number,
        policy_id=policy.id,
        type=claim_type,
        incident_date=datetime.now(timezone.utc) - timedelta(days=5),
        claimant_name="Test Holder",
        requested_amount=100000,
    )
    session.add(claim)
    await session.commit()
    return claim.id


# ── Test 1 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_coverage_active_policy_covered():
    """Active policy, incident within period, no flags → COVERED, payable computed."""
    from app.db.session import AsyncSessionLocal
    from app.services.coverage_engine import CoverageEngine

    async with AsyncSessionLocal() as session:
        claim_id = await _seed_scenario(session, "CLM-CE-01", "health_reimbursement", "ACTIVE", co_pay=10, deductible=5000)

    engine = CoverageEngine()
    result = await engine.compute_coverage(claim_id)
    assert result["status"] in ("COVERED", "PARTLY_COVERED")
    assert "POLICY_ACTIVE" in result["reason_codes"]
    assert result["breakdown"]["payable_amount"] > 0


# ── Test 2 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_coverage_lapsed_policy_not_covered():
    """Lapsed policy → NOT_COVERED."""
    from app.db.session import AsyncSessionLocal
    from app.services.coverage_engine import CoverageEngine

    async with AsyncSessionLocal() as session:
        claim_id = await _seed_scenario(session, "CLM-CE-02", "health_reimbursement", "LAPSED")

    engine = CoverageEngine()
    result = await engine.compute_coverage(claim_id)
    assert result["status"] == "NOT_COVERED"
    assert "POLICY_NOT_ACTIVE" in result["reason_codes"]


# ── Test 3 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_coverage_with_critical_fraud_flag_not_covered():
    """Unresolved CRITICAL fraud flag → NOT_COVERED."""
    from app.db.session import AsyncSessionLocal
    from app.db.insurance_models import FraudFlag
    from app.services.coverage_engine import CoverageEngine

    async with AsyncSessionLocal() as session:
        claim_id = await _seed_scenario(session, "CLM-CE-03", "health_reimbursement", "ACTIVE")
        flag = FraudFlag(
            claim_id=claim_id,
            flag_type="DATE_OUTSIDE_POLICY",
            severity="CRITICAL",
            evidence={"reason": "incident before policy start"},
            resolved=False,
        )
        session.add(flag)
        await session.commit()

    engine = CoverageEngine()
    result = await engine.compute_coverage(claim_id)
    assert result["status"] == "NOT_COVERED"
    assert "CRITICAL_FRAUD_FLAG_UNRESOLVED" in result["reason_codes"]


# ── Test 4 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_route_to_departments_health_cashless():
    """health_cashless → 3 tasks: CLAIMS_INTAKE, MEDICAL_TPA, PAYMENTS."""
    from app.db.session import AsyncSessionLocal
    from app.services.coverage_engine import CoverageEngine

    async with AsyncSessionLocal() as session:
        claim_id = await _seed_scenario(session, "CLM-CE-04", "health_cashless", "ACTIVE")

    engine = CoverageEngine()
    tasks = await engine.route_to_departments(claim_id)
    depts = [t["department"] for t in tasks]
    assert "CLAIMS_INTAKE" in depts
    assert "MEDICAL_TPA" in depts
    assert "PAYMENTS" in depts
    assert len(tasks) == 3


# ── Test 5 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_approve_claim_creates_settlement():
    """approve_claim → Claim.status APPROVED, Settlement row created."""
    from app.db.session import AsyncSessionLocal
    from app.db.insurance_models import Claim, Settlement, ClaimStatus
    from app.services.coverage_engine import CoverageEngine
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        claim_id = await _seed_scenario(session, "CLM-CE-05", "health_reimbursement", "ACTIVE")

    engine = CoverageEngine()
    result = await engine.approve_claim(claim_id, "OFFICER-001", 90000, "All docs verified")
    assert result["status"] == "APPROVED"

    async with AsyncSessionLocal() as session:
        claim = await session.get(Claim, claim_id)
        assert claim.status == ClaimStatus.APPROVED
        assert claim.approved_amount == 90000
        res = await session.execute(select(Settlement).where(Settlement.claim_id == claim_id))
        settlement = res.scalar_one_or_none()
        assert settlement is not None
        assert settlement.status == "INITIATED"
