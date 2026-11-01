import pytest
from app.services.agent_engine import ChatAgentGuardrails, GapFillingAgentEngine


def test_guardrails_strip_aadhaar_and_refuse():
    user_msg = "My Aadhaar number is 9876 5432 1098 please verify."
    res = ChatAgentGuardrails.sanitize_user_input(user_msg)
    assert res["has_sensitive_leak"] is True
    assert "9876 5432 1098" not in res["sanitized_text"]
    assert "never paste your Aadhaar" in res["refusal_reason"]


def test_guardrails_strip_otp_and_refuse():
    user_msg = "My OTP is 654321"
    res = ChatAgentGuardrails.sanitize_user_input(user_msg)
    assert res["has_sensitive_leak"] is True
    assert "654321" not in res["sanitized_text"]
    assert "never share OTPs" in res["refusal_reason"]


def test_agent_consolidated_missing_documents_request():
    required = ["PAN", "AADHAAR_MASKED", "SALARY_SLIP", "MARKSHEET"]
    received = [
        {"doc_type": "PAN", "masked_fields": {"name": "Amit Patel"}},
        {"doc_type": "AADHAAR_MASKED", "masked_fields": {"name": "Amit Patel"}}
    ]
    engine = GapFillingAgentEngine(required_doc_types=required)
    res = engine.process_message("What else do you need?", received)
    
    assert res["status"] == "AWAITING_DOCUMENTS"
    # Prompt 4 Hard Rule: ask only for what is missing, once, all together
    assert "SALARY_SLIP" in res["reply"]
    assert "MARKSHEET" in res["reply"]
    actions = [a["doc_type"] for a in res["actions"]]
    assert actions == ["SALARY_SLIP", "MARKSHEET"]


def test_agent_hinglish_response():
    required = ["PAN", "AADHAAR_MASKED", "SALARY_SLIP"]
    received = [
        {"doc_type": "PAN", "masked_fields": {"name": "Amit Patel"}},
        {"doc_type": "AADHAAR_MASKED", "masked_fields": {"name": "Amit Patel"}}
    ]
    engine = GapFillingAgentEngine(required_doc_types=required)
    res = engine.process_message("Bhai aur kya document bheju?", received)
    assert res["status"] == "AWAITING_DOCUMENTS"
    assert "Namaste!" in res["reply"]
    assert "SALARY_SLIP" in res["reply"]


def test_agent_completion_only_when_all_present():
    required = ["PAN", "AADHAAR_MASKED", "SALARY_SLIP"]
    received = [
        {"doc_type": "PAN", "masked_fields": {"name": "Rahul Verma"}},
        {"doc_type": "AADHAAR_MASKED", "masked_fields": {"name": "Rahul Verma"}},
        {"doc_type": "SALARY_SLIP", "masked_fields": {"monthly_net_pay": 85000}}
    ]
    engine = GapFillingAgentEngine(required_doc_types=required)
    res = engine.process_message("Is my file complete?", received)
    assert res["status"] == "COMPLETED"
    assert any(a["type"] == "MARK_COMPLETE" for a in res["actions"])
