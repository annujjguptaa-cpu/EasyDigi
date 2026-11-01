"""
Mock DigiLocker API endpoints for App 3.
Provides:
- User profile documents
- Live Activity Feed
- Active Consents with Revocation trigger
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from app.services import mock_digilocker_service
from app.services.notification_service import broadcast_event

router = APIRouter(prefix="/mock-digilocker", tags=["Mock DigiLocker Portal"])

class RevokeConsentRequest(BaseModel):
    token: str

@router.get("/activities")
async def get_activities():
    return mock_digilocker_service.list_activities()

@router.get("/consents")
async def get_consents():
    return mock_digilocker_service.list_consents()

@router.post("/revoke")
async def revoke_consent_endpoint(payload: RevokeConsentRequest):
    ok = mock_digilocker_service.revoke_consent(payload.token)
    if not ok:
        raise HTTPException(status_code=404, detail="Consent record not found")
    
    # Broadcast event to bank staff
    await broadcast_event("consent_revoked", {
        "token": payload.token,
        "message": "Customer revoked DigiLocker access consent."
    })
    return {"status": "REVOKED", "token": payload.token, "retention_countdown_hours": 24}

# Profiles for Home issued documents
PROFILES = {
    "clean_file": {
        "name": "Rahul Verma",
        "mobile_masked": "XXXXXX9921",
        "aadhaar_last4": "4001",
        "documents": [
            {"id": "doc_pan_1", "type": "PAN", "title": "PAN Verification Record", "issuer": "Income Tax Department", "date": "2021-04-12"},
            {"id": "doc_adh_1", "type": "AADHAAR_OFFLINE", "title": "Aadhaar e-KYC Offline", "issuer": "UIDAI", "date": "2022-01-15"},
            {"id": "doc_sal_1", "type": "SALARY_SLIP", "title": "Salary Certificate (3M)", "issuer": "TechCorp Pvt Ltd", "date": "2024-03-31"},
            {"id": "doc_bnk_1", "type": "BANK_STATEMENT", "title": "Account Statement (6M)", "issuer": "HDFC Bank", "date": "2024-04-01"},
            {"id": "doc_mrk_1", "type": "MARKSHEET", "title": "Degree Marksheet", "issuer": "University of Delhi", "date": "2018-06-20"},
        ]
    },
    "name_mismatch": {
        "name": "Priya S. Sharma",
        "mobile_masked": "XXXXXX9922",
        "aadhaar_last4": "5002",
        "documents": [
            {"id": "doc_pan_2", "type": "PAN", "title": "PAN Card (Priya Sharma)", "issuer": "Income Tax Department", "date": "2020-08-10"},
            {"id": "doc_adh_2", "type": "AADHAAR_OFFLINE", "title": "Aadhaar (Priya Sunita Sharma)", "issuer": "UIDAI", "date": "2021-11-04"},
            {"id": "doc_sal_2", "type": "SALARY_SLIP", "title": "Salary Statement", "issuer": "EduWorks", "date": "2024-03-25"},
        ]
    },
    "missing_docs": {
        "name": "Amit Patel",
        "mobile_masked": "XXXXXX9923",
        "aadhaar_last4": "6003",
        "documents": [
            {"id": "doc_pan_3", "type": "PAN", "title": "PAN Verification Record", "issuer": "Income Tax Department", "date": "2019-02-14"},
        ]
    }
}

@router.get("/profile/{profile_key}")
async def get_profile_docs(profile_key: str):
    if profile_key not in PROFILES:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile = PROFILES[profile_key]
    
    # Check if active consent exists to show badge
    consents = mock_digilocker_service.list_consents()
    active_consent = next((c for c in consents if c.status == "GRANTED"), None)
    
    docs = []
    for d in profile["documents"]:
        docs.append({
            **d,
            "shared_with": active_consent.requester if active_consent else None
        })
        
    return {
        "profile_key": profile_key,
        "name": profile["name"],
        "mobile_masked": profile["mobile_masked"],
        "aadhaar_last4": profile["aadhaar_last4"],
        "documents": docs
    }
