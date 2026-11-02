from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.insurance_models import Claim, ClaimDocument, ClaimEvent, ClaimStatus, ClaimTask, FraudFlag
from app.services.claim_agent_service import ClaimIntakeAgent, generate_claim_intake_link
from app.services.claim_vault import (
    claim_vault_service, SyncBlob, VaultRef, ChecklistItem, PolicyWalletEntry, SyncResult,
)
from app.services.claim_share_service import claim_share_service
from app.services.deadline_engine import deadline_engine
from app.services.consistency_checker import consistency_checker
from app.services.coverage_engine import coverage_engine
from app.services.settlement_service import settlement_service
from app.core.claim_types import load_claim_types_config
from app.core.config import settings

router = APIRouter(prefix="/insurance", tags=["Insurance Claims"])
agent = ClaimIntakeAgent()


class ClaimLinkCreateBody(BaseModel):
    claim_number: str


class ClaimChatBody(BaseModel):
    token: str
    message: str
    policy_number: Optional[str] = None
    claimant_name: Optional[str] = None


class ClaimStatusQuery(BaseModel):
    token: str


@router.post("/claims/generate-link")
async def create_claim_link(body: ClaimLinkCreateBody):
    """Generate signed single-use claim intake link (/claim/{token})"""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Claim).where(Claim.claim_number == body.claim_number)
        )
        claim = res.scalar_one_or_none()
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")

        link_data = generate_claim_intake_link(
            claim_number=body.claim_number,
            base_url=settings.CUSTOMER_URL or "http://localhost:3001"
        )
        claim.intake_token = link_data["token"]
        await session.commit()
        return link_data


@router.get("/claim/{token}/intake-details")
async def get_claim_intake_details(token: str):
    """Retrieve initial claim metadata and required documents for the mobile intake view"""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Claim).where(Claim.intake_token == token)
        )
        claim = res.scalar_one_or_none()
        if not claim:
            # Check if token exists in test or DB
            raise HTTPException(status_code=404, detail="Invalid or expired claim intake token")

        docs_res = await session.execute(
            select(ClaimDocument).where(ClaimDocument.claim_id == claim.id)
        )
        docs = docs_res.scalars().all()
        received_types = [d.doc_type for d in docs]

        status = agent.get_claim_status(claim.type, received_types)
        guidance = agent.get_required_documents(claim.type)

        return {
            "claim_number": claim.claim_number,
            "claim_type": claim.type,
            "claimant_name": claim.claimant_name,
            "incident_date": claim.incident_date.isoformat(),
            "status": status,
            "guidance": guidance
        }


@router.post("/claim/chat")
async def process_claim_chat(body: ClaimChatBody):
    """Conversational intake agent endpoint (/claim/{token})"""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Claim).where(Claim.intake_token == body.token)
        )
        claim = res.scalar_one_or_none()

        received_types: List[str] = []
        claim_type = "health_reimbursement"
        claimant_name = body.claimant_name

        if claim:
            claim_type = claim.type
            claimant_name = claimant_name or claim.claimant_name
            docs_res = await session.execute(
                select(ClaimDocument).where(ClaimDocument.claim_id == claim.id)
            )
            docs = docs_res.scalars().all()
            received_types = [d.doc_type for d in docs]

        chat_result = await agent.process_chat(
            user_message=body.message,
            claim_type=claim_type,
            received_docs=received_types,
            policy_number=body.policy_number,
            claimant_name=claimant_name
        )

        # Log timeline event if claim exists
        if claim and chat_result["action"] != "SECURITY_WARNING":
            event = ClaimEvent(
                claim_id=claim.id,
                action="CHAT_INTERACTION",
                actor=claimant_name or "claimant",
                details={"message": body.message[:100], "action": chat_result["action"]}
            )
            session.add(event)
            await session.commit()

        return chat_result


# ══════════════════════════════════════════════════════════════════
# Vault endpoints  (Prompt 5)
# ══════════════════════════════════════════════════════════════════

class VaultStoreBody(BaseModel):
    claim_id: str
    doc_type: str
    encrypted_b64: str      # AES-256-GCM ciphertext, base64-encoded
    size_bytes: int
    sha256: str
    retention_hours: int = 2160   # 90 days


class PolicyWalletStoreBody(BaseModel):
    policy_number: str
    encrypted_b64: str
    size_bytes: int
    sha256: str
    expires_at: Optional[str] = None  # ISO-8601


@router.post("/vault/store", response_model=VaultRef)
async def vault_store_doc(body: VaultStoreBody):
    """
    Store a single encrypted claim document.
    The server never decrypts the blob — only stores ciphertext + metadata.
    SHA-256 integrity is verified server-side before storing.
    """
    try:
        ref = claim_vault_service.store_claim_doc(
            claim_id       = body.claim_id,
            doc_type       = body.doc_type,
            encrypted_b64  = body.encrypted_b64,
            size_bytes     = body.size_bytes,
            sha256         = body.sha256,
            retention_hours= body.retention_hours,
        )
        return ref
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/vault/checklist/{claim_token}", response_model=List[ChecklistItem])
async def vault_get_checklist(claim_token: str):
    """
    Return originals checklist for a claim (PENDING / UPLOADED / VERIFIED per doc type).
    Uses the claim intake token to look up the claim_id and required docs.
    """
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Claim).where(Claim.intake_token == claim_token)
        )
        claim = res.scalar_one_or_none()
        if not claim:
            raise HTTPException(status_code=404, detail="Invalid or expired claim token")

    # Load required doc types from config
    config = load_claim_types_config()
    ct = config.claim_types.get(claim.type)
    required_docs = ct.required_documents if ct else []

    return claim_vault_service.get_originals_checklist(
        claim_id=str(claim.id),
        required_docs=required_docs,
    )


@router.post("/vault/sync", response_model=List[SyncResult])
async def vault_sync_offline(blobs: List[SyncBlob]):
    """
    Batch offline sync endpoint.
    Accepts locally-queued encrypted blobs (built while offline),
    stores them idempotently, returns per-blob status.
    """
    if not blobs:
        return []
    return claim_vault_service.sync_offline_blobs(blobs)


@router.get("/vault/policy-wallet", response_model=List[PolicyWalletEntry])
async def vault_get_policy_wallet():
    """Return all non-deleted policy wallet entries (masked identifiers only)."""
    return claim_vault_service.get_policy_wallet()


@router.post("/vault/policy-wallet", response_model=PolicyWalletEntry)
async def vault_store_policy(body: PolicyWalletStoreBody):
    """Store an encrypted policy card. Only the masked policy number is stored in metadata."""
    from datetime import datetime, timezone
    expires_at = None
    if body.expires_at:
        try:
            expires_at = datetime.fromisoformat(body.expires_at.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=422, detail="expires_at must be ISO-8601")
    try:
        return claim_vault_service.store_policy_wallet_entry(
            policy_number = body.policy_number,
            encrypted_b64 = body.encrypted_b64,
            size_bytes    = body.size_bytes,
            sha256        = body.sha256,
            expires_at    = expires_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/vault/policy-wallet/{policy_number}")
async def vault_delete_policy(policy_number: str):
    """Soft-delete a policy wallet entry."""
    removed = claim_vault_service.delete_policy_wallet_entry(policy_number)
    if not removed:
        raise HTTPException(status_code=404, detail="Policy not found in wallet")
    return {"deleted": True, "policy_number": policy_number}


# ══════════════════════════════════════════════════════════════════
# P6 — Share / Consent endpoints
# ══════════════════════════════════════════════════════════════════

class SharePackageBody(BaseModel):
    claim_token: str
    consented_doc_refs: List[str]
    recipient_public_key_b64: str


class PreAuthBody(BaseModel):
    claim_token: str
    hospital_ref: str
    estimated_amount: int


@router.post("/share/package")
async def share_claim_package(body: SharePackageBody):
    """Generate an encrypted claim package for insurer/TPA (consent-gated)."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Claim).where(Claim.intake_token == body.claim_token))
        claim = res.scalar_one_or_none()
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        claim_id = claim.id

    try:
        return await claim_share_service.generate_share_package(
            claim_id=claim_id,
            consented_doc_refs=body.consented_doc_refs,
            recipient_public_key_b64=body.recipient_public_key_b64,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/share/preauth")
async def request_preauth(body: PreAuthBody):
    """Request cashless pre-authorisation (health_cashless only)."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Claim).where(Claim.intake_token == body.claim_token))
        claim = res.scalar_one_or_none()
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        claim_id = claim.id

    try:
        return await claim_share_service.generate_cashless_preauth(
            claim_id=claim_id,
            hospital_ref=body.hospital_ref,
            estimated_amount=body.estimated_amount,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/share/{share_token}")
async def revoke_share(share_token: str):
    """Revoke a previously issued share token."""
    return await claim_share_service.revoke_share(share_token)


# ══════════════════════════════════════════════════════════════════
# P7 — Deadline & Timeline endpoints
# ══════════════════════════════════════════════════════════════════

class DeadlineInitBody(BaseModel):
    claim_token: str


class DeadlineMetBody(BaseModel):
    claim_token: str
    deadline_type: str


async def _claim_id_from_token(token: str) -> str:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Claim).where(Claim.intake_token == token))
        claim = res.scalar_one_or_none()
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        return claim.id


@router.post("/deadlines/init")
async def init_deadlines(body: DeadlineInitBody):
    """Initialise all SLA deadlines for a claim."""
    claim_id = await _claim_id_from_token(body.claim_token)
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Claim).where(Claim.id == claim_id))
        claim = res.scalar_one_or_none()
    return await deadline_engine.initialise_deadlines(
        claim_id=claim_id,
        claim_type=claim.type,
        intimation_at=claim.intimation_at,
    )


@router.get("/deadlines/{claim_token}")
async def get_deadlines(claim_token: str):
    """Return deadline status for all deadlines of a claim."""
    claim_id = await _claim_id_from_token(claim_token)
    return await deadline_engine.check_deadline_status(claim_id)


@router.get("/timeline/{claim_token}")
async def get_timeline(claim_token: str):
    """Unified timeline: events + deadlines merged chronologically."""
    claim_id = await _claim_id_from_token(claim_token)
    return await deadline_engine.get_timeline(claim_id)


# ══════════════════════════════════════════════════════════════════
# P8 — Consistency checks & insurer ingestion endpoints
# ══════════════════════════════════════════════════════════════════

class ChecksRunBody(BaseModel):
    claim_token: str


class IngestResponseBody(BaseModel):
    claim_token: str
    approved: bool
    approved_amount: Optional[int] = None
    query_items: Optional[List[str]] = None
    notes: Optional[str] = None


@router.post("/checks/run")
async def run_checks(body: ChecksRunBody):
    """Run all consistency checks; return flags + single consolidated query."""
    claim_id = await _claim_id_from_token(body.claim_token)
    return await consistency_checker.run_all_checks(claim_id)


@router.get("/checks/flags/{claim_token}")
async def get_flags(claim_token: str):
    """Return all fraud flags for a claim."""
    claim_id = await _claim_id_from_token(claim_token)
    return await consistency_checker.get_fraud_flags(claim_id)


@router.post("/checks/ingest-response")
async def ingest_response(body: IngestResponseBody):
    """Process insurer/TPA response. Never auto-rejects — human review required."""
    claim_id = await _claim_id_from_token(body.claim_token)
    try:
        return await consistency_checker.ingest_insurer_response(
            claim_id=claim_id,
            approved=body.approved,
            approved_amount=body.approved_amount,
            query_items=body.query_items,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# ══════════════════════════════════════════════════════════════════
# P9 — Coverage engine & department routing endpoints
# ══════════════════════════════════════════════════════════════════

class CoverageComputeBody(BaseModel):
    claim_token: str


class ApproveBody(BaseModel):
    claim_token: str
    officer_id: str
    approved_amount: int
    notes: str = ""


class RejectBody(BaseModel):
    claim_token: str
    officer_id: str
    reason_code: str
    notes: str = ""


@router.post("/coverage/compute")
async def compute_coverage(body: CoverageComputeBody):
    """Deterministic coverage computation — code decides, not LLM."""
    claim_id = await _claim_id_from_token(body.claim_token)
    try:
        return await coverage_engine.compute_coverage(claim_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/coverage/route-departments")
async def route_departments(body: CoverageComputeBody):
    """Create department tasks for all applicable departments."""
    claim_id = await _claim_id_from_token(body.claim_token)
    return await coverage_engine.route_to_departments(claim_id)


@router.get("/coverage/tasks/{claim_token}")
async def get_tasks(claim_token: str):
    """List all ClaimTasks for a claim."""
    claim_id = await _claim_id_from_token(claim_token)
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(ClaimTask).where(ClaimTask.claim_id == claim_id))
        tasks = res.scalars().all()
    return [
        {"department": t.department.value, "status": t.status, "cited_summary": t.cited_summary}
        for t in tasks
    ]


@router.post("/coverage/approve")
async def approve_claim(body: ApproveBody):
    """Human decision: approve claim. Logs decision with officer_id."""
    claim_id = await _claim_id_from_token(body.claim_token)
    try:
        return await coverage_engine.approve_claim(claim_id, body.officer_id, body.approved_amount, body.notes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/coverage/reject")
async def reject_claim(body: RejectBody):
    """Human decision: reject claim. Logs decision with officer_id."""
    claim_id = await _claim_id_from_token(body.claim_token)
    try:
        return await coverage_engine.reject_claim(claim_id, body.officer_id, body.reason_code, body.notes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# ══════════════════════════════════════════════════════════════════
# P10 — Settlement endpoints
# ══════════════════════════════════════════════════════════════════

class SettlementInitBody(BaseModel):
    claim_token: str
    bank_account_last4: str
    payment_mode: str = "NEFT"


class EscalateBody(BaseModel):
    claim_token: str
    grievance_text: str


@router.post("/settlement/initiate")
async def initiate_settlement(body: SettlementInitBody):
    """Initiate settlement for an APPROVED claim. Stores last-4 only."""
    claim_id = await _claim_id_from_token(body.claim_token)
    try:
        return await settlement_service.initiate_settlement(
            claim_id=claim_id,
            bank_account_last4=body.bank_account_last4,
            payment_mode=body.payment_mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/settlement/status/{claim_token}")
async def get_settlement_status(claim_token: str):
    """Return current settlement status."""
    claim_id = await _claim_id_from_token(claim_token)
    result = await settlement_service.get_settlement_status(claim_id)
    if not result:
        raise HTTPException(status_code=404, detail="No settlement found for this claim")
    return result


@router.post("/settlement/escalate")
async def escalate_ombudsman(body: EscalateBody):
    """Escalate to Insurance Ombudsman (REJECTED/QUERY_RAISED claims only)."""
    claim_id = await _claim_id_from_token(body.claim_token)
    try:
        return await settlement_service.escalate_to_ombudsman(claim_id, body.grievance_text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
