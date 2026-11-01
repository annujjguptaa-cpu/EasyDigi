import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import VerificationRequest, CustomerSession, Department
from scripts.seed import seed_database


@pytest.mark.asyncio
async def test_department_slice_kyc_and_risk_isolation(client: AsyncClient):
    # Ensure database has seeded staff and create a slice test case
    await seed_database()

    from datetime import datetime, timedelta
    from app.db.models import Organisation, Document, DocumentType, DocumentStatus
    async with AsyncSessionLocal() as session:
        org_res = await session.execute(select(Organisation).where(Organisation.code == "APEX_BANK_DEMO"))
        org = org_res.scalar_one()

        v_req = VerificationRequest(
            organisation_id=org.id,
            reference_code="REQ-TEST-SLICE",
            customer_fictional_id="cust_clean_001",
            customer_name="Rahul Verma",
            loan_type="HOME_LOAN",
            status="READY_FOR_REVIEW"
        )
        session.add(v_req)
        await session.flush()
        req_id = v_req.id

        c_sess = CustomerSession(
            verification_request_id=req_id,
            session_token="sess_test_slice_token",
            status="INITIATED",
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        session.add(c_sess)

        # Add KYC + Income docs
        session.add(Document(
            verification_request_id=req_id,
            doc_type=DocumentType.PAN,
            status=DocumentStatus.VERIFIED,
            masked_fields={"name": "Rahul Verma", "id_last4": "1234"}
        ))
        session.add(Document(
            verification_request_id=req_id,
            doc_type=DocumentType.AADHAAR_OFFLINE,
            status=DocumentStatus.VERIFIED,
            masked_fields={"name": "Rahul Verma", "id_last4": "5678"}
        ))
        session.add(Document(
            verification_request_id=req_id,
            doc_type=DocumentType.SALARY_SLIP,
            status=DocumentStatus.VERIFIED,
            masked_fields={"monthly_net_pay": 80000}
        ))
        await session.commit()
        session_token = c_sess.session_token

    # 1. Fetch consent session details
    sess_res = await client.get(f"/api/v1/consent/session/{session_token}")
    assert sess_res.status_code == 200
    sess_data = sess_res.json()
    assert sess_data["customer_name"] == "Rahul Verma"
    assert len(sess_data["requested_categories"]) == 3

    # 2. Submit customer consent
    submit_res = await client.post("/api/v1/consent/submit", json={
        "session_token": session_token,
        "granted_scopes": ["KYC_VERIFICATION", "INCOME_ANALYSIS"],
        "action": "GRANT"
    })
    assert submit_res.status_code == 200
    assert submit_res.json()["status"] == "CONSENT_GRANTED"

    # 3. Request KYC Slice: Must ONLY contain identity documents (PAN, AADHAAR), ZERO salary slip
    kyc_slice_res = await client.get(f"/api/v1/bank/requests/{req_id}/slice?department=KYC")
    assert kyc_slice_res.status_code == 200
    kyc_data = kyc_slice_res.json()
    kyc_doc_types = [d["doc_type"] for d in kyc_data["sliced_documents"]]
    assert "PAN" in kyc_doc_types
    assert "AADHAAR_OFFLINE" in kyc_doc_types
    assert "SALARY_SLIP" not in kyc_doc_types  # Privacy isolation guarantee
    assert "MARKSHEET" not in kyc_doc_types

    # 4. Request Risk Slice: Must contain income documents
    risk_slice_res = await client.get(f"/api/v1/bank/requests/{req_id}/slice?department=RISK")
    assert risk_slice_res.status_code == 200
    risk_data = risk_slice_res.json()
    risk_doc_types = [d["doc_type"] for d in risk_data["sliced_documents"]]
    assert "SALARY_SLIP" in risk_doc_types
    assert "AADHAAR_OFFLINE" not in risk_doc_types  # Aadhaar isolated from Risk department

    # 5. Deterministic eligibility outcome check
    assert risk_data["deterministic_eligibility"]["computed_by_code"] is True
    assert risk_data["deterministic_eligibility"]["status"] == "ELIGIBLE"
    assert "Rahul Verma" in risk_data["cited_summary"]
    assert "[SALARY_SLIP" in risk_data["cited_summary"] or "[PAN" in risk_data["cited_summary"]
