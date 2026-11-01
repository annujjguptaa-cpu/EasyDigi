import pytest
import time
from httpx import AsyncClient
from app.providers.digilocker import MockDigiLockerProvider, _MOCK_OAUTH_STORE, _MOCK_CODE_STORE
from app.core.eligibility import DeterministicEligibilityEngine


@pytest.mark.asyncio
async def test_digilocker_oauth_flow_and_security(client: AsyncClient):
    # 1. Start flow
    start_res = await client.get("/api/v1/auth/digilocker/start?session_id=sess_test_123")
    assert start_res.status_code == 200
    start_data = start_res.json()
    state = start_data["state"]
    assert "mock-digilocker" in start_data["authorization_url"]

    # 2. Grant consent on mock screen
    grant_res = await client.post("/api/v1/auth/digilocker/mock-consent", json={
        "state": state,
        "action": "GRANT",
        "customer_id": "customer_clean",
        "demo_aadhaar_input": "999988887777",
        "demo_otp_input": "123456"
    })
    assert grant_res.status_code == 200
    grant_data = grant_res.json()
    code = grant_data["code"]
    assert "DEMO ONLY" in grant_data["demo_notice"]

    # 3. Exchange code for token
    token_res = await client.get(f"/api/v1/auth/digilocker/callback?code={code}&state={state}")
    assert token_res.status_code == 200
    token_data = token_res.json()
    access_token = token_data["access_token"]
    assert "mock_dl_token_" in access_token

    # 4. TEST SECURITY: Replayed code rejected
    replayed_res = await client.get(f"/api/v1/auth/digilocker/callback?code={code}&state={state}")
    assert replayed_res.status_code == 400

    # 5. TEST SECURITY: State mismatch rejected
    mismatch_res = await client.get(f"/api/v1/auth/digilocker/callback?code=fake_code&state=non_existent_state")
    assert mismatch_res.status_code == 400

    # 6. Fetch documents with valid token
    doc_res = await client.get(f"/api/v1/digilocker/documents?token={access_token}")
    assert doc_res.status_code == 200
    assert len(doc_res.json()["documents"]) >= 3


@pytest.mark.asyncio
async def test_digilocker_deny_path_leaves_no_token(client: AsyncClient):
    start_res = await client.get("/api/v1/auth/digilocker/start?session_id=sess_deny_test")
    state = start_res.json()["state"]

    deny_res = await client.post("/api/v1/auth/digilocker/mock-consent", json={
        "state": state,
        "action": "DENY"
    })
    assert deny_res.status_code == 200
    deny_data = deny_res.json()
    assert deny_data["status"] == "DENIED"
    assert "code" not in deny_data


@pytest.mark.asyncio
async def test_digilocker_expired_state():
    provider = MockDigiLockerProvider()
    res = await provider.create_authorization_url("sess_expired_test", ["KYC"])
    state = res["state"]
    # Manually expire state
    _MOCK_OAUTH_STORE[state]["expires_at"] = time.time() - 10

    with pytest.raises(ValueError, match="expired"):
        await provider.create_mock_grant(state)


def test_deterministic_eligibility_clean_file():
    customer_data = {"name": "Rahul Verma"}
    documents = [
        {"doc_type": "PAN", "masked_fields": {"name": "Rahul Verma", "pan_masked": "ABCDE1234F"}},
        {"doc_type": "AADHAAR_OFFLINE", "masked_fields": {"name": "Rahul Verma", "id_last4": "4321"}},
        {"doc_type": "SALARY_SLIP", "masked_fields": {"monthly_net_pay": 80000}}
    ]
    res = DeterministicEligibilityEngine.evaluate(customer_data, documents, loan_amount=500000)
    assert res["status"] == "ELIGIBLE"
    assert res["computed_by_code"] is True


def test_deterministic_eligibility_name_mismatch():
    customer_data = {"name": "Priya Sharma"}
    documents = [
        {"doc_type": "PAN", "masked_fields": {"name": "Priya Sharma", "pan_masked": "BKDPA9876Q"}},
        {"doc_type": "AADHAAR_OFFLINE", "masked_fields": {"name": "Priya Sunil Sharma", "id_last4": "8765"}},
        {"doc_type": "SALARY_SLIP", "masked_fields": {"monthly_net_pay": 70000}}
    ]
    res = DeterministicEligibilityEngine.evaluate(customer_data, documents, loan_amount=500000)
    assert res["status"] == "MANUAL_REVIEW"
    assert any("NAME_MISMATCH" in rule for rule in res["rules_triggered"])
