import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Text, JSON, Enum as SAEnum, Boolean, Integer
)
from sqlalchemy.orm import relationship
from app.db.session import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class StaffRole(str, enum.Enum):
    ADMIN = "ADMIN"
    KYC_OFFICER = "KYC_OFFICER"
    RISK_ANALYST = "RISK_ANALYST"
    CREDIT_MANAGER = "CREDIT_MANAGER"
    OPERATIONS = "OPERATIONS"


class Department(str, enum.Enum):
    KYC = "KYC"
    RISK = "RISK"
    CREDIT = "CREDIT"
    OPERATIONS = "OPERATIONS"


class RequestStatus(str, enum.Enum):
    PENDING_CONSENT = "PENDING_CONSENT"
    CONSENT_GRANTED = "CONSENT_GRANTED"
    GAPS_DETECTED = "GAPS_DETECTED"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class DocumentType(str, enum.Enum):
    PAN = "PAN"
    AADHAAR_OFFLINE = "AADHAAR_OFFLINE"
    SALARY_SLIP = "SALARY_SLIP"
    MARKSHEET = "MARKSHEET"
    BANK_STATEMENT = "BANK_STATEMENT"


class DocumentStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    MISMATCH = "MISMATCH"
    MISSING = "MISSING"
    REJECTED = "REJECTED"


class ApprovalStatus(str, enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ADDITIONAL_INFO_REQUIRED = "ADDITIONAL_INFO_REQUIRED"


class Organisation(Base):
    """Lending organisations (Banks / NBFCs)"""
    __tablename__ = "organisations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    staff_users = relationship("StaffUser", back_populates="organisation")
    verification_requests = relationship("VerificationRequest", back_populates="organisation")


class StaffUser(Base):
    """Bank employees scoped to department & roles"""
    __tablename__ = "staff_users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organisation_id = Column(String(36), ForeignKey("organisations.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(StaffRole), nullable=False, default=StaffRole.KYC_OFFICER)
    department = Column(SAEnum(Department), nullable=False, default=Department.KYC)
    created_at = Column(DateTime, default=datetime.utcnow)

    organisation = relationship("Organisation", back_populates="staff_users")
    department_tasks = relationship("DepartmentTask", back_populates="assigned_to")


class VerificationRequest(Base):
    """Verification flow instance initiated for a prospective borrower"""
    __tablename__ = "verification_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organisation_id = Column(String(36), ForeignKey("organisations.id"), nullable=False)
    reference_code = Column(String(50), unique=True, nullable=False)
    customer_fictional_id = Column(String(100), nullable=False)
    customer_name = Column(String(255), nullable=False)
    loan_type = Column(String(50), default="PERSONAL_LOAN")
    requested_amount = Column(Integer, default=500000)
    status = Column(SAEnum(RequestStatus), default=RequestStatus.PENDING_CONSENT)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organisation = relationship("Organisation", back_populates="verification_requests")
    sessions = relationship("CustomerSession", back_populates="verification_request")
    documents = relationship("Document", back_populates="verification_request")
    share_packages = relationship("SharePackage", back_populates="verification_request")
    tasks = relationship("DepartmentTask", back_populates="verification_request")
    approvals = relationship("Approval", back_populates="verification_request")


class CustomerSession(Base):
    """Temporary customer session created via consent link"""
    __tablename__ = "customer_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    verification_request_id = Column(String(36), ForeignKey("verification_requests.id"), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False)
    status = Column(String(50), default="INITIATED")
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    verification_request = relationship("VerificationRequest", back_populates="sessions")
    consent_logs = relationship("ConsentLog", back_populates="session")


class ConsentLog(Base):
    """Immutable audit trail of what scopes customer granted, denied, or revoked"""
    __tablename__ = "consent_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("customer_sessions.id"), nullable=False)
    action = Column(String(20), nullable=False)  # GRANT, DENY, REVOKE
    scopes = Column(JSON, nullable=False)       # ["KYC_VERIFICATION", "INCOME_ANALYSIS", ...]
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("CustomerSession", back_populates="consent_logs")


class Document(Base):
    """
    Document records.
    CRITICAL: Never stores raw sensitive numbers/files.
    'encrypted_blob_ref' points to client-encrypted device blob or local mock storage.
    'masked_fields' holds only safe, masked metadata (e.g. last 4 digits only).
    """
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    verification_request_id = Column(String(36), ForeignKey("verification_requests.id"), nullable=False)
    doc_type = Column(SAEnum(DocumentType), nullable=False)
    status = Column(SAEnum(DocumentStatus), default=DocumentStatus.PENDING)
    encrypted_blob_ref = Column(String(255), nullable=True)
    # masked_fields: strictly holds safe data like {"name": "...", "id_last4": "1234"}
    masked_fields = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    verification_request = relationship("VerificationRequest", back_populates="documents")


class SharePackage(Base):
    """Consent-scoped package created for bank consumption"""
    __tablename__ = "share_packages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    verification_request_id = Column(String(36), ForeignKey("verification_requests.id"), nullable=False)
    consented_scopes = Column(JSON, nullable=False)
    package_metadata = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    verification_request = relationship("VerificationRequest", back_populates="share_packages")


class DepartmentTask(Base):
    """Tasks generated for distinct departments (KYC, Risk, Credit, Ops)"""
    __tablename__ = "department_tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    verification_request_id = Column(String(36), ForeignKey("verification_requests.id"), nullable=False)
    department = Column(SAEnum(Department), nullable=False)
    assigned_to_id = Column(String(36), ForeignKey("staff_users.id"), nullable=True)
    status = Column(String(50), default="PENDING")
    # cited_summary: masked explanation with explicit document citations
    cited_summary = Column(Text, nullable=True)
    # deterministic_eligibility: pure code outcome
    deterministic_eligibility = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    verification_request = relationship("VerificationRequest", back_populates="tasks")
    assigned_to = relationship("StaffUser", back_populates="department_tasks")


class Approval(Base):
    """Bank department approval record"""
    __tablename__ = "approvals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    verification_request_id = Column(String(36), ForeignKey("verification_requests.id"), nullable=False)
    department = Column(SAEnum(Department), nullable=False)
    status = Column(SAEnum(ApprovalStatus), nullable=False)
    decision_notes = Column(Text, nullable=True)
    decided_by = Column(String(100), nullable=False)
    decided_at = Column(DateTime, default=datetime.utcnow)

    verification_request = relationship("VerificationRequest", back_populates="approvals")


class AuditLog(Base):
    """Immutable audit trail for all critical operations"""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=False)
    action = Column(String(50), nullable=False)
    actor_id = Column(String(100), nullable=False)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
