import pytest
import time
from app.services.document_service import (
    DocumentClassifier, FieldMasker, CrossCheckEngine,
    MissingDocumentCalculator, DocumentStorageService
)


def test_document_classifier():
    assert DocumentClassifier.classify("pan_card_copy.pdf") == "PAN"
    assert DocumentClassifier.classify("aadhaar_offline.xml") == "AADHAAR_MASKED"
    assert DocumentClassifier.classify("salary_slip_oct.pdf") == "SALARY_SLIP"
    assert DocumentClassifier.classify("btech_degree_marksheet.jpg") == "MARKSHEET"
    assert DocumentClassifier.classify("unknown_document.txt") == "OTHER"


def test_field_masker():
    # PAN masking (first 2 and last 1)
    masked_pan = FieldMasker.mask_pan("ABCDE1234F")
    assert masked_pan == "ABXXXXXXXF"

    # Aadhaar masking (last 4 only)
    masked_aadhaar = FieldMasker.mask_aadhaar("123456789012")
    assert masked_aadhaar == "XXXXXXXX9012"

    # Account number masking
    masked_acc = FieldMasker.mask_account_number("987654321098")
    assert masked_acc.endswith("1098")
    assert "987654" not in masked_acc


def test_cross_check_engine_detects_name_mismatch():
    documents = [
        {
            "doc_type": "PAN",
            "masked_fields": {"name": "Priya Sharma", "dob": "1994-11-22"}
        },
        {
            "doc_type": "AADHAAR_MASKED",
            "masked_fields": {"name": "Priya Sunil Sharma", "dob": "1994-11-22"}
        }
    ]
    mismatches = CrossCheckEngine.cross_check_documents(documents)
    assert len(mismatches) == 1
    m = mismatches[0]
    assert m["type"] == "NAME_MISMATCH"
    assert m["severity"] == "MEDIUM"
    assert "Priya Sharma" in m["reason"]
    assert "Priya Sunil Sharma" in m["reason"]


def test_missing_document_calculator():
    required = ["PAN", "AADHAAR_MASKED", "SALARY_SLIP", "MARKSHEET"]
    received = ["PAN", "AADHAAR_MASKED"]
    missing = MissingDocumentCalculator.calculate(required, received)
    assert missing == ["SALARY_SLIP", "MARKSHEET"]


def test_encrypted_at_rest_storage_and_retention():
    service = DocumentStorageService()
    doc_id = "test_doc_001"
    raw_payload = b"Sample confidential document content"

    # 1. Store encrypted with 1-hour retention
    ref = service.encrypt_and_store(doc_id, raw_payload, retention_hours=1)
    assert ref.startswith("encrypted_ref_")

    # 2. Decrypt round-trip
    decrypted = service.decrypt(doc_id)
    assert decrypted == raw_payload

    # 3. Retention job does not delete before expiry
    now = time.time()
    deleted = service.run_retention_job(current_time=now)
    assert deleted == 0

    # 4. Retention job deletes after expiry (+2 hours)
    future = now + 7200
    deleted_future = service.run_retention_job(current_time=future)
    assert deleted_future == 1

    # 5. Accessing deleted document fails
    with pytest.raises(FileNotFoundError):
        service.decrypt(doc_id)
