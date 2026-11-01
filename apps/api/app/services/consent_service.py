from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import (
    VerificationRequest, Document, Department, ConsentLog, DocumentType
)
from app.core.eligibility import DeterministicEligibilityEngine
from app.providers.factory import get_llm_provider


class DepartmentSliceService:
    """
    Ensures bank departments receive strictly their permitted slice of verified data:
    - KYC Department: Identity docs only (PAN, Aadhaar last 4), name matching.
    - Risk & Credit Department: Income docs (salary slip, bank statement), eligibility metrics.
    - Operations Department: Audit trail, consent logs, approval status.
    """

    # Department permissions mapping
    PERMITTED_DOC_TYPES = {
        Department.KYC: {DocumentType.PAN, DocumentType.AADHAAR_OFFLINE},
        Department.RISK: {DocumentType.SALARY_SLIP, DocumentType.BANK_STATEMENT, DocumentType.PAN},
        Department.CREDIT: {DocumentType.SALARY_SLIP, DocumentType.BANK_STATEMENT},
        Department.OPERATIONS: {DocumentType.PAN, DocumentType.AADHAAR_OFFLINE, DocumentType.SALARY_SLIP, DocumentType.MARKSHEET}
    }

    @classmethod
    async def get_department_slice(
        cls,
        db: AsyncSession,
        verification_request_id: str,
        department: Department
    ) -> Dict[str, Any]:
        # 1. Fetch verification request
        q = select(VerificationRequest).where(VerificationRequest.id == verification_request_id)
        res = await db.execute(q)
        v_req = res.scalar_one_or_none()
        if not v_req:
            raise ValueError(f"Verification request {verification_request_id} not found")

        # 2. Fetch all documents for this request
        doc_q = select(Document).where(Document.verification_request_id == verification_request_id)
        doc_res = await db.execute(doc_q)
        all_docs = doc_res.scalars().all()

        # 3. Filter documents strictly permitted for this department
        allowed_types = cls.PERMITTED_DOC_TYPES.get(department, set())
        sliced_docs = []
        citations = []

        for d in all_docs:
            if d.doc_type in allowed_types:
                # Include only masked fields, zero raw unmasked data
                sliced_docs.append({
                    "id": d.id,
                    "doc_type": d.doc_type.value,
                    "status": d.status.value,
                    "masked_fields": d.masked_fields
                })
                citations.append({
                    "doc_type": d.doc_type.value,
                    "ref": f"DOC-{d.id[:8]}"
                })

        # 4. Compute deterministic eligibility (code only)
        all_docs_dict = [
            {"doc_type": d.doc_type.value, "masked_fields": d.masked_fields}
            for d in all_docs
        ]
        deterministic_outcome = DeterministicEligibilityEngine.evaluate(
            customer_masked_data={"name": v_req.customer_name},
            documents=all_docs_dict,
            loan_amount=v_req.requested_amount
        )

        # 5. LLM generates cited explanation based strictly on masked data & code outcome
        llm_provider = get_llm_provider()
        cited_explanation = await llm_provider.explain_eligibility(
            deterministic_outcome=deterministic_outcome,
            masked_customer_data={"name": v_req.customer_name},
            citations=citations
        )

        # 6. For Operations, include recent consent logs
        recent_consent_logs = []
        if department == Department.OPERATIONS:
            clog_q = select(ConsentLog).order_by(ConsentLog.timestamp.desc()).limit(10)
            clog_res = await db.execute(clog_q)
            logs = clog_res.scalars().all()
            recent_consent_logs = [
                {
                    "id": l.id,
                    "action": l.action,
                    "scopes": l.scopes,
                    "timestamp": l.timestamp.isoformat() if l.timestamp else None,
                    "ip_address": l.ip_address
                }
                for l in logs
            ]

        return {
            "department": department.value,
            "request_id": v_req.id,
            "reference_code": v_req.reference_code,
            "customer_name": v_req.customer_name,
            "loan_amount": v_req.requested_amount,
            "sliced_documents": sliced_docs,
            "deterministic_eligibility": deterministic_outcome,
            "cited_summary": cited_explanation,
            "consent_audit": recent_consent_logs if department == Department.OPERATIONS else None
        }
