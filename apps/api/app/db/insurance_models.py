import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Text, JSON, Enum as SAEnum, Boolean, Integer, Float
)
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.db.models import generate_uuid


class PolicyStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    LAPSED = "LAPSED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class ClaimStatus(str, enum.Enum):
    INTIMATED = "INTIMATED"
    DOCS_PENDING = "DOCS_PENDING"
    IN_REVIEW = "IN_REVIEW"
    QUERY_RAISED = "QUERY_RAISED"
    COVERAGE_ASSESSED = "COVERAGE_ASSESSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SETTLED = "SETTLED"


class InsuranceDepartment(str, enum.Enum):
    CLAIMS_INTAKE = "CLAIMS_INTAKE"
    MEDICAL_TPA = "MEDICAL_TPA"
    SURVEYOR = "SURVEYOR"
    FRAUD_SIU = "FRAUD_SIU"
    PAYMENTS = "PAYMENTS"


class DeadlineStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    MET = "MET"
    AT_RISK = "AT_RISK"
    BREACHED = "BREACHED"


class CoverageStatus(str, enum.Enum):
    COVERED = "COVERED"
    PARTLY_COVERED = "PARTLY_COVERED"
    NOT_COVERED = "NOT_COVERED"


class Policy(Base):
    """Insurance Policy definition"""
    __tablename__ = "policies"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    number = Column(String(100), unique=True, nullable=False)
    holder_name = Column(String(255), nullable=False)
    holder_id = Column(String(100), nullable=False)  # fictional identifier (e.g. CUST_RAJAN)
    product_type = Column(String(50), nullable=False)  # HEALTH, MOTOR, LIFE
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    sum_insured = Column(Integer, nullable=False)
    deductible = Column(Integer, default=0)
    co_pay_pct = Column(Float, default=0.0)
    waiting_period_days = Column(Integer, default=0)
    status = Column(SAEnum(PolicyStatus), default=PolicyStatus.ACTIVE)
    nominee_name = Column(String(255), nullable=True)
    nominee_relation = Column(String(100), nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    claims = relationship("Claim", back_populates="policy")


class Claim(Base):
    """Insurance Claim instance"""
    __tablename__ = "claims"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_number = Column(String(50), unique=True, nullable=False)
    policy_id = Column(String(36), ForeignKey("policies.id"), nullable=False)
    type = Column(String(50), nullable=False)  # health_cashless, health_reimbursement, motor_own_damage, motor_theft, life_death
    status = Column(SAEnum(ClaimStatus), default=ClaimStatus.INTIMATED)
    incident_date = Column(DateTime, nullable=False)
    intimation_at = Column(DateTime, default=datetime.utcnow)
    claimant_name = Column(String(255), nullable=False)
    claimant_phone = Column(String(20), nullable=True)
    requested_amount = Column(Integer, default=0)
    approved_amount = Column(Integer, nullable=True)
    intake_token = Column(String(255), unique=True, nullable=True)
    intake_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    policy = relationship("Policy", back_populates="claims")
    documents = relationship("ClaimDocument", back_populates="claim")
    events = relationship("ClaimEvent", back_populates="claim")
    deadlines = relationship("ClaimDeadline", back_populates="claim")
    coverage_results = relationship("CoverageResult", back_populates="claim")
    fraud_flags = relationship("FraudFlag", back_populates="claim")
    tasks = relationship("ClaimTask", back_populates="claim")
    settlement = relationship("Settlement", back_populates="claim", uselist=False)


class ClaimDocument(Base):
    """
    Evidence & identity documents attached to an insurance claim.
    Sensitive details masked; raw files referenced via encrypted storage.
    """
    __tablename__ = "claim_documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id"), nullable=False)
    doc_type = Column(String(100), nullable=False)
    status = Column(String(50), default="PENDING")  # PENDING, EXTRACTED, VERIFIED, MISMATCH, MISSING
    encrypted_blob_ref = Column(String(255), nullable=True)
    masked_fields = Column(JSON, nullable=False, default=dict)
    ocr_confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    claim = relationship("Claim", back_populates="documents")


class ClaimEvent(Base):
    """Timeline event log for claim auditability"""
    __tablename__ = "claim_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id"), nullable=False)
    action = Column(String(100), nullable=False)
    actor = Column(String(100), nullable=False)  # system, policyholder, claims_officer, medical_tpa
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    claim = relationship("Claim", back_populates="events")


class ClaimDeadline(Base):
    """Service level / regulatory deadline tracking"""
    __tablename__ = "deadlines"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id"), nullable=False)
    deadline_type = Column(String(100), nullable=False)  # intimation, pre_auth, doc_submission, survey_report, settlement
    owner = Column(String(100), nullable=False)  # TPA, SURVEYOR, CLAIMS_OFFICER, POLICYHOLDER
    due_at = Column(DateTime, nullable=False)
    status = Column(SAEnum(DeadlineStatus), default=DeadlineStatus.RUNNING)
    created_at = Column(DateTime, default=datetime.utcnow)

    claim = relationship("Claim", back_populates="deadlines")


class CoverageResult(Base):
    """Deterministic coverage computation results (code output, not LLM)"""
    __tablename__ = "coverage_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id"), nullable=False)
    status = Column(SAEnum(CoverageStatus), nullable=False)
    breakdown = Column(JSON, nullable=False, default=dict)  # sum_insured, co_pay_deductions, non_payable_items, final_payable
    reason_codes = Column(JSON, nullable=False, default=list)  # ["POLICY_ACTIVE", "WAITING_PERIOD_MET", ...]
    assessed_at = Column(DateTime, default=datetime.utcnow)

    claim = relationship("Claim", back_populates="coverage_results")


class FraudFlag(Base):
    """Signals flagged for human review (never automatic rejection)"""
    __tablename__ = "fraud_flags"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id"), nullable=False)
    flag_type = Column(String(100), nullable=False)  # BILL_DISCHARGE_MISMATCH, DATE_OUTSIDE_POLICY, NOMINEE_NAME_MISMATCH
    severity = Column(String(20), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    evidence = Column(JSON, nullable=False, default=dict)
    resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    claim = relationship("Claim", back_populates="fraud_flags")


class ClaimTask(Base):
    """Department tasks with department-sliced views and cited summaries"""
    __tablename__ = "claim_tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id"), nullable=False)
    department = Column(SAEnum(InsuranceDepartment), nullable=False)
    assigned_to_id = Column(String(36), nullable=True)
    status = Column(String(50), default="PENDING")  # PENDING, IN_PROGRESS, COMPLETED, QUERIED
    cited_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    claim = relationship("Claim", back_populates="tasks")


class Settlement(Base):
    """Settlement details & payouts"""
    __tablename__ = "settlements"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id"), nullable=False, unique=True)
    amount = Column(Integer, nullable=False)
    utr_number = Column(String(100), nullable=True)
    bank_account_last4 = Column(String(4), nullable=True)
    payment_mode = Column(String(50), default="NEFT")
    status = Column(String(50), default="INITIATED")  # INITIATED, PROCESSED, FAILED
    settled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    claim = relationship("Claim", back_populates="settlement")
