import pytest
from fastapi import HTTPException
from app.db.models import Department, StaffRole, StaffUser
from app.services.department_workflow import DepartmentWorkflowService


def test_department_rbac_isolation():
    kyc_user = StaffUser(
        id="user_kyc_01",
        email="kyc@bank.com",
        role=StaffRole.KYC_OFFICER,
        department=Department.KYC,
        hashed_password="pw"
    )

    # KYC accessing KYC is allowed
    assert DepartmentWorkflowService.check_department_access(kyc_user, Department.KYC) is True

    # KYC accessing Credit is strictly 403 Forbidden
    with pytest.raises(HTTPException) as exc:
        DepartmentWorkflowService.check_department_access(kyc_user, Department.CREDIT)
    assert exc.value.status_code == 403


def test_maker_checker_approval_rule():
    maker_id = "staff_maker_01"
    checker_head_id = "staff_head_02"

    # Maker attempting to self-approve fails
    with pytest.raises(ValueError, match="Maker cannot approve their own task"):
        DepartmentWorkflowService.transition_task(
            task_id="task_123",
            current_status="IN_REVIEW",
            target_status="APPROVED",
            actor_id=maker_id,
            prepared_by_id=maker_id,
            actor_role=StaffRole.CREDIT_MANAGER,
            decision_notes="Self-approval attempt"
        )

    # Different checker/head approving succeeds
    res = DepartmentWorkflowService.transition_task(
        task_id="task_123",
        current_status="IN_REVIEW",
        target_status="APPROVED",
        actor_id=checker_head_id,
        prepared_by_id=maker_id,
        actor_role=StaffRole.CREDIT_MANAGER,
        decision_notes="Verified by credit manager"
    )
    assert res["new_status"] == "APPROVED"
    assert res["audit_recorded"] is True


def test_profile_summary_citation_validation():
    # Valid cited summary
    cited_summary = (
        "Applicant identity verified via Aadhaar [AADHAAR_MASKED Ref: DOC-1234] "
        "and salary verified from pay slip [SALARY_SLIP Ref: DOC-5678]."
    )
    assert DepartmentWorkflowService.validate_profile_summary_citations(cited_summary) is True

    # Uncited summary rejected
    uncited_summary = "Applicant looks good and has sufficient income for the loan."
    assert DepartmentWorkflowService.validate_profile_summary_citations(uncited_summary) is False
