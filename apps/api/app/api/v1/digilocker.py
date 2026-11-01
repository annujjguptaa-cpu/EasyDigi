from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import ConsentLog
from app.providers.factory import get_digilocker_provider
from app.core.logging import logger

router = APIRouter()


class StartOAuthResponse(BaseModel):
    authorization_url: str
    state: str
    expires_in: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    demo_notice: str


class MockConsentDecisionRequest(BaseModel):
    state: str
    action: str  # "GRANT" or "DENY"
    customer_id: str = "customer_clean"
    demo_aadhaar_input: Optional[str] = None  # Mock dummy number (never stored)
    demo_otp_input: Optional[str] = None      # Mock dummy OTP 123456 (never stored)


@router.get("/auth/digilocker/start", response_model=StartOAuthResponse)
async def digilocker_start(
    session_id: str = Query(..., description="Customer session ID"),
    scopes: str = Query("KYC,INCOME", description="Comma separated scopes")
):
    """
    Start OAuth 2.0 PKCE flow.
    Generates state & PKCE challenge, binding to session with 10-minute TTL.
    """
    scope_list = [s.strip() for s in scopes.split(",")]
    provider = get_digilocker_provider()
    res = await provider.create_authorization_url(session_id=session_id, scopes=scope_list)
    return res


@router.get("/auth/digilocker/callback", response_model=TokenResponse)
async def digilocker_callback(
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="OAuth state parameter")
):
    """
    Callback endpoint that validates state and exchanges code for token.
    Token is returned and never logged in plain text.
    """
    provider = get_digilocker_provider()
    try:
        token_data = await provider.exchange_code_for_token(code=code, state=state)
        return token_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/digilocker/mock-consent")
async def mock_consent_action(
    payload: MockConsentDecisionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Simulates user action on the DEMO ONLY DigiLocker page.
    HARD RULE 1 & 3: Accepts ANY dummy 12-digit number and OTP 123456 purely for demo.
    NEVER PERSISTS full Aadhaar or OTP.
    Logs consent_logs record for grant or deny.
    """
    provider = get_digilocker_provider()
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "Unknown")

    if payload.action == "DENY":
        # Record DENY in consent log
        consent_log = ConsentLog(
            session_id=payload.state,
            action="DENY",
            scopes=["KYC_VERIFICATION", "INCOME_ANALYSIS"],
            ip_address=client_ip,
            user_agent=user_agent
        )
        db.add(consent_log)
        await db.commit()
        return {
            "status": "DENIED",
            "message": "User denied consent. No access token issued.",
            "demo_notice": "DEMO ONLY, not the real DigiLocker"
        }

    # If GRANT, generate mock code
    try:
        from app.providers.digilocker import MockDigiLockerProvider
        if isinstance(provider, MockDigiLockerProvider):
            code = await provider.create_mock_grant(
                state=payload.state,
                customer_id=payload.customer_id
            )
        else:
            code = "real_aggregator_code"

        # Record GRANT in consent log
        consent_log = ConsentLog(
            session_id=payload.state,
            action="GRANT",
            scopes=["KYC_VERIFICATION", "INCOME_ANALYSIS"],
            ip_address=client_ip,
            user_agent=user_agent
        )
        db.add(consent_log)
        await db.commit()

        # Notice: payload.demo_aadhaar_input and demo_otp_input are discarded completely
        return {
            "status": "GRANTED",
            "code": code,
            "state": payload.state,
            "demo_notice": "DEMO ONLY, not the real DigiLocker"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/digilocker/documents")
async def list_issued_documents(
    token: str = Query(..., description="Access token"),
    failure_mode: Optional[str] = Query(None, description="Simulate failure mode: missing_document | expired_token | name_mismatch")
):
    """
    List issued documents for the authenticated session.
    """
    provider = get_digilocker_provider()
    try:
        docs = await provider.get_issued_documents(token=token, failure_mode=failure_mode)
        return {"documents": docs, "demo_notice": "DEMO ONLY, not the real DigiLocker"}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
