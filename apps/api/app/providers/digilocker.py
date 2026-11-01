import hashlib
import os
import secrets
import time
from typing import Dict, Any, List, Optional
from app.providers.base import DigiLockerProvider
from app.core.logging import logger

# In-memory session state store simulating Redis for local testing / dev
# Key: state -> Value: dict(code_verifier, session_id, expires_at, created_at)
_MOCK_OAUTH_STORE: Dict[str, Dict[str, Any]] = {}

# Mock code tokens: code -> dict(token, session_id, customer_id, used)
_MOCK_CODE_STORE: Dict[str, Dict[str, Any]] = {}

# Mock tokens: token -> dict(session_id, customer_id, expires_at)
_MOCK_TOKEN_STORE: Dict[str, Dict[str, Any]] = {}


class MockDigiLockerProvider(DigiLockerProvider):
    """
    Mock implementation that mimics the official OAuth 2.0 PKCE flow.
    MARKED: DEMO ONLY, NOT THE REAL DIGILOCKER.
    Adheres strictly to Hard Rules: Never logs tokens, accepts dummy numbers,
    retains at most last 4 digits.
    """
    DEMO_LABEL = "DEMO ONLY, not the real DigiLocker"

    async def create_authorization_url(self, session_id: str, scopes: List[str]) -> Dict[str, str]:
        # Generate PKCE verifier and challenge
        code_verifier = secrets.token_urlsafe(32)
        code_challenge = hashlib.sha256(code_verifier.encode('utf-8')).hexdigest()
        state = secrets.token_urlsafe(16)
        
        # 10 minute TTL
        expires_at = time.time() + 600

        _MOCK_OAUTH_STORE[state] = {
            "session_id": session_id,
            "code_verifier": code_verifier,
            "scopes": scopes,
            "expires_at": expires_at
        }

        # Redirect to the mock consent page
        mock_consent_url = (
            f"/mock-digilocker?response_type=code"
            f"&state={state}"
            f"&code_challenge={code_challenge}"
            f"&scope={','.join(scopes)}"
            f"&demo_label=DEMO_ONLY"
        )
        return {
            "authorization_url": mock_consent_url,
            "state": state,
            "expires_in": 600
        }

    async def create_mock_grant(self, state: str, customer_id: str = "customer_clean") -> str:
        """Called when user clicks 'Allow' on the DEMO ONLY consent screen."""
        if state not in _MOCK_OAUTH_STORE:
            raise ValueError("Invalid or unknown state parameter")
        
        state_data = _MOCK_OAUTH_STORE[state]
        if time.time() > state_data["expires_at"]:
            del _MOCK_OAUTH_STORE[state]
            raise ValueError("OAuth state has expired (10-minute TTL exceeded)")

        code = f"mock_code_{secrets.token_hex(16)}"
        _MOCK_CODE_STORE[code] = {
            "state": state,
            "session_id": state_data["session_id"],
            "customer_id": customer_id,
            "used": False
        }
        return code

    async def exchange_code_for_token(self, code: str, state: str) -> Dict[str, Any]:
        """
        Validate state and exchange code for token.
        Hard Rule: Tokens must be handled securely and NEVER printed to logs.
        """
        if state not in _MOCK_OAUTH_STORE:
            raise ValueError("OAuth state mismatch or unrecognized state")

        state_data = _MOCK_OAUTH_STORE[state]
        if time.time() > state_data["expires_at"]:
            raise ValueError("OAuth state has expired")

        if code not in _MOCK_CODE_STORE:
            raise ValueError("Invalid authorization code")

        code_data = _MOCK_CODE_STORE[code]
        if code_data["used"]:
            raise ValueError("Authorization code has already been used (replayed code rejected)")

        if code_data["state"] != state:
            raise ValueError("Code does not match state")

        # Mark code as consumed
        code_data["used"] = True

        # Generate mock token
        access_token = f"mock_dl_token_{secrets.token_hex(24)}"
        _MOCK_TOKEN_STORE[access_token] = {
            "session_id": state_data["session_id"],
            "customer_id": code_data["customer_id"],
            "expires_at": time.time() + 3600
        }

        # Clean up used state
        del _MOCK_OAUTH_STORE[state]

        # Note: Logger will filter any token values automatically
        logger.info(f"DigiLocker OAuth token generated for session: {state_data['session_id']}")

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "demo_notice": self.DEMO_LABEL
        }

    async def get_issued_documents(
        self,
        token: str,
        failure_mode: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Mock document list with failure mode flags:
        'missing_document', 'expired_token', 'name_mismatch'
        """
        if token not in _MOCK_TOKEN_STORE:
            raise ValueError("Invalid or expired access token")

        token_data = _MOCK_TOKEN_STORE[token]
        if time.time() > token_data["expires_at"] or failure_mode == "expired_token":
            raise ValueError("Access token has expired")

        customer_id = token_data.get("customer_id", "customer_clean")

        if failure_mode == "missing_document" or customer_id == "customer_missing_docs":
            # Missing marksheet and salary slips
            return [
                {
                    "name": "PAN Verification Record",
                    "doc_type": "PAN",
                    "uri": "in.gov.pan/fictional-pan-003",
                    "status": "ISSUED",
                    "demo_only": True
                }
            ]

        if failure_mode == "name_mismatch" or customer_id == "customer_name_mismatch":
            return [
                {
                    "name": "PAN Verification Record",
                    "doc_type": "PAN",
                    "uri": "in.gov.pan/fictional-pan-002",
                    "status": "ISSUED",
                    "demo_only": True
                },
                {
                    "name": "Aadhaar e-KYC Offline",
                    "doc_type": "AADHAAR_OFFLINE",
                    "uri": "in.gov.uidai/fictional-aadhaar-002",
                    "status": "ISSUED",
                    "demo_only": True
                }
            ]

        # Clean profile
        return [
            {
                "name": "PAN Verification Record",
                "doc_type": "PAN",
                "uri": "in.gov.pan/fictional-pan-001",
                "status": "ISSUED",
                "demo_only": True
            },
            {
                "name": "Aadhaar e-KYC Offline",
                "doc_type": "AADHAAR_OFFLINE",
                "uri": "in.gov.uidai/fictional-aadhaar-001",
                "status": "ISSUED",
                "demo_only": True
            },
            {
                "name": "Income Tax / Salary Statement",
                "doc_type": "SALARY_SLIP",
                "uri": "in.gov.income/fictional-salary-001",
                "status": "ISSUED",
                "demo_only": True
            },
            {
                "name": "University Degree Marksheet",
                "doc_type": "MARKSHEET",
                "uri": "in.gov.edu/fictional-degree-001",
                "status": "ISSUED",
                "demo_only": True
            }
        ]

    async def fetch_document_content(self, token: str, uri: str) -> Dict[str, Any]:
        """Fetch document metadata with masked values only."""
        if token not in _MOCK_TOKEN_STORE:
            raise ValueError("Unauthorized token")

        # Fictional synthetic content
        return {
            "uri": uri,
            "demo_notice": self.DEMO_LABEL,
            "masked_fields": {
                "name": "Rahul Verma",
                "id_last4": "4321",
                "pan_masked": "ABCDE1234F",
                "dob": "1992-05-14"
            },
            "blob_ref": f"mock_vault_blob_{hashlib.md5(uri.encode()).hexdigest()}"
        }


class AggregatorProvider(DigiLockerProvider):
    """
    Contract for real DigiLocker / Account Aggregator.
    TODO: Insert official Sandbox Base URLs, Client Credentials, RSA Keystores,
    and mutual TLS (mTLS) certs when deploying production bank aggregator integration.
    """
    SANDBOX_BASE_URL = "https://digilocker.meripehchaan.gov.in/public/oauth2/1"  # TODO: Update with certified portal

    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        self.client_id = client_id
        self.client_secret = client_secret
        # TODO: Initialize mTLS certificates and JWT signer

    async def create_authorization_url(self, session_id: str, scopes: List[str]) -> Dict[str, str]:
        # TODO: Build official signed PKCE request to real aggregator gateway
        raise NotImplementedError("Real aggregator integration requires production credentials")

    async def exchange_code_for_token(self, code: str, state: str) -> Dict[str, Any]:
        # TODO: Post to official /token endpoint with client assertion
        raise NotImplementedError("Real aggregator integration requires production credentials")

    async def get_issued_documents(self, token: str) -> List[Dict[str, Any]]:
        # TODO: Query official /pull/documents with signed bearer token
        raise NotImplementedError("Real aggregator integration requires production credentials")

    async def fetch_document_content(self, token: str, uri: str) -> Dict[str, Any]:
        # TODO: Fetch official XML / PDF payload and parse through redaction pipeline
        raise NotImplementedError("Real aggregator integration requires production credentials")
