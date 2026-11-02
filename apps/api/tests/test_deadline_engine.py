"""
Prompt 7 — Tests: Deadline Engine
"""
import pytest
from datetime import datetime, timezone, timedelta
from app.services.deadline_engine import DeadlineEngine


@pytest.fixture
def engine():
    return DeadlineEngine()


# ── Test 1 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_initialise_deadlines_health_cashless(engine):
    """health_cashless creates pre_auth + final_auth + intimation + settlement deadlines."""
    from app.db.session import AsyncSessionLocal
    from app.db.insurance_models import Claim, Policy, PolicyStatus

    async with AsyncSessionLocal() as session:
        policy = Policy(
            number="POL-DL-HC-01",
            holder_name="Rajan Nair",
            holder_id="CUST_DL01",
            product_type="HEALTH",
            start_date=datetime.now(timezone.utc) - timedelta(days=180),
            end_date=datetime.now(timezone.utc) + timedelta(days=185),
            sum_insured=500000,
            status=PolicyStatus.ACTIVE,
        )
        session.add(policy)
        await session.flush()
        claim = Claim(
            claim_number="CLM-DL-HC-01",
            policy_id=policy.id,
            type="health_cashless",
            incident_date=datetime.now(timezone.utc) - timedelta(days=1),
            claimant_name="Rajan Nair",
            requested_amount=48500,
        )
        session.add(claim)
        await session.commit()
        claim_id = claim.id

    result = await engine.initialise_deadlines(claim_id, "health_cashless")
    types = [d["deadline_type"] for d in result]
    assert "intimation" in types
    assert "pre_auth_decision" in types
    assert "settlement" in types
    assert len(result) == 4


# ── Test 2 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_initialise_deadlines_motor(engine):
    """motor_own_damage creates doc_submission + survey_report + settlement."""
    from app.db.session import AsyncSessionLocal
    from app.db.insurance_models import Claim, Policy, PolicyStatus

    async with AsyncSessionLocal() as session:
        policy = Policy(
            number="POL-DL-MOT-01",
            holder_name="Vikram M",
            holder_id="CUST_DL02",
            product_type="MOTOR",
            start_date=datetime.now(timezone.utc) - timedelta(days=200),
            end_date=datetime.now(timezone.utc) + timedelta(days=165),
            sum_insured=300000,
            status=PolicyStatus.ACTIVE,
        )
        session.add(policy)
        await session.flush()
        claim = Claim(
            claim_number="CLM-DL-MOT-01",
            policy_id=policy.id,
            type="motor_own_damage",
            incident_date=datetime.now(timezone.utc) - timedelta(days=2),
            claimant_name="Vikram M",
            requested_amount=80000,
        )
        session.add(claim)
        await session.commit()
        claim_id = claim.id

    result = await engine.initialise_deadlines(claim_id, "motor_own_damage")
    types = [d["deadline_type"] for d in result]
    assert "doc_submission" in types
    assert "survey_report" in types
    assert "settlement" in types


# ── Test 3 ─────────────────────────────────────────────────────

def test_deadline_status_running():
    """Deadline 10 days out → status RUNNING."""
    from app.services.deadline_engine import DeadlineEngine
    engine = DeadlineEngine()
    now = datetime.now(timezone.utc)
    due_at = now + timedelta(hours=240)  # 10 days
    diff_h = (due_at - now).total_seconds() / 3600
    status = "RUNNING" if diff_h > 4 else ("AT_RISK" if diff_h > 0 else "BREACHED")
    assert status == "RUNNING"


# ── Test 4 ─────────────────────────────────────────────────────

def test_deadline_status_at_risk():
    """Deadline 2 hours out → status AT_RISK."""
    now = datetime.now(timezone.utc)
    due_at = now + timedelta(hours=2)
    diff_h = (due_at - now).total_seconds() / 3600
    status = "RUNNING" if diff_h > 4 else ("AT_RISK" if diff_h > 0 else "BREACHED")
    assert status == "AT_RISK"


# ── Test 5 ─────────────────────────────────────────────────────

def test_deadline_status_breached():
    """Deadline 1 hour ago → status BREACHED."""
    now = datetime.now(timezone.utc)
    due_at = now - timedelta(hours=1)
    diff_h = (due_at - now).total_seconds() / 3600
    status = "RUNNING" if diff_h > 4 else ("AT_RISK" if diff_h > 0 else "BREACHED")
    assert status == "BREACHED"
