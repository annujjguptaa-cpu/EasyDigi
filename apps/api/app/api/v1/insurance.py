from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.insurance_models import Claim, ClaimDocument, ClaimEvent, ClaimStatus
from app.services.claim_agent_service import ClaimIntakeAgent, generate_claim_intake_link
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
