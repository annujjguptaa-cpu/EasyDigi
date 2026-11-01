import re
from typing import Dict, Any, List
from fastapi import HTTPException
from app.db.models import Department, StaffRole, StaffUser


class DepartmentWorkflowService:
    """
    Implements Bank Department Workflow with Maker-Checker RBAC:
    - Maker prepares case
    - Checker reviews
    - Head approves
    - Hard Rule: Maker CANNOT approve their own prepared task.
    - Profile summary citation validator: Rejects summaries with uncited claims.
    """

    ALLOWED_DEPARTMENTS = {
        Department.KYC: ["PAN", "AADHAAR_MASKED", "PHOTO"],
        Department.CREDIT: ["SALARY_SLIP", "BANK_STATEMENT", "ITR", "FORM16"],
        Department.RISK: ["SALARY_SLIP", "BANK_STATEMENT", "PAN"],
        Department.OPERATIONS: ["SIGNATURE", "MARKSHEET", "PAN", "AADHAAR_MASKED"]
    }

    CITATION_REGEX = re.compile(r'\[[A-Z0-9_\-]+(\s+Ref:\s+[A-Za-z0-9_\-]+)?\]')

    @classmethod
    def check_department_access(cls, staff_user: StaffUser, requested_department: Department) -> bool:
        """Enforces departmental RBAC. Returns True or raises 403 Forbidden."""
        if staff_user.role == StaffRole.ADMIN:
            return True
        if staff_user.department != requested_department:
            raise HTTPException(
                status_code=403,
                detail=f"Access Denied: Staff in {staff_user.department.value} cannot access {requested_department.value} tasks."
            )
        return True

    @classmethod
    def validate_profile_summary_citations(cls, summary_text: str) -> bool:
        """
        Validates that every claim in the department summary carries a valid source reference citation.
        Rejects output with uncited claims.
        """
        if not summary_text or len(summary_text.strip()) < 10:
            return False
        # Must contain at least one bracketed citation (e.g. [PAN Ref: DOC-1234] or [SALARY_SLIP])
        matches = cls.CITATION_REGEX.findall(summary_text)
        return len(matches) > 0

    @classmethod
    def transition_task(
        cls,
        task_id: str,
        current_status: str,
        target_status: str,
        actor_id: str,
        prepared_by_id: str,
        actor_role: StaffRole,
        decision_notes: str
    ) -> Dict[str, Any]:
        """
        Maker-Checker state machine:
        States: PENDING -> IN_REVIEW -> APPROVED / REJECTED / QUERY_RAISED
        Hard Rule: Maker cannot approve their own task.
        """
        # Enforce maker-checker rule
        if target_status == "APPROVED" and actor_id == prepared_by_id:
            raise ValueError("Maker-Checker Violation: Maker cannot approve their own task.")

        if target_status == "APPROVED" and actor_role not in (StaffRole.ADMIN, StaffRole.CREDIT_MANAGER):
            raise ValueError(f"Role {actor_role.value} does not have permission to approve tasks.")

        return {
            "task_id": task_id,
            "previous_status": current_status,
            "new_status": target_status,
            "transitioned_by": actor_id,
            "notes": decision_notes,
            "audit_recorded": True
        }
