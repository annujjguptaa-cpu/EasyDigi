"""
Bank Staff API — RBAC-guarded endpoints.
Auth: Authorization: Bearer <staff_email>  (demo mode; replace with JWT in prod)
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.session import get_db
from app.db.models import (
    StaffUser, StaffRole, VerificationRequest, DepartmentTask, Notification,
    AuditLog, RequestStatus, Department, Document
)
from app.services.case_service import create_case, transition_state, send_to_departments
from app.services.notification_service import subscribe, unsubscribe
from app.core.config import settings
import asyncio
import json

router = APIRouter(prefix="/bank", tags=["Bank Dashboard"])


# ── Auth helper ──────────────────────────────────────────────────────────────
async def get_current_staff(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> StaffUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    email = authorization.removeprefix("Bearer ").strip()
    result = await db.execute(select(StaffUser).where(StaffUser.email == email))
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=401, detail="Unknown staff email")
    return staff


# ── Pydantic models ───────────────────────────────────────────────────────────
class CreateCaseRequest(BaseModel):
    customer_name: str
    customer_phone_masked: str = "XXXXXX9901"
    loan_type: str = "HOME_LOAN"
    required_documents: List[str] = ["PAN", "AADHAAR_OFFLINE", "SALARY_SLIP"]
    ttl_hours: int = 24


class SendToDepartmentsRequest(BaseModel):
    departments: List[str] = ["KYC", "CREDIT", "RISK", "OPERATIONS"]


class QueryRequest(BaseModel):
    message: str


class DepartmentDecisionRequest(BaseModel):
    task_id: str
    new_status: str  # IN_REVIEW | QUERY_RAISED | APPROVED | REJECTED
    notes: str = ""


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get("/me")
async def get_me(staff: StaffUser = Depends(get_current_staff)):
    return {
        "id": staff.id,
        "email": staff.email,
        "role": staff.role.value,
        "department": staff.department.value,
    }


@router.get("/cases")
async def list_cases(
    staff: StaffUser = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VerificationRequest)
        .where(VerificationRequest.organisation_id == staff.organisation_id)
        .order_by(desc(VerificationRequest.created_at))
    )
    cases = result.scalars().all()
    return [_case_summary(c) for c in cases]


@router.post("/cases", status_code=201)
async def create_new_case(
    body: CreateCaseRequest,
    staff: StaffUser = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    case = await create_case(
        db=db,
        created_by=staff,
        customer_name=body.customer_name,
        customer_phone_masked=body.customer_phone_masked,
        loan_type=body.loan_type,
        required_docs=body.required_documents,
        ttl_hours=body.ttl_hours,
    )
    customer_url = f"{settings.CUSTOMER_URL}/w/{case.link_token}"
    return {
        "case_reference": case.reference_code,
        "case_id": case.id,
        "customer_link": customer_url,
        "link_token": case.link_token,
        "expires_at": case.link_expires_at.isoformat() if case.link_expires_at else None,
        "whatsapp_stub": f"https://wa.me/?text=Please+complete+your+document+submission:+{customer_url}",
        "sms_stub": f"sms:?body=Please+complete+your+application:+{customer_url}",
    }


@router.post("/reset-demo-data")
async def reset_demo_data(
    staff: StaffUser = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Bank Admin Action: Wipes all cases, links, notifications, consents and share records.
    Preserves staff users and DigiLocker accounts.
    """
    from sqlalchemy import delete
    from app.db.models import CustomerSession, ConsentLog, SharePackage
    from app.services import mock_digilocker_service

    await db.execute(delete(Notification))
    await db.execute(delete(DepartmentTask))
    await db.execute(delete(Document))
    await db.execute(delete(SharePackage))
    await db.execute(delete(ConsentLog))
    await db.execute(delete(CustomerSession))
    await db.execute(delete(AuditLog))
    await db.execute(delete(VerificationRequest))
    await db.commit()

    mock_digilocker_service.reset_digilocker_state()

    return {"status": "SUCCESS", "message": "Demo data wiped clean. Fresh slate established."}


@router.get("/cases/{case_id}")
async def get_case(
    case_id: str,
    staff: StaffUser = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    case = await _fetch_case(db, case_id, staff.organisation_id)
    # Timeline from audit logs
    logs_result = await db.execute(
        select(AuditLog).where(AuditLog.entity_id == case.id).order_by(AuditLog.created_at)
    )
    logs = logs_result.scalars().all()
    # Documents
    docs_result = await db.execute(
        select(Document).where(Document.verification_request_id == case.id)
    )
    docs = docs_result.scalars().all()
    # Tasks
    tasks_result = await db.execute(
        select(DepartmentTask).where(DepartmentTask.verification_request_id == case.id)
    )
    tasks = tasks_result.scalars().all()

    customer_url = f"{settings.PUBLIC_BASE_URL}/c/{case.link_token}" if case.link_token else None
    return {
        **_case_summary(case),
        "customer_link": customer_url,
        "timeline": [
            {"action": l.action, "actor": l.actor_id, "at": l.created_at.isoformat(), "details": l.details}
            for l in logs
        ],
        "documents": [
            {"id": d.id, "type": d.doc_type.value, "status": d.status.value, "masked_fields": d.masked_fields}
            for d in docs
        ],
        "department_tasks": [
            {"id": t.id, "department": t.department.value, "status": t.status, "summary": t.cited_summary}
            for t in tasks
        ],
        "readiness_score": _compute_readiness(docs, case.required_documents or []),
    }


@router.post("/cases/{case_id}/send-to-departments")
async def send_case_to_departments(
    case_id: str,
    body: SendToDepartmentsRequest,
    staff: StaffUser = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    case = await _fetch_case(db, case_id, staff.organisation_id)
    allowed_states = ("documents_received", "ready_for_review", "wish_granted", "wish_partial")
    if case.workflow_state not in allowed_states:
        raise HTTPException(status_code=400, detail=f"Cannot send to departments from state: {case.workflow_state}")
    tasks = await send_to_departments(db, case, staff, body.departments)
    return {"tasks_created": len(tasks), "departments": [t.department.value for t in tasks]}


@router.post("/cases/{case_id}/query")
async def raise_query(
    case_id: str,
    body: QueryRequest,
    staff: StaffUser = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    case = await _fetch_case(db, case_id, staff.organisation_id)
    await transition_state(
        db, case, "query_raised", staff.email,
        details={"message": body.message},
        notify_staff_id=case.created_by_staff_id,
        notify_message=f"Query raised on {case.reference_code}: {body.message}",
    )
    return {"status": "query_raised", "case_reference": case.reference_code}


@router.get("/cases/{case_id}/departments")
async def get_department_progress(
    case_id: str,
    staff: StaffUser = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    case = await _fetch_case(db, case_id, staff.organisation_id)
    tasks_result = await db.execute(
        select(DepartmentTask).where(DepartmentTask.verification_request_id == case.id)
    )
    tasks = tasks_result.scalars().all()
    
    docs_result = await db.execute(
        select(Document).where(Document.verification_request_id == case.id)
    )
    docs = docs_result.scalars().all()

    from app.core.eligibility import DeterministicEligibilityEngine
    elig_result = DeterministicEligibilityEngine.evaluate(
        customer_masked_data={"name": case.customer_name},
        documents=[{"doc_type": d.doc_type.value, "masked_fields": d.masked_fields} for d in docs],
        loan_amount=case.requested_amount or 500000
    )

    return {
        "case_reference": case.reference_code,
        "workflow_state": case.workflow_state,
        "department_tasks": [
            {"id": t.id, "department": t.department.value, "status": t.status, "summary": t.cited_summary}
            for t in tasks
        ],
        "eligibility_result": elig_result,
    }


@router.post("/cases/{case_id}/departments/{task_id}/decide")
async def department_decision(
    case_id: str,
    task_id: str,
    body: DepartmentDecisionRequest,
    staff: StaffUser = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    from app.services.department_workflow import DepartmentWorkflowService
    case = await _fetch_case(db, case_id, staff.organisation_id)
    result = await db.execute(select(DepartmentTask).where(DepartmentTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # Department RBAC check
    DepartmentWorkflowService.check_department_access(staff, task.department)
    
    task.status = body.new_status
    await db.commit()
    return {"task_id": task_id, "new_status": body.new_status}


@router.get("/notifications")
async def get_notifications(
    staff: StaffUser = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
    unread_only: bool = False,
):
    q = select(Notification).where(Notification.recipient_staff_id == staff.id).order_by(desc(Notification.created_at))
    if unread_only:
        q = q.where(Notification.is_read == False)
    result = await db.execute(q)
    notifs = result.scalars().all()
    return [
        {"id": n.id, "case_ref": n.case_reference, "event": n.event_type,
         "message": n.message, "is_read": n.is_read, "created_at": n.created_at.isoformat()}
        for n in notifs
    ]


@router.post("/notifications/{notif_id}/read")
async def mark_read(
    notif_id: str,
    staff: StaffUser = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Notification).where(Notification.id == notif_id, Notification.recipient_staff_id == staff.id))
    n = result.scalar_one_or_none()
    if n:
        n.is_read = True
        await db.commit()
    return {"ok": True}


@router.get("/notifications/stream")
async def sse_stream(
    staff: StaffUser = Depends(get_current_staff),
):
    """Server-Sent Events stream for real-time notifications."""
    async def event_generator():
        q = await subscribe(staff.id)
        try:
            yield "data: {\"event\":\"connected\"}\n\n"
            while True:
                try:
                    data = await asyncio.wait_for(q.get(), timeout=25.0)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            unsubscribe(staff.id, q)
    return StreamingResponse(event_generator(), media_type="text/event-stream",
                              headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── Helpers ───────────────────────────────────────────────────────────────────
def _case_summary(c: VerificationRequest) -> dict:
    return {
        "id": c.id,
        "reference_code": c.reference_code,
        "customer_name": c.customer_name,
        "loan_type": c.loan_type,
        "status": c.status.value,
        "workflow_state": c.workflow_state or "link_created",
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "link_expires_at": c.link_expires_at.isoformat() if c.link_expires_at else None,
    }


async def _fetch_case(db: AsyncSession, case_id: str, org_id: str) -> VerificationRequest:
    result = await db.execute(
        select(VerificationRequest).where(
            VerificationRequest.id == case_id,
            VerificationRequest.organisation_id == org_id,
        )
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


def _compute_readiness(docs, required_docs) -> int:
    if not required_docs:
        return 100
    doc_types = {d.doc_type.value for d in docs if d.status.value in ("VERIFIED", "PENDING")}
    matches = sum(1 for req in required_docs if req in doc_types)
    return min(100, int((matches / len(required_docs)) * 100))
