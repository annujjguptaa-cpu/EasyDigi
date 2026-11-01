import pytest
from datetime import datetime
from app.providers.policy import MockPolicyProvider, InsurerApiProvider
from app.providers.factory import get_policy_provider
from scripts.seed_insurance import seed_insurance_data


@pytest.mark.asyncio
async def test_mock_policy_provider_get_policy():
    await seed_insurance_data()
    provider = get_policy_provider()
    assert isinstance(provider, MockPolicyProvider)

    # Clean health policy
    pol = await provider.get_policy("POL-HLT-2024-001")
    assert pol is not None
    assert pol["holder_name"] == "Rajan Nair"
    assert pol["product_type"] == "HEALTH"
    assert pol["status"] == "ACTIVE"
    assert pol["sum_insured"] == 500000

    # Policy with holder_ref matching
    pol_with_ref = await provider.get_policy("POL-HLT-2024-001", holder_ref="CUST_RAJAN_01")
    assert pol_with_ref is not None

    # Policy with wrong holder_ref
    pol_wrong_ref = await provider.get_policy("POL-HLT-2024-001", holder_ref="SOMEONE_ELSE")
    assert pol_wrong_ref is None


@pytest.mark.asyncio
async def test_policy_verification_success():
    provider = MockPolicyProvider()

    # Valid claim verification
    res = await provider.verify_policy_for_claim(
        policy_number="POL-HLT-2024-001",
        holder_name="Rajan Nair",
        incident_date="2024-06-15T10:00:00"
    )
    assert res["is_valid"] is True
    assert res["error_code"] is None
    assert "policy" in res


@pytest.mark.asyncio
async def test_policy_verification_failure_policy_not_found():
    provider = MockPolicyProvider()

    res = await provider.verify_policy_for_claim(
        policy_number="NON_EXISTENT_POL",
        holder_name="Rajan Nair",
        incident_date="2024-06-15T10:00:00"
    )
    assert res["is_valid"] is False
    assert res["error_code"] == "POLICY_NOT_FOUND"


@pytest.mark.asyncio
async def test_policy_verification_failure_wrong_holder():
    provider = MockPolicyProvider()

    res = await provider.verify_policy_for_claim(
        policy_number="POL-HLT-2024-001",
        holder_name="Impostor Name",
        incident_date="2024-06-15T10:00:00"
    )
    assert res["is_valid"] is False
    assert res["error_code"] == "WRONG_HOLDER"


@pytest.mark.asyncio
async def test_policy_verification_failure_lapsed_policy():
    provider = MockPolicyProvider()

    # Vikram Malhotra's policy is LAPSED
    res = await provider.verify_policy_for_claim(
        policy_number="POL-MOT-2023-003",
        holder_name="Vikram Malhotra",
        incident_date="2023-06-15T10:00:00"
    )
    assert res["is_valid"] is False
    assert res["error_code"] == "LAPSED_POLICY"


@pytest.mark.asyncio
async def test_policy_verification_failure_incident_outside_period():
    provider = MockPolicyProvider()

    # Incident before start date
    res = await provider.verify_policy_for_claim(
        policy_number="POL-HLT-2024-001",
        holder_name="Rajan Nair",
        incident_date="2023-11-15T10:00:00"
    )
    assert res["is_valid"] is False
    assert res["error_code"] == "INCIDENT_OUTSIDE_POLICY_PERIOD"


@pytest.mark.asyncio
async def test_insurer_api_provider_stubs():
    insurer_api = InsurerApiProvider(
        api_base_url="https://sandbox.insurer.example.com",
        client_id="demo_id",
        client_secret="demo_secret"
    )
    with pytest.raises(NotImplementedError):
        await insurer_api.get_policy("POL-001")

    with pytest.raises(NotImplementedError):
        await insurer_api.verify_policy_for_claim("POL-001", "John", datetime.utcnow())
