from typing import Dict, Any, List


class ThreatModelSecurityAudit:
    """
    Threat model verification & prompt injection guard:
    Hard Rule: Document text and customer messages are treated as DATA,
    NEVER as instructions to the LLM agent.
    """
    INJECTION_PATTERNS = [
        "ignore previous instructions",
        "system prompt",
        "override eligibility",
        "approve loan",
        "drop table",
        "ignore all rules"
    ]

    @classmethod
    def sanitize_untrusted_document_data(cls, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Strips adversarial instruction strings from document metadata fields,
        preventing prompt injection attacks.
        """
        sanitized = {}
        for key, value in document_data.items():
            if isinstance(value, str):
                cleaned = value
                for pat in cls.INJECTION_PATTERNS:
                    if pat in cleaned.lower():
                        cleaned = "[SANITIZED_UNTRUSTED_CONTENT]"
                sanitized[key] = cleaned
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_untrusted_document_data(value)
            else:
                sanitized[key] = value
        return sanitized
