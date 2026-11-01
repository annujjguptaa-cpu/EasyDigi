from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import (
    CustomerSession, VerificationRequest, Document, ConsentLog,
    Department, RequestStatus
)
from app.services.consent_service import DepartmentSliceService

router = APIRouter()


class SubmitConsentRequest(BaseModel):
    session_token: str
    granted_scopes: List[str]  # e.g. ["KYC_VERIFICATION", "INCOME_ANALYSIS"]
    action: str = "GRANT"      # "GRANT" or "DENY"


@router.get("/consent/session/{session_token}")
async def get_consent_session(
    session_token: str,
    db: AsyncSession = Depends(get_db)
):
    """Fetch consent request metadata for the customer's PWA consent link."""
    q = select(CustomerSession).where(CustomerSession.session_token == session_token)
    res = await db.execute(q)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Invalid or expired consent session")

    # Fetch verification request
    v_q = select(VerificationRequest).where(VerificationRequest.id == session.verification_request_id)
    v_res = await db.execute(v_q)
    v_req = v_res.scalar_one_or_none()
    if not v_req:
        raise HTTPException(status_code=404, detail="Verification request not found")

    return {
        "session_token": session.session_token,
        "customer_name": v_req.customer_name,
        "loan_type": v_req.loan_type,
        "requested_amount": v_req.requested_amount,
        "status": session.status,
        "expires_at": session.expires_at.isoformat(),
        "requested_categories": [
            {
                "scope": "KYC_VERIFICATION",
                "label": "Identity Verification",
                "description": "Offline Aadhaar XML (last 4 digits only) and PAN record"
            },
            {
                "scope": "INCOME_ANALYSIS",
                "label": "Income Verification",
                "description": "Recent salary slip and employer verification"
            },
            {
                "scope": "ACADEMIC_CHECK",
                "label": "Education Verification",
                "description": "Graduation marksheet or degree certificate"
            }
        ]
    }


@router.post("/consent/submit")
async def submit_consent(
    payload: SubmitConsentRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Records customer consent decision into immutable consent_logs and updates session status.
    """
    q = select(CustomerSession).where(CustomerSession.session_token == payload.session_token)
    res = await db.execute(q)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Consent session not found")

    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "Unknown")

    # Record in consent logs
    consent_log = ConsentLog(
        session_id=session.id,
        action=payload.action,
        scopes=payload.granted_scopes,
        ip_address=client_ip,
        user_agent=user_agent
    )
    db.add(consent_log)

    # Update session status
    if payload.action == "GRANT":
        session.status = "CONSENT_GRANTED"
    else:
        session.status = "CONSENT_DENIED"

    await db.commit()
    return {
        "status": session.status,
        "granted_scopes": payload.granted_scopes,
        "message": "Consent preferences recorded in immutable audit log."
    }


@router.get("/bank/requests/{verification_request_id}/slice")
async def get_department_slice_view(
    verification_request_id: str,
    department: str = "KYC",
    db: AsyncSession = Depends(get_db)
):
    """
    Lender department slice endpoint: returns only permitted document fields
    for the specified department (KYC, RISK, CREDIT, OPERATIONS), plus code-driven
    eligibility and cited LLM summary.
    """
    try:
        dept_enum = Department(department.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid department '{department}'. Must be KYC, RISK, CREDIT, or OPERATIONS.")

    try:
        slice_data = await DepartmentSliceService.get_department_slice(
            db=db,
            verification_request_id=verification_request_id,
            department=dept_enum
        )
        return slice_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
