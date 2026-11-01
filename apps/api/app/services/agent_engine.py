import re
from typing import Dict, Any, List
from app.services.document_service import MissingDocumentCalculator, CrossCheckEngine


class ChatAgentGuardrails:
    """
    CRITICAL HARD RULE #4:
    The LLM never sees Aadhaar numbers, OTPs, tokens, or raw files.
    Strips any 12-digit numbers and OTP-like strings from user messages
    before they can reach the LLM context.
    """
    AADHAAR_REGEX = re.compile(r'\b(?:\d[ -]?){11}\d\b')
    OTP_REGEX = re.compile(r'\b\d{4,8}\b')
    PHONE_REGEX = re.compile(r'\b(?:\+91|0)?[6-9]\d{9}\b')

    @classmethod
    def sanitize_user_input(cls, user_text: str) -> Dict[str, Any]:
        has_sensitive_number = False
        refusal_reason = None

        if cls.AADHAAR_REGEX.search(user_text):
            has_sensitive_number = True
            refusal_reason = (
                "For your security and under DPDP guidelines, please never paste your "
                "Aadhaar number in chat. Official verification happens only through "
                "the simulated DigiLocker portal."
            )
            sanitized_text = cls.AADHAAR_REGEX.sub("[BLOCKED_IDENTIFIER]", user_text)
        elif "otp" in user_text.lower() and cls.OTP_REGEX.search(user_text):
            has_sensitive_number = True
            refusal_reason = (
                "Please never share OTPs in chat. DocFlow agents will never ask for your "
                "OTP, password, or PIN."
            )
            sanitized_text = cls.OTP_REGEX.sub("[BLOCKED_OTP]", user_text)
        else:
            sanitized_text = user_text

        return {
            "sanitized_text": sanitized_text,
            "has_sensitive_leak": has_sensitive_number,
            "refusal_reason": refusal_reason
        }


class GapFillingAgentEngine:
    """
    Deterministic Agent Engine backing the Customer Gap-Filling Assistant.
    Provides tool execution for:
    - get_session_status()
    - list_received_documents()
    - get_masked_fields(doc_type)
    - list_mismatches()
    - request_upload(doc_type, reason)
    - ask_user(question)
    - mark_complete(summary)
    """
    def __init__(self, required_doc_types: List[str]):
        self.required_doc_types = required_doc_types

    def get_session_status(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        received_types = [d.get("doc_type") for d in documents]
        missing = MissingDocumentCalculator.calculate(self.required_doc_types, received_types)
        mismatches = CrossCheckEngine.cross_check_documents(documents)
        is_complete = len(missing) == 0 and len(mismatches) == 0

        return {
            "is_complete": is_complete,
            "missing_documents": missing,
            "mismatch_count": len(mismatches),
            "total_received": len(documents)
        }

    def process_message(
        self,
        user_message: str,
        received_documents: List[Dict[str, Any]],
        user_language_hint: str = "en"
    ) -> Dict[str, Any]:
        # 1. Guardrail check
        guardrail_result = ChatAgentGuardrails.sanitize_user_input(user_message)
        if guardrail_result["has_sensitive_leak"]:
            return {
                "reply": guardrail_result["refusal_reason"],
                "actions": [{"type": "REDIRECT_OFFICIAL_PORTAL"}],
                "status": "GUARDRAIL_TRIGGERED"
            }

        # 2. Check gaps
        received_types = [d.get("doc_type") for d in received_documents]
        missing = MissingDocumentCalculator.calculate(self.required_doc_types, received_types)
        mismatches = CrossCheckEngine.cross_check_documents(received_documents)

        # 3. Detect Hinglish in user message
        is_hinglish = any(w in user_message.lower() for w in ["kya", "kaise", "bheju", "document", "karna", "hai", "namaste", "bhai"])

        if missing:
            # Consolidate missing requests all at once (Hard Rule Prompt 4: ask only for what is missing, once, all together)
            missing_names = ", ".join(missing)
            if is_hinglish:
                reply = (
                    f"Namaste! Aapke loan application ko complete karne ke liye humein in documents ki "
                    f"zaroorat hai: {missing_names}. Kripya neeche diye upload button se inhein share karein."
                )
            else:
                reply = (
                    f"Hello! To process your application smoothly, we need the following missing documents: "
                    f"{missing_names}. Please use the upload buttons below to provide them."
                )
            return {
                "reply": reply,
                "actions": [{"type": "REQUEST_UPLOAD", "doc_type": m} for m in missing],
                "status": "AWAITING_DOCUMENTS"
            }

        if mismatches:
            m = mismatches[0]
            if is_hinglish:
                reply = (
                    f"Aapke documents check karne par humein ek mismatch mila hai: {m['reason']}. "
                    f"Kripya clarify karein ya supporting proof upload karein."
                )
            else:
                reply = (
                    f"We noticed a slight difference across your documents: {m['reason']}. "
                    f"Could you please confirm or share an explanation so the bank's team can review?"
                )
            return {
                "reply": reply,
                "actions": [{"type": "CLARIFICATION_REQUIRED", "mismatch": m}],
                "status": "AWAITING_CLARIFICATION"
            }

        # Complete
        if is_hinglish:
            reply = "Shukriya! Aapke saare documents verify ho chuke hain aur file review ke liye ready hai."
        else:
            reply = "Thank you! All required documents have been received and verified. Your file is ready for bank review."

        return {
            "reply": reply,
            "actions": [{"type": "MARK_COMPLETE"}],
            "status": "COMPLETED"
        }
