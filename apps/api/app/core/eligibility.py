from typing import Dict, Any, List


class DeterministicEligibilityEngine:
    """
    CRITICAL HARD RULE #5:
    The LLM NEVER decides eligibility. Code decides; the LLM explains.
    Pure deterministic logic for underwriting and risk verification.
    """

    @staticmethod
    def evaluate(
        customer_masked_data: Dict[str, Any],
        documents: List[Dict[str, Any]],
        loan_amount: int = 500000
    ) -> Dict[str, Any]:
        rules_triggered = []
        is_eligible = True
        requires_manual_review = False

        doc_types = {d.get("doc_type") for d in documents}
        
        # Rule 1: Identity & KYC must have PAN and Aadhaar
        if "PAN" not in doc_types:
            rules_triggered.append("MISSING_PAN_RECORD")
            is_eligible = False

        if "AADHAAR_OFFLINE" not in doc_types:
            rules_triggered.append("MISSING_AADHAAR_RECORD")
            is_eligible = False

        # Rule 2: Check Name consistency across PAN and Aadhaar
        pan_name = ""
        aadhaar_name = ""
        for d in documents:
            if d.get("doc_type") == "PAN":
                pan_name = d.get("masked_fields", {}).get("name", "").strip().lower()
            elif d.get("doc_type") == "AADHAAR_OFFLINE":
                aadhaar_name = d.get("masked_fields", {}).get("name", "").strip().lower()

        if pan_name and aadhaar_name and pan_name != aadhaar_name:
            rules_triggered.append(f"NAME_MISMATCH_BETWEEN_PAN_AND_AADHAAR: '{pan_name}' != '{aadhaar_name}'")
            requires_manual_review = True

        # Rule 3: Check Income / Salary requirements for loan amount
        salary_doc = next((d for d in documents if d.get("doc_type") == "SALARY_SLIP"), None)
        if not salary_doc:
            rules_triggered.append("MISSING_SALARY_SLIP")
            is_eligible = False
        else:
            monthly_pay = salary_doc.get("masked_fields", {}).get("monthly_net_pay", 0)
            # Minimum income threshold: monthly net pay * 10 >= loan amount
            if monthly_pay * 10 < loan_amount:
                rules_triggered.append(f"INSUFFICIENT_INCOME_FOR_REQUESTED_AMOUNT: Pay={monthly_pay}, Req={loan_amount}")
                is_eligible = False

        # Determine Final Outcome
        if not is_eligible:
            final_status = "INELIGIBLE"
        elif requires_manual_review:
            final_status = "MANUAL_REVIEW"
        else:
            final_status = "ELIGIBLE"

        return {
            "status": final_status,
            "computed_by_code": True,
            "deterministic_timestamp": "2026-11-01T00:00:00Z",
            "rules_triggered": rules_triggered,
            "evaluated_loan_amount": loan_amount
        }
