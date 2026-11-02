import pytest
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.insurance_models import Policy, Claim, ClaimDocument, ClaimEvent, FraudFlag
from scripts.seed_insurance import seed_insurance_data


@pytest.mark.asyncio
async def test_insurance_seed_data_loaded():
    # Run seed in test db context
    await seed_insurance_data()

    async with AsyncSessionLocal() as session:
        # Check all 5 seeded policies exist
        policies_res = await session.execute(
            select(Policy).where(Policy.number.in_([
                "POL-HLT-2024-001",
                "POL-HLT-2024-002",
                "POL-MOT-2023-003",
                "POL-MOT-2024-004",
                "POL-LIF-2022-005",
            ]))
        )
        policies = policies_res.scalars().all()
        assert len(policies) == 5

        # Check all 5 seeded claims exist
        claims_res = await session.execute(
            select(Claim).where(Claim.claim_number.in_([
                "CLM-HLT-2024-8801",
                "CLM-HLT-2024-8802",
                "CLM-MOT-2024-8803",
                "CLM-MOT-2024-8804",
                "CLM-LIF-2024-8805",
            ]))
        )
        claims = claims_res.scalars().all()
        assert len(claims) == 5

        # Check clean health claim
        clean_res = await session.execute(
            select(Claim).where(Claim.claim_number == "CLM-HLT-2024-8801")
        )
        clean_claim = clean_res.scalar_one_or_none()
        assert clean_claim is not None
        assert clean_claim.type == "health_cashless"
        assert clean_claim.claimant_name == "Rajan Nair"

        # Check reimbursement mismatch fraud flag
        mismatch_res = await session.execute(
            select(Claim).where(Claim.claim_number == "CLM-HLT-2024-8802")
        )
        mismatch_claim = mismatch_res.scalar_one_or_none()
        assert mismatch_claim is not None
        flags_res = await session.execute(
            select(FraudFlag).where(FraudFlag.claim_id == mismatch_claim.id)
        )
        flags = flags_res.scalars().all()
        assert len(flags) == 1
        assert flags[0].flag_type == "BILL_DISCHARGE_MISMATCH"

        # Check documents for life claim
        life_res = await session.execute(
            select(Claim).where(Claim.claim_number == "CLM-LIF-2024-8805")
        )
        life_claim = life_res.scalar_one_or_none()
        assert life_claim is not None
        docs_res = await session.execute(
            select(ClaimDocument).where(ClaimDocument.claim_id == life_claim.id)
        )
        docs = docs_res.scalars().all()
        assert len(docs) == 4
        doc_types = [d.doc_type for d in docs]
        assert "DEATH_CERTIFICATE" in doc_types
        assert "NOMINEE_ID" in doc_types
