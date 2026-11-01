import pytest
from app.services.bank_exchange import BankPackageExchangeService
from app.services.case_processor import BankCaseProcessor


def test_bank_package_hybrid_encryption_roundtrip():
    service = BankPackageExchangeService()
    files = [
        {"name": "pan.json", "masked_fields": {"name": "Rahul Verma", "pan_masked": "ABXXXXXXXF"}},
        {"name": "aadhaar.json", "masked_fields": {"name": "Rahul Verma", "id_last4": "4321"}}
    ]
    scopes = ["KYC_VERIFICATION", "INCOME_ANALYSIS"]

    # 1. Create client-side encrypted package
    package = service.create_encrypted_package(files, scopes)
    assert "package_sha256" in package
    assert "encrypted_aes_key_b64" in package

    # 2. Bank worker decrypts package
    decrypted = service.decrypt_package_as_bank(package)
    assert len(decrypted["files"]) == 2
    assert decrypted["consented_scopes"] == scopes


def test_bank_package_tampering_rejected():
    service = BankPackageExchangeService()
    package = service.create_encrypted_package([{"name": "doc.json"}], ["KYC"])
    # Tamper with sha256 checksum
    package["package_sha256"] = "0000000000000000000000000000000000000000000000000000000000000000"

    with pytest.raises(ValueError, match="Tampered package rejected"):
        service.decrypt_package_as_bank(package)


def test_consent_revocation():
    service = BankPackageExchangeService()
    res = service.revoke_consent("token_cust_123")
    assert res["status"] == "REVOKED"
    assert res["retention_clock_started"] is True


def test_case_readiness_clean_case():
    required = ["PAN", "AADHAAR_MASKED", "SALARY_SLIP"]
    docs = [
        {"doc_type": "PAN", "masked_fields": {"name": "Rahul Verma"}},
        {"doc_type": "AADHAAR_MASKED", "masked_fields": {"name": "Rahul Verma"}},
        {"doc_type": "SALARY_SLIP", "masked_fields": {"monthly_net_pay": 85000, "employer_name": "Apex Tech"}}
    ]
    res = BankCaseProcessor.evaluate_case(required, docs)
    assert res["readiness_status"] == "GREEN"
    assert res["readiness_score"] == 100
    assert res["consolidated_query"] is None


def test_case_readiness_missing_case_generates_one_query():
    required = ["PAN", "AADHAAR_MASKED", "SALARY_SLIP"]
    docs = [
        {"doc_type": "PAN", "masked_fields": {"name": "Amit Patel"}},
        {"doc_type": "AADHAAR_MASKED", "masked_fields": {"name": "Amit Patel"}}
    ]
    res = BankCaseProcessor.evaluate_case(required, docs)
    assert res["readiness_status"] in ("AMBER", "RED")
    assert res["consolidated_query"] is not None
    assert "SALARY_SLIP" in res["consolidated_query"]["missing"]
