import pytest
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import Organisation, VerificationRequest, Document, StaffUser
from scripts.seed import seed_database


@pytest.mark.asyncio
async def test_seed_database_clean_slate_and_staff_roles():
    # Run seed script
    await seed_database()

    async with AsyncSessionLocal() as session:
        # Check org
        org_res = await session.execute(select(Organisation))
        orgs = org_res.scalars().all()
        assert len(orgs) >= 1

        # Check Staff Users are seeded across required roles
        staff_res = await session.execute(select(StaffUser))
        staff_users = staff_res.scalars().all()
        assert len(staff_users) >= 4
        emails = {u.email for u in staff_users}
        assert "employee@apexbank-demo.com" in emails
        assert "kyc_officer@apexbank-demo.com" in emails
        assert "credit_head@apexbank-demo.com" in emails
