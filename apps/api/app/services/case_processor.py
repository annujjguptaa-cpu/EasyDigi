from typing import Dict, Any, List
from app.services.document_service import CrossCheckEngine, MissingDocumentCalculator


class BankCaseProcessor:
    """
    Ingests and validates document packages for the bank:
    1. Case Readiness Score (traffic-light: GREEN, AMBER, RED).
    2. Loan-specific checks: salary credits vs salary slips, employer consistency.
    3. Produces single consolidated query if items are missing or inconsistent.
    """
    @classmethod
    def evaluate_case(
        cls,
        required_types: List[str],
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        received_types = [d.get("doc_type") for d in documents]
        missing = MissingDocumentCalculator.calculate(required_types, received_types)
        mismatches = CrossCheckEngine.cross_check_documents(documents)

        # Check loan-specific checks (e.g. salary slip vs bank statement employer)
        salary_doc = next((d for d in documents if d.get("doc_type") in ("SALARY_SLIP", "SALARY")), None)
        bank_doc = next((d for d in documents if d.get("doc_type") == "BANK_STATEMENT"), None)

        if salary_doc and bank_doc:
            sal_emp = salary_doc.get("masked_fields", {}).get("employer_name", "").lower()
            bank_desc = bank_doc.get("masked_fields", {}).get("salary_credit_narration", "").lower()
            if sal_emp and bank_desc and sal_emp not in bank_desc:
                mismatches.append({
                    "type": "EMPLOYER_SALARY_CREDIT_MISMATCH",
                    "severity": "MEDIUM",
                    "reason": f"Salary slip employer '{sal_emp}' does not match bank narration '{bank_desc}'",
                    "doc_a": "SALARY_SLIP",
                    "doc_b": "BANK_STATEMENT"
                })

        # Calculate Readiness Score
        high_severity_count = sum(1 for m in mismatches if m["severity"] == "HIGH")
        medium_severity_count = sum(1 for m in mismatches if m["severity"] == "MEDIUM")

        if len(missing) == 0 and high_severity_count == 0 and medium_severity_count == 0:
            readiness_status = "GREEN"  # Ready for Underwriting
            score = 100
        elif high_severity_count > 0 or len(missing) > 1:
            readiness_status = "RED"    # Gaps / Critical Mismatch
            score = 30
        else:
            readiness_status = "AMBER"  # Minor issues, requires manual maker-checker review
            score = 70

        # Build consolidated query if gaps/issues exist
        consolidated_query = None
        if missing or mismatches:
            reasons = []
            if missing:
                reasons.append(f"Missing required documents: {', '.join(missing)}")
            for m in mismatches:
                reasons.append(m["reason"])
            consolidated_query = {
                "action": "RAISE_CONSOLIDATED_QUERY",
                "summary": "; ".join(reasons),
                "missing": missing,
                "mismatches": mismatches
            }

        return {
            "readiness_status": readiness_status,
            "readiness_score": score,
            "missing_documents": missing,
            "mismatches": mismatches,
            "consolidated_query": consolidated_query
        }
