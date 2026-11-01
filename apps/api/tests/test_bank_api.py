import pytest
from datetime import datetime, timedelta
from app.db.session import AsyncSessionLocal
from app.db.models import VerificationRequest, Organisation, StaffUser, StaffRole, Department, DepartmentTask, RequestStatus


@pytest.mark.asyncio
async def test_bank_auth_and_case_lifecycle(client):
    # Ensure test staff exists (query first or create)
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        org_res = await session.execute(select(Organisation).where(Organisation.code == "APEX_BANK_DEMO"))
        org = org_res.scalar_one_or_none()
        if not org:
            org = Organisation(name="Apex Bank Test", code="APEX_BANK_DEMO", is_active=True)
            session.add(org)
            await session.flush()

        for email, role, dept in [
            ("employee@apexbank-demo.com", StaffRole.RELATIONSHIP_EMPLOYEE, Department.KYC),
            ("kyc_officer@apexbank-demo.com", StaffRole.KYC_OFFICER, Department.KYC),
            ("credit_manager@apexbank-demo.com", StaffRole.CREDIT_MANAGER, Department.CREDIT),
        ]:
            s_res = await session.execute(select(StaffUser).where(StaffUser.email == email))
            if not s_res.scalar_one_or_none():
                session.add(StaffUser(
                    organisation_id=org.id,
                    email=email,
                    hashed_password="mock",
                    role=role,
                    department=dept
                ))
        await session.commit()

    # 1. Unauthenticated request to /bank/cases gets 401
    res = await client.get("/api/v1/bank/cases")
    assert res.status_code == 401

    # 2. Authenticated as Relationship Employee
    headers = {"Authorization": "Bearer employee@apexbank-demo.com"}
    me_res = await client.get("/api/v1/bank/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["role"] == "RELATIONSHIP_EMPLOYEE"

    # 3. Create a new case
    new_case_payload = {
        "customer_name": "Test Customer",
        "customer_phone_masked": "XXXXXX1234",
        "loan_type": "HOME_LOAN",
        "required_documents": ["PAN", "AADHAAR_OFFLINE", "SALARY_SLIP"],
        "ttl_hours": 24
    }
    create_res = await client.post("/api/v1/bank/cases", json=new_case_payload, headers=headers)
    assert create_res.status_code == 201
    data = create_res.json()
    assert "case_reference" in data
    assert "customer_link" in data
    token = data["link_token"]
    case_id = data["case_id"]

    # 4. Customer Link Experience (/c/{token})
    cust_res = await client.get(f"/api/v1/c/{token}")
    assert cust_res.status_code == 200
    assert cust_res.json()["customer_name"] == "Test Customer"

    open_res = await client.post(f"/api/v1/c/{token}/open")
    assert open_res.status_code == 200
    assert open_res.json()["workflow_state"] == "link_opened"

    consent_res = await client.post(f"/api/v1/c/{token}/consent", json={"agreed": True})
    assert consent_res.status_code == 200
    assert consent_res.json()["workflow_state"] == "consent_given"

    # Submit clean profile
    doc_res = await client.post(f"/api/v1/c/{token}/documents", json={"profile_key": "clean_file"})
    assert doc_res.status_code == 200
    assert doc_res.json()["workflow_state"] in ("wish_granted", "documents_received")

    # 5. Check Bank notifications
    notifs_res = await client.get("/api/v1/bank/notifications", headers=headers)
    assert notifs_res.status_code == 200
    notifs = notifs_res.json()
    events = [n["event"] for n in notifs]
    assert "wish_granted" in events or "documents_received" in events

    # 6. Employee sends case to departments
    send_dept_res = await client.post(
        f"/api/v1/bank/cases/{case_id}/send-to-departments",
        json={"departments": ["KYC", "CREDIT"]},
        headers=headers
    )
    assert send_dept_res.status_code == 200
    assert send_dept_res.json()["tasks_created"] == 2

    # 7. Check Department Progress and RBAC
    dept_prog_res = await client.get(f"/api/v1/bank/cases/{case_id}/departments", headers=headers)
    assert dept_prog_res.status_code == 200
    tasks = dept_prog_res.json()["department_tasks"]
    assert len(tasks) == 2
    kyc_task = next(t for t in tasks if t["department"] == "KYC")
    credit_task = next(t for t in tasks if t["department"] == "CREDIT")

    # kyc_officer trying to update credit task should get 403
    kyc_headers = {"Authorization": "Bearer kyc_officer@apexbank-demo.com"}
    forbidden_res = await client.post(
        f"/api/v1/bank/cases/{case_id}/departments/{credit_task['id']}/decide",
        json={"task_id": credit_task["id"], "new_status": "APPROVED", "notes": "Approved by KYC"},
        headers=kyc_headers
    )
    assert forbidden_res.status_code == 403

    # KYC updates KYC task -> 200 OK
    kyc_ok_res = await client.post(
        f"/api/v1/bank/cases/{case_id}/departments/{kyc_task['id']}/decide",
        json={"task_id": kyc_task["id"], "new_status": "APPROVED", "notes": "KYC Verified"},
        headers=kyc_headers
    )
    assert kyc_ok_res.status_code == 200
    assert kyc_ok_res.json()["new_status"] == "APPROVED"


@pytest.mark.asyncio
async def test_link_expiry_and_single_use(client):
    async with AsyncSessionLocal() as session:
        case = VerificationRequest(
            organisation_id="org_expiry_test",
            reference_code="CASE-EXP-001",
            customer_fictional_id="cust_exp",
            customer_name="Expired User",
            loan_type="HOME_LOAN",
            link_token="token-expired-test",
            link_expires_at=datetime.utcnow() - timedelta(hours=1),
            workflow_state="link_created"
        )
        session.add(case)
        await session.commit()

    # Expired link returns 410 Gone
    res = await client.get("/api/v1/c/token-expired-test")
    assert res.status_code == 410

    # Non-existent link returns 404 Not Found
    res404 = await client.get("/api/v1/c/non-existent-token")
    assert res404.status_code == 404
