import logging
from app.core.logging import MaskingLogFilter


def test_pii_masking_aadhaar():
    text = "User submitted Aadhaar 1234 5678 9012 for verification."
    masked = MaskingLogFilter.mask_text(text)
    assert "1234 5678" not in masked
    assert "9012" in masked
    assert "XXXXXXXX9012" in masked


def test_pii_masking_pan():
    text = "Extracted PAN ABCDE1234F from applicant."
    masked = MaskingLogFilter.mask_text(text)
    assert "ABCDE1234F" not in masked
    assert "ABCDEXXXXF" in masked


def test_pii_masking_bearer_token():
    text = "Header: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secretpayload"
    masked = MaskingLogFilter.mask_text(text)
    assert "secretpayload" not in masked
    assert "[REDACTED_TOKEN]" in masked


def test_pii_masking_otp():
    text = "Generated otp: 123456 for phone verification"
    masked = MaskingLogFilter.mask_text(text)
    assert "123456" not in masked
    assert "[REDACTED_OTP]" in masked
