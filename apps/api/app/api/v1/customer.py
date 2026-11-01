"""
Customer-facing public API — no auth required (token IS the credential).
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.db.session import get_db
from app.db.models import VerificationRequest, Document, DocumentType, DocumentStatus, RequestStatus
from app.services.case_service import transition_state
from app.services.notification_service import emit_event

router = APIRouter(prefix="/c", tags=["Customer Link"])


class ConsentBody(BaseModel):
    agreed: bool


class DocumentSubmitBody(BaseModel):
    profile_key: str  # "clean_file" | "name_mismatch" | "missing_docs"
    selected_documents: Optional[List[str]] = None


class SelectDocumentsBody(BaseModel):
    selected_documents: List[str]


@router.post("/{token}/select-documents")
async def select_documents(token: str, body: SelectDocumentsBody, db: AsyncSession = Depends(get_db)):
    case = await _get_case_by_token(db, token)
    case.required_documents = body.selected_documents
    await transition_state(
        db, case, "documents_selected", "CUSTOMER",
        details={"selected": body.selected_documents},
        notify_staff_id=case.created_by_staff_id,
        notify_message=f"Customer selected {len(body.selected_documents)} documents for {case.reference_code}"
    )
    return {"workflow_state": case.workflow_state, "selected_documents": case.required_documents}


@router.post("/{token}/decline")
async def decline_wish(token: str, db: AsyncSession = Depends(get_db)):
    case = await _get_case_by_token(db, token)
    await transition_state(
        db, case, "declined", "CUSTOMER",
        notify_staff_id=case.created_by_staff_id,
        notify_message=f"Customer declined document request for {case.reference_code}"
    )
    return {"workflow_state": "declined"}


# Mock DigiLocker profile data for each seed customer
MOCK_PROFILES = {
    "clean_file": {
        "name": "Rahul Verma",
        "documents": [
            {"type": "PAN", "status": "VERIFIED", "masked_fields": {"name": "Rahul Verma", "id_last4": "9921"}},
            {"type": "AADHAAR_OFFLINE", "status": "VERIFIED", "masked_fields": {"name": "Rahul Verma", "id_last4": "4001"}},
            {"type": "SALARY_SLIP", "status": "VERIFIED", "masked_fields": {"monthly_net_pay": 85000, "employer": "TechCorp Pvt Ltd"}},
            {"type": "BANK_STATEMENT", "status": "VERIFIED", "masked_fields": {"avg_balance": 120000}},
        ]
    },
    "name_mismatch": {
        "name": "Priya S. Sharma",
        "documents": [
            {"type": "PAN", "status": "VERIFIED", "masked_fields": {"name": "Priya Sharma", "id_last4": "9922"}},
            {"type": "AADHAAR_OFFLINE", "status": "MISMATCH", "masked_fields": {"name": "Priya Sunita Sharma", "id_last4": "5002"}},
            {"type": "SALARY_SLIP", "status": "VERIFIED", "masked_fields": {"monthly_net_pay": 62000, "employer": "EduWorks"}},
        ]
    },
    "missing_docs": {
        "name": "Amit Patel",
        "documents": [
            {"type": "PAN", "status": "VERIFIED", "masked_fields": {"name": "Amit Patel", "id_last4": "9923"}},
        ]
    },
}


@router.get("/{token}")
async def get_case_for_customer(token: str, db: AsyncSession = Depends(get_db)):
    case = await _get_case_by_token(db, token)
    return {
        "reference_code": case.reference_code,
        "customer_name": case.customer_name,
        "loan_type": case.loan_type,
        "required_documents": case.required_documents or [],
        "workflow_state": case.workflow_state,
        "expires_at": case.link_expires_at.isoformat() if case.link_expires_at else None,
        "bank_name": "Apex Mutual Bank (Demo)",
    }


@router.post("/{token}/open")
async def mark_link_opened(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    case = await _get_case_by_token(db, token)
    if case.workflow_state == "link_created":
        case.link_opened_at = datetime.utcnow()
        await transition_state(
            db, case, "link_opened", "CUSTOMER",
            details={"ip_hash": token[:8]},
            notify_staff_id=case.created_by_staff_id,
            notify_message=f"Customer opened link for {case.reference_code}",
        )
    return {"workflow_state": case.workflow_state}


@router.post("/{token}/consent")
async def give_consent(token: str, body: ConsentBody, db: AsyncSession = Depends(get_db)):
    case = await _get_case_by_token(db, token)
    if not body.agreed:
        raise HTTPException(status_code=400, detail="Consent not given")
    if case.workflow_state not in ("documents_selected", "link_opened", "link_created"):
        raise HTTPException(status_code=409, detail=f"Already in state: {case.workflow_state}")
    await transition_state(
        db, case, "consent_given", "CUSTOMER",
        notify_staff_id=case.created_by_staff_id,
        notify_message=f"Consent given for {case.reference_code}",
    )
    return {"workflow_state": case.workflow_state}


@router.post("/{token}/documents")
async def submit_documents(token: str, body: DocumentSubmitBody, db: AsyncSession = Depends(get_db)):
    case = await _get_case_by_token(db, token)
    if case.workflow_state not in ("consent_given", "documents_selected", "link_opened", "link_created"):
        raise HTTPException(status_code=409, detail=f"Cannot submit documents in state: {case.workflow_state}")

    profile = MOCK_PROFILES.get(body.profile_key)
    if not profile:
        raise HTTPException(status_code=400, detail=f"Unknown profile key: {body.profile_key}")

    # Clear previous docs if any for this case, add new docs
    await db.execute(delete(Document).where(Document.verification_request_id == case.id))

    allowed_filter = body.selected_documents if body.selected_documents else case.required_documents
    docs_to_add = []
    for doc_data in profile["documents"]:
        if not allowed_filter or doc_data["type"] in allowed_filter:
            doc = Document(
                verification_request_id=case.id,
                doc_type=DocumentType(doc_data["type"]),
                status=DocumentStatus(doc_data["status"]),
                masked_fields=doc_data["masked_fields"],
            )
            db.add(doc)
            docs_to_add.append(doc_data)

    # Determine wish outcome: granted vs partial
    required_types = set(case.required_documents or [])
    fetched_types = {d["type"] for d in docs_to_add}
    missing_required = required_types - fetched_types

    new_state = "wish_partial" if missing_required else "wish_granted"

    from app.services import mock_digilocker_service
    # Record in DigiLocker activity & active consent
    mock_digilocker_service.record_activity(
        requester="Apex Mutual Bank",
        purpose=f"Verification for {case.loan_type}",
        documents=list(fetched_types),
        expiry="24 Hours"
    )
    mock_digilocker_service.add_consent(
        token=token,
        requester="Apex Mutual Bank",
        scopes=list(fetched_types)
    )

    await transition_state(
        db, case, new_state, "CUSTOMER",
        details={"profile_key": body.profile_key, "doc_count": len(docs_to_add)},
        notify_staff_id=case.created_by_staff_id,
        notify_message=f"Wish granted: {len(docs_to_add)} documents received for {case.reference_code}" if new_state == "wish_granted" else f"Wish partly granted: {len(docs_to_add)} documents received for {case.reference_code}",
    )
    return {
        "workflow_state": new_state,
        "documents": [{"type": d["type"], "status": d["status"]} for d in docs_to_add],
        "missing_documents": list(missing_required)
    }


@router.get("/{token}/documents")
async def get_documents(token: str, db: AsyncSession = Depends(get_db)):
    case = await _get_case_by_token(db, token)
    result = await db.execute(select(Document).where(Document.verification_request_id == case.id))
    docs = result.scalars().all()
    return [{"type": d.doc_type.value, "status": d.status.value, "masked_fields": d.masked_fields} for d in docs]


# ── Helper ─────────────────────────────────────────────────────────────────────
async def _get_case_by_token(db: AsyncSession, token: str) -> VerificationRequest:
    result = await db.execute(select(VerificationRequest).where(VerificationRequest.link_token == token))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Link not found")
    now = datetime.utcnow()
    if case.link_expires_at and now > case.link_expires_at:
        raise HTTPException(status_code=410, detail="This link has expired")
    if case.workflow_state == "decided":
        raise HTTPException(status_code=410, detail="This link has already been completed")
    return case
