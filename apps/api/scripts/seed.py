import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta
from app.db.session import AsyncSessionLocal, engine, Base
from app.db.models import (
    Organisation, StaffUser, StaffRole, Department,
    VerificationRequest, RequestStatus, Document, DocumentType, DocumentStatus,
    CustomerSession, DepartmentTask
)
from app.core.logging import logger

SEED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../seed_data"))


async def seed_database():
    logger.info("Setting up database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        from sqlalchemy import select
        existing_org = await session.execute(select(Organisation).where(Organisation.code == "APEX_BANK_DEMO"))
        org = existing_org.scalar_one_or_none()
        if not org:
            # 1. Create Default Bank Organisation
            org = Organisation(
                name="Apex Mutual Bank (Demo)",
                code="APEX_BANK_DEMO",
                is_active=True
            )
            session.add(org)
            await session.flush()

        # 2. Create Staff Users across departments
        staff_roles = [
            ("employee@apexbank-demo.com", StaffRole.RELATIONSHIP_EMPLOYEE, Department.KYC),
            ("kyc_officer@apexbank-demo.com", StaffRole.KYC_OFFICER, Department.KYC),
            ("risk_analyst@apexbank-demo.com", StaffRole.RISK_ANALYST, Department.RISK),
            ("credit_manager@apexbank-demo.com", StaffRole.CREDIT_MANAGER, Department.CREDIT),
            ("credit_head@apexbank-demo.com", StaffRole.CREDIT_HEAD, Department.CREDIT),
            ("legal_officer@apexbank-demo.com", StaffRole.LEGAL_OFFICER, Department.LEGAL),
            ("tech_officer@apexbank-demo.com", StaffRole.TECHNICAL_OFFICER, Department.TECHNICAL),
            ("ops_specialist@apexbank-demo.com", StaffRole.OPERATIONS, Department.OPERATIONS)
        ]
        staff_map = {}
        for email, role, dept in staff_roles:
            existing_staff = await session.execute(select(StaffUser).where(StaffUser.email == email))
            staff = existing_staff.scalar_one_or_none()
            if not staff:
                staff = StaffUser(
                    organisation_id=org.id,
                    email=email,
                    hashed_password="mock_pbkdf2_hashed_password",
                    role=role,
                    department=dept
                )
                session.add(staff)
            staff_map[dept] = staff
        await session.flush()
        await session.commit()
        logger.info("Successfully seeded clean slate: bank staff accounts created. Zero active cases.")


if __name__ == "__main__":
    asyncio.run(seed_database())
