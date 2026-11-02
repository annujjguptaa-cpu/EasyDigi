"""
Prompt 8 — Tests: Consistency Checker & Fraud Flags
"""
import pytest
from datetime import datetime, timezone, timedelta
from app.services.consistency_checker import ConsistencyChecker, _fuzzy_similarity


@pytest.fixture
def checker():
    return ConsistencyChecker()


# ── Helpers ────────────────────────────────────────────────────

async def _seed_claim(session, claim_number, claim_type, status_value=None):
    from app.db.insurance_models import Claim, Policy, PolicyStatus, ClaimStatus
    policy = Policy(
        number=f"POL-CC-{claim_number}",
        holder_name="Test Holder",
        holder_id="CUST_CC",
        product_type="HEALTH",
        start_date=datetime.now(timezone.utc) - timedelta(days=180),
        end_date=datetime.now(timezone.utc) + timedelta(days=185),
        sum_insured=500000,
        status=PolicyStatus.ACTIVE,
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
async def test_bill_discharge_mismatch_flagged(checker):
    """>10% variance between bill and discharge → flag raised."""
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        claim_id = await _seed_claim(session, "CLM-CC-01", "health_reimbursement")

    result = await checker.check_bill_vs_discharge(claim_id, 10000, 9000)
    assert result["flag_raised"] is True
    assert result["variance_pct"] == 10.0
    assert result["consistent"] is False


# ── Test 2 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bill_discharge_match_ok(checker):
    """< 5% variance → no flag."""
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        claim_id = await _seed_claim(session, "CLM-CC-02", "health_reimbursement")

    result = await checker.check_bill_vs_discharge(claim_id, 10000, 9950)
    assert result["flag_raised"] is False
    assert result["consistent"] is True
    assert result["variance_pct"] < 5.0


# ── Test 3 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_incident_outside_policy_flagged(checker):
    """Incident before policy_start → CRITICAL flag raised."""
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        claim_id = await _seed_claim(session, "CLM-CC-03", "motor_own_damage")

    now = datetime.now(timezone.utc)
    result = await checker.check_incident_within_policy(
        claim_id=claim_id,
        incident_date=now - timedelta(days=400),   # before policy
        policy_start=now - timedelta(days=180),
        policy_end=now + timedelta(days=185),
    )
    assert result["flag_raised"] is True
    assert result["within_period"] is False


# ── Test 4 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_nominee_name_mismatch_flagged(checker):
    """"Kavita R. Gupta" vs "Kavita Sharma" → mismatch flag."""
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        claim_id = await _seed_claim(session, "CLM-CC-04", "life_death")

    result = await checker.check_nominee_name(
        claim_id=claim_id,
        doc_nominee_name="Kavita R. Gupta",
        policy_nominee_name="Kavita Sharma",
    )
    assert result["flag_raised"] is True
    assert result["match_score"] < 0.75


# ── Test 5 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingest_approved_response_updates_claim(checker):
    """approved=True → Claim.status == COVERAGE_ASSESSED."""
    from app.db.session import AsyncSessionLocal
    from app.db.insurance_models import Claim, ClaimStatus
    async with AsyncSessionLocal() as session:
        claim_id = await _seed_claim(session, "CLM-CC-05", "health_reimbursement")

    result = await checker.ingest_insurer_response(
        claim_id=claim_id,
        approved=True,
        approved_amount=90000,
        query_items=None,
        notes="All docs verified",
    )
    assert result["new_status"] == ClaimStatus.COVERAGE_ASSESSED.value
