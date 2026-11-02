"""
Prompt 10 — Tests: Settlement Service
"""
import pytest
from datetime import datetime, timezone, timedelta


async def _seed_approved_claim(session, claim_number):
    from app.db.insurance_models import Claim, Policy, PolicyStatus, ClaimStatus
    policy = Policy(
        number=f"POL-SS-{claim_number}",
        holder_name="Rajan Nair",
        holder_id=f"CUST_SS_{claim_number}",
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
        type="health_reimbursement",
        incident_date=datetime.now(timezone.utc) - timedelta(days=5),
        claimant_name="Rajan Nair",
        requested_amount=48500,
        status=ClaimStatus.APPROVED,
        approved_amount=48500,
    )
    session.add(claim)
    await session.commit()
    return claim.id


# ── Test 1 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_initiate_settlement_generates_utr():
    """Approved claim → settlement processed, UTR present."""
    from app.db.session import AsyncSessionLocal
    from app.services.settlement_service import SettlementService

    async with AsyncSessionLocal() as session:
        claim_id = await _seed_approved_claim(session, "CLM-SS-01")

    svc = SettlementService()
    result = await svc.initiate_settlement(claim_id, "5678")
    assert result["utr_number"].startswith("UTR")
    assert len(result["utr_number"]) > 10
    assert result["status"] == "PROCESSED"


# ── Test 2 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_settlement_masked_account():
    """bank_account_last4 stored (not full number)."""
    from app.db.session import AsyncSessionLocal
    from app.services.settlement_service import SettlementService

    async with AsyncSessionLocal() as session:
        claim_id = await _seed_approved_claim(session, "CLM-SS-02")

    svc = SettlementService()
    result = await svc.initiate_settlement(claim_id, "9012")
    assert result["bank_account_last4"] == "9012"
    # Full account number should NOT be present
    assert "1234567890" not in str(result)


# ── Test 3 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_settlement_fails_if_not_approved():
    """INTIMATED claim → ValueError."""
    from app.db.session import AsyncSessionLocal
    from app.db.insurance_models import Claim, Policy, PolicyStatus
    from app.services.settlement_service import SettlementService

    async with AsyncSessionLocal() as session:
        policy = Policy(
            number="POL-SS-NOT-APPR",
            holder_name="Test",
            holder_id="CUST_SS_X",
            product_type="HEALTH",
            start_date=datetime.now(timezone.utc) - timedelta(days=100),
            end_date=datetime.now(timezone.utc) + timedelta(days=265),
            sum_insured=300000,
            status=PolicyStatus.ACTIVE,
        )
        session.add(policy)
        await session.flush()
        claim = Claim(
            claim_number="CLM-SS-NOT-APPR",
            policy_id=policy.id,
            type="health_reimbursement",
            incident_date=datetime.now(timezone.utc) - timedelta(days=3),
            claimant_name="Test",
            requested_amount=50000,
            # status defaults to INTIMATED
        )
        session.add(claim)
        await session.commit()
        claim_id = claim.id

    svc = SettlementService()
    with pytest.raises(ValueError, match="APPROVED"):
        await svc.initiate_settlement(claim_id, "1234")


# ── Test 4 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ombudsman_escalation_rejected_claim():
    """REJECTED claim → escalation_ref returned."""
    from app.db.session import AsyncSessionLocal
    from app.db.insurance_models import Claim, Policy, PolicyStatus, ClaimStatus
    from app.services.settlement_service import SettlementService

    async with AsyncSessionLocal() as session:
        policy = Policy(
            number="POL-SS-REJ",
            holder_name="Sunita Rao",
            holder_id="CUST_SS_REJ",
            product_type="HEALTH",
            start_date=datetime.now(timezone.utc) - timedelta(days=100),
            end_date=datetime.now(timezone.utc) + timedelta(days=265),
            sum_insured=300000,
            status=PolicyStatus.ACTIVE,
        )
        session.add(policy)
        await session.flush()
        claim = Claim(
            claim_number="CLM-SS-REJ",
            policy_id=policy.id,
            type="health_reimbursement",
            incident_date=datetime.now(timezone.utc) - timedelta(days=3),
            claimant_name="Sunita Rao",
            requested_amount=50000,
            status=ClaimStatus.REJECTED,
        )
        session.add(claim)
        await session.commit()
        claim_id = claim.id

    svc = SettlementService()
    result = await svc.escalate_to_ombudsman(claim_id, "My claim was incorrectly rejected.")
    assert "escalation_ref" in result
    assert result["escalation_ref"].startswith("OMB-")
    assert "30 working days" in result["message"]


# ── Test 5 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ombudsman_escalation_not_allowed_if_settled():
    """SETTLED claim → ValueError for ombudsman escalation."""
    from app.db.session import AsyncSessionLocal
    from app.db.insurance_models import Claim, Policy, PolicyStatus, ClaimStatus
    from app.services.settlement_service import SettlementService

    async with AsyncSessionLocal() as session:
        policy = Policy(
            number="POL-SS-SETTLED",
            holder_name="Rajan Settled",
            holder_id="CUST_SS_SETTLED",
            product_type="HEALTH",
            start_date=datetime.now(timezone.utc) - timedelta(days=100),
            end_date=datetime.now(timezone.utc) + timedelta(days=265),
            sum_insured=300000,
            status=PolicyStatus.ACTIVE,
        )
        session.add(policy)
        await session.flush()
        claim = Claim(
            claim_number="CLM-SS-SETTLED",
            policy_id=policy.id,
            type="health_reimbursement",
            incident_date=datetime.now(timezone.utc) - timedelta(days=3),
            claimant_name="Rajan Settled",
            requested_amount=50000,
            status=ClaimStatus.SETTLED,
        )
        session.add(claim)
        await session.commit()
        claim_id = claim.id

    svc = SettlementService()
    with pytest.raises(ValueError, match="SETTLED"):
        await svc.escalate_to_ombudsman(claim_id, "I want to escalate.")
