import pytest
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import Organisation, VerificationRequest, Document, StaffUser
from scripts.seed import seed_database


@pytest.mark.asyncio
async def test_seed_database_loads_three_customers():
    # Run seed script
    await seed_database()

    async with AsyncSessionLocal() as session:
        # Check org
        org_res = await session.execute(select(Organisation))
        orgs = org_res.scalars().all()
        assert len(orgs) >= 1

        # Check 3 customers
        req_res = await session.execute(select(VerificationRequest))
        requests = req_res.scalars().all()
        assert len(requests) >= 3

        cust_ids = {r.customer_fictional_id for r in requests}
        assert "cust_clean_001" in cust_ids
        assert "cust_mismatch_002" in cust_ids
        assert "cust_missing_003" in cust_ids

        # Check documents are seeded with masked metadata
        doc_res = await session.execute(select(Document))
        docs = doc_res.scalars().all()
        assert len(docs) >= 8
        for d in docs:
            # Ensure no full Aadhaar or secret leaks into masked fields
            masked = d.masked_fields
            if "id_last4" in masked:
                assert len(masked["id_last4"]) == 4
