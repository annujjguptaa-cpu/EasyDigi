"""
Orchestrates the case workflow state machine.
States: link_created -> link_opened -> consent_given -> documents_received ->
        ready_for_review -> sent_to_departments -> in_review -> query_raised -> decided
Every transition writes an AuditLog and emits a notification event.
"""
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import (
    VerificationRequest, StaffUser, Department, DepartmentTask,
    AuditLog, Notification, RequestStatus
)
from app.services.notification_service import emit_event
from app.core.config import settings

DEPT_DOC_MAP = {
    "KYC": ["PAN", "AADHAAR_OFFLINE", "AADHAAR_MASKED"],
    "CREDIT": ["SALARY_SLIP", "BANK_STATEMENT", "ITR", "FORM16"],
    "RISK": ["SALARY_SLIP", "BANK_STATEMENT", "PAN"],
    "LEGAL": ["TITLE_DEED", "EC", "AADHAAR_MASKED", "PAN"],
    "TECHNICAL": ["TITLE_DEED", "EC"],
    "OPERATIONS": ["SIGNATURE", "MARKSHEET", "PAN", "AADHAAR_MASKED"],
}


async def create_case(
    db: AsyncSession,
    created_by: StaffUser,
    customer_name: str,
    customer_phone_masked: str,
    loan_type: str,
    required_docs: List[str],
    ttl_hours: int = 24,
) -> VerificationRequest:
    token = secrets.token_urlsafe(24)
    expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
    ref_code = f"CASE-{uuid.uuid4().hex[:8].upper()}"

    case = VerificationRequest(
        organisation_id=created_by.organisation_id,
        reference_code=ref_code,
        customer_fictional_id=f"cust_{uuid.uuid4().hex[:8]}",
        customer_name=customer_name,
        loan_type=loan_type,
        requested_amount=500000,
        status=RequestStatus.PENDING_CONSENT,
        created_by_staff_id=created_by.id,
        link_token=token,
        link_expires_at=expires_at,
        workflow_state="link_created",
        required_documents=required_docs,
    )
    db.add(case)
    await db.flush()

    await _write_audit(db, case.id, "link_created", created_by.email, {"loan_type": loan_type})
    await emit_event(created_by.id, "link_created", {"case_ref": ref_code, "token": token})
    await db.commit()
    return case


async def transition_state(
    db: AsyncSession,
    case: VerificationRequest,
    new_state: str,
    actor: str,
    details: Optional[dict] = None,
    notify_staff_id: Optional[str] = None,
    notify_message: Optional[str] = None,
):
    case.workflow_state = new_state
    if new_state == "documents_received":
        case.status = RequestStatus.READY_FOR_REVIEW
    elif new_state == "decided":
        case.status = RequestStatus.APPROVED
    
    await _write_audit(db, case.id, new_state, actor, details or {})

    if notify_staff_id and notify_message:
        notif = Notification(
            recipient_staff_id=notify_staff_id,
            case_reference=case.reference_code,
            event_type=new_state,
            message=notify_message,
        )
        db.add(notif)
        await emit_event(notify_staff_id, new_state, {
            "case_ref": case.reference_code,
            "message": notify_message,
        })

    await db.commit()


async def send_to_departments(
    db: AsyncSession,
    case: VerificationRequest,
    actor_staff: StaffUser,
    departments: List[str],
) -> List[DepartmentTask]:
    """
    Creates exactly one DepartmentTask per department with scoped document list.
    """
    tasks = []
    for dept_name in departments:
        try:
            dept_enum = Department(dept_name)
        except ValueError:
            continue
            
        allowed_docs = DEPT_DOC_MAP.get(dept_name, [])
        scoped_docs = [d for d in (case.required_documents or []) if d in allowed_docs]

        # Find assigned staff for this dept
        result = await db.execute(
            select(StaffUser).where(
                StaffUser.organisation_id == case.organisation_id,
                StaffUser.department == dept_enum,
            )
        )
        dept_staff = result.scalars().first()

        task = DepartmentTask(
            verification_request_id=case.id,
            department=dept_enum,
            assigned_to_id=dept_staff.id if dept_staff else None,
            status="PENDING",
            cited_summary=f"Case {case.reference_code} assigned. Scoped Documents: {', '.join(scoped_docs) if scoped_docs else 'Standard set'}. [AUTO_ROUTED Ref: {case.reference_code}]",
            deterministic_eligibility={"scoped_docs": scoped_docs, "status": "PENDING_REVIEW"},
        )
        db.add(task)
        tasks.append(task)

        if dept_staff:
            notif = Notification(
                recipient_staff_id=dept_staff.id,
                case_reference=case.reference_code,
                event_type="task_assigned",
                message=f"New case {case.reference_code} assigned to {dept_name}.",
            )
            db.add(notif)
            await emit_event(dept_staff.id, "task_assigned", {
                "case_ref": case.reference_code, "dept": dept_name
            })

    case.workflow_state = "sent_to_departments"
    await _write_audit(db, case.id, "sent_to_departments", actor_staff.email, {"departments": departments})
    await db.commit()
    return tasks


async def _write_audit(db: AsyncSession, case_id: str, action: str, actor: str, details: dict):
    log = AuditLog(
        entity_type="case",
        entity_id=case_id,
        action=action,
        actor_id=actor,
        details=details,
        ip_address="0.0.0.0",
    )
    db.add(log)
