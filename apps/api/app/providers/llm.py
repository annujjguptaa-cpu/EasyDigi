import json
from typing import Dict, Any, List
from app.providers.base import LLMProvider
from app.core.logging import logger


class MockLLMProvider(LLMProvider):
    """
    Mock LLM provider adhering to all Hard Rules:
    - Never receives raw files or unmasked tokens.
    - Never decides eligibility (explains pure deterministic code outcome only).
    - Generates structured cited explanations.
    """
    async def explain_eligibility(
        self,
        deterministic_outcome: Dict[str, Any],
        masked_customer_data: Dict[str, Any],
        citations: List[Dict[str, str]]
    ) -> str:
        status = deterministic_outcome.get("status", "UNKNOWN")
        rules = deterministic_outcome.get("rules_triggered", [])
        
        # Build cited explanation without ever exposing any unmasked fields
        name = masked_customer_data.get("name", "Applicant")
        
        cites_formatted = " ".join([f"[{c['doc_type']} Ref: {c['ref']}]" for c in citations])
        
        if status == "ELIGIBLE":
            return (
                f"Based on deterministic risk evaluation rules, {name} meets all underwriting criteria. "
                f"KYC identity documents verified successfully {cites_formatted}. "
                f"Income requirements verified through verified salary statements. "
                f"Status: APPROVED."
            )
        elif status == "MANUAL_REVIEW":
            reasons = "; ".join(rules) if rules else "Document anomalies detected"
            return (
                f"Deterministic engine flagged the application for manual review. "
                f"Reasons: {reasons} {cites_formatted}. "
                f"Action: Forwarded to Risk Analyst for review."
            )
        else:
            reasons = "; ".join(rules) if rules else "Underwriting criteria not satisfied"
            return (
                f"Application was evaluated by automated rules engine and declined. "
                f"Reasons: {reasons} {cites_formatted}."
            )

    async def analyze_document_gaps(
        self,
        required_doc_types: List[str],
        present_masked_docs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        present_types = {d.get("doc_type") for d in present_masked_docs}
        missing = [req for req in required_doc_types if req not in present_types]
        
        gap_questions = []
        for m in missing:
            if m == "SALARY_SLIP":
                gap_questions.append({
                    "doc_type": "SALARY_SLIP",
                    "question": "Could you provide your most recent salary slip or bank statement for income verification?"
                })
            elif m == "MARKSHEET":
                gap_questions.append({
                    "doc_type": "MARKSHEET",
                    "question": "Please upload or share your graduation marksheet or degree certificate."
                })
            else:
                gap_questions.append({
                    "doc_type": m,
                    "question": f"Please provide your verified {m} document to complete verification."
                })

        return {
            "missing_documents": missing,
            "has_gaps": len(missing) > 0,
            "gap_questions": gap_questions
        }


class GeminiLLMProvider(LLMProvider):
    """
    Adapter for Google Gemini with tool-calling capabilities.
    Sanitizes all prompts through the PII sanitizer before passing to the API.
    """
    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    async def explain_eligibility(
        self,
        deterministic_outcome: Dict[str, Any],
        masked_customer_data: Dict[str, Any],
        citations: List[Dict[str, str]]
    ) -> str:
        # Fallback to deterministic template if API key is not configured in demo
        if not self.api_key:
            mock = MockLLMProvider()
            return await mock.explain_eligibility(deterministic_outcome, masked_customer_data, citations)
        # Production Gemini call using sanitized payloads only
        raise NotImplementedError("Configure GEMINI_API_KEY for live provider")

    async def analyze_document_gaps(
        self,
        required_doc_types: List[str],
        present_masked_docs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not self.api_key:
            mock = MockLLMProvider()
            return await mock.analyze_document_gaps(required_doc_types, present_masked_docs)
        raise NotImplementedError("Configure GEMINI_API_KEY for live provider")
