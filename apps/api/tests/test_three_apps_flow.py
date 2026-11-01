import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timedelta
from app.main import app
from app.db.session import AsyncSessionLocal
from app.db.models import VerificationRequest, Organisation, StaffUser, StaffRole, Department
from app.services import mock_digilocker_service


@pytest.mark.asyncio
async def test_three_apps_end_to_end_flow(client):
    # Ensure fresh slate with staff
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        org_res = await session.execute(select(Organisation).where(Organisation.code == "APEX_BANK_DEMO"))
        org = org_res.scalar_one_or_none()
        if not org:
            org = Organisation(name="Apex Bank Demo", code="APEX_BANK_DEMO", is_active=True)
            session.add(org)
            await session.flush()

        emp_res = await session.execute(select(StaffUser).where(StaffUser.email == "employee@apexbank-demo.com"))
        if not emp_res.scalar_one_or_none():
            session.add(StaffUser(
                organisation_id=org.id,
                email="employee@apexbank-demo.com",
                hashed_password="mock",
                role=StaffRole.RELATIONSHIP_EMPLOYEE,
                department=Department.KYC
            ))
            await session.commit()

    # 1. Bank App (Port 3000): Reset demo data to verify clean slate
    headers = {"Authorization": "Bearer employee@apexbank-demo.com"}
    reset_res = await client.post("/api/v1/bank/reset-demo-data", headers=headers)
    assert reset_res.status_code == 200

    # Verify zero cases exist
    cases_res = await client.get("/api/v1/bank/cases", headers=headers)
    assert cases_res.status_code == 200
    assert len(cases_res.json()) == 0

    # 2. Bank App: Create New Request
    new_case_payload = {
        "customer_name": "Rahul Verma",
        "customer_phone_masked": "XXXXXX9921",
        "loan_type": "HOME_LOAN",
        "required_documents": ["PAN", "AADHAAR_OFFLINE", "SALARY_SLIP"],
        "ttl_hours": 24
    }
    create_res = await client.post("/api/v1/bank/cases", json=new_case_payload, headers=headers)
    assert create_res.status_code == 201
    data = create_res.json()
    token = data["link_token"]
    case_id = data["case_id"]
    assert "3001/w/" in data["customer_link"]

    # 3. Customer App (Port 3001): Customer opens /w/{token}
    cust_res = await client.get(f"/api/v1/c/{token}")
    assert cust_res.status_code == 200
    assert cust_res.json()["customer_name"] == "Rahul Verma"

    # Select documents (ticked and locked)
    sel_res = await client.post(
        f"/api/v1/c/{token}/select-documents",
        json={"selected_documents": ["PAN", "AADHAAR_OFFLINE", "SALARY_SLIP"]}
    )
    assert sel_res.status_code == 200
    assert sel_res.json()["workflow_state"] == "documents_selected"

    # 4. Mock DigiLocker (Port 3002): Consent screen Allow
    consent_res = await client.post(f"/api/v1/c/{token}/consent", json={"agreed": True})
    assert consent_res.status_code == 200

    doc_res = await client.post(
        f"/api/v1/c/{token}/documents",
        json={
            "profile_key": "clean_file",
            "selected_documents": ["PAN", "AADHAAR_OFFLINE", "SALARY_SLIP"]
        }
    )
    assert doc_res.status_code == 200
    assert doc_res.json()["workflow_state"] == "wish_granted"
    assert len(doc_res.json()["documents"]) == 3

    # 5. Verify Mock DigiLocker live update: Activity log gained entry & active consent
    acts_res = await client.get("/api/v1/mock-digilocker/activities")
    assert acts_res.status_code == 200
    acts = acts_res.json()
    assert len(acts) >= 1
    assert acts[0]["requester"] == "Apex Mutual Bank"

    cns_res = await client.get("/api/v1/mock-digilocker/consents")
    assert cns_res.status_code == 200
    assert len(cns_res.json()) >= 1

    # 6. Verify Bank App live update: Notifications gained "Wish granted"
    notifs_res = await client.get("/api/v1/bank/notifications", headers=headers)
    assert notifs_res.status_code == 200
    events = [n["event"] for n in notifs_res.json()]
    assert "wish_granted" in events

    # 7. Customer revokes consent in DigiLocker (Port 3002)
    revoke_res = await client.post(
        "/api/v1/mock-digilocker/revoke",
        json={"token": token}
    )
    assert revoke_res.status_code == 200
    assert revoke_res.json()["status"] == "REVOKED"

    # Verify activity marked revoked
    updated_acts = (await client.get("/api/v1/mock-digilocker/activities")).json()
    assert updated_acts[0]["status"] == "REVOKED"


@pytest.mark.asyncio
async def test_partial_wish_flow_with_missing_docs_profile(client):
    headers = {"Authorization": "Bearer employee@apexbank-demo.com"}
    create_res = await client.post(
        "/api/v1/bank/cases",
        json={
            "customer_name": "Amit Patel",
            "customer_phone_masked": "XXXXXX9923",
            "loan_type": "PERSONAL_LOAN",
            "required_documents": ["PAN", "AADHAAR_OFFLINE", "SALARY_SLIP"],
            "ttl_hours": 24
        },
        headers=headers
    )
    token = create_res.json()["link_token"]

    # Customer submits missing_docs profile
    await client.post(f"/api/v1/c/{token}/consent", json={"agreed": True})
    doc_res = await client.post(
        f"/api/v1/c/{token}/documents",
        json={"profile_key": "missing_docs", "selected_documents": ["PAN", "AADHAAR_OFFLINE", "SALARY_SLIP"]}
    )
    assert doc_res.status_code == 200
    # Because Amit Patel only has PAN, wish is partial
    assert doc_res.json()["workflow_state"] == "wish_partial"
    assert "AADHAAR_OFFLINE" in doc_res.json()["missing_documents"]
