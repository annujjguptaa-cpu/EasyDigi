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
            ("kyc_officer@apexbank-demo.com", StaffRole.KYC_OFFICER, Department.KYC),
            ("risk_analyst@apexbank-demo.com", StaffRole.RISK_ANALYST, Department.RISK),
            ("credit_manager@apexbank-demo.com", StaffRole.CREDIT_MANAGER, Department.CREDIT),
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

        # 3. Seed 3 Fictional Customers
        customer_folders = [
            ("customer_clean", "clean_file", RequestStatus.READY_FOR_REVIEW),
            ("customer_name_mismatch", "name_mismatch", RequestStatus.GAPS_DETECTED),
            ("customer_missing_docs", "missing_docs", RequestStatus.PENDING_CONSENT)
        ]

        for folder, label, req_status in customer_folders:
            meta_path = os.path.join(SEED_DIR, folder, "metadata.json")
            if not os.path.exists(meta_path):
                continue

            with open(meta_path, "r", encoding="utf-8") as f:
                cust_data = json.load(f)

            # Check if customer already seeded
            existing_vreq = await session.execute(
                select(VerificationRequest).where(VerificationRequest.customer_fictional_id == cust_data["customer_id"])
            )
            v_req = existing_vreq.scalar_one_or_none()
            if not v_req:
                # Verification Request
                v_req = VerificationRequest(
                    organisation_id=org.id,
                    reference_code=f"REQ-{label.upper()}-{uuid.uuid4().hex[:6]}",
                    customer_fictional_id=cust_data["customer_id"],
                    customer_name=cust_data["name"],
                    loan_type="PERSONAL_LOAN",
                    requested_amount=500000,
                    status=req_status
                )
                session.add(v_req)
                await session.flush()

                # Active Customer Session
                c_sess = CustomerSession(
                    verification_request_id=v_req.id,
                    session_token=f"sess_{uuid.uuid4().hex}",
                    status="INITIATED" if req_status == RequestStatus.PENDING_CONSENT else "COMPLETED",
                    expires_at=datetime.utcnow() + timedelta(days=7)
                )
                session.add(c_sess)

                # Insert masked documents
                for doc_item in cust_data.get("documents", []):
                    doc = Document(
                        verification_request_id=v_req.id,
                        doc_type=DocumentType(doc_item["type"]),
                        status=DocumentStatus(doc_item["status"]),
                        encrypted_blob_ref=f"blob_vault_{uuid.uuid4().hex[:12]}",
                        masked_fields=doc_item.get("masked_fields", {})
                    )
                    session.add(doc)

                # Department Task
                task = DepartmentTask(
                    verification_request_id=v_req.id,
                    department=Department.KYC,
                    assigned_to_id=staff_map[Department.KYC].id,
                    status="PENDING",
                    cited_summary=f"Automated ingestion completed for {cust_data['name']}. Fictional test profile: {label}."
                )
                session.add(task)

        await session.commit()
        logger.info("Successfully seeded 3 fictional customer profiles and bank staff.")


if __name__ == "__main__":
    asyncio.run(seed_database())
