"""
Mock DigiLocker Activity and Consent state management.
Provides live updates for App 3 (Mock DigiLocker) when wishes are granted or revoked.
"""
import time
from typing import Dict, List, Any
from pydantic import BaseModel

class DigiLockerActivity(BaseModel):
    id: str
    requester: str
    purpose: str
    documents: List[str]
    timestamp: float
    expiry: str
    status: str  # ACTIVE | REVOKED

class DigiLockerConsent(BaseModel):
    id: str
    token: str
    requester: str
    scopes: List[str]
    granted_at: float
    status: str  # GRANTED | REVOKED

# In-memory stores for DigiLocker activity & active consents
_DIGILOCKER_ACTIVITIES: List[DigiLockerActivity] = []
_DIGILOCKER_CONSENTS: Dict[str, DigiLockerConsent] = {}

def record_activity(requester: str, purpose: str, documents: List[str], expiry: str = "24 Hours") -> DigiLockerActivity:
    act = DigiLockerActivity(
        id=f"act_{int(time.time()*1000)}",
        requester=requester,
        purpose=purpose,
        documents=documents,
        timestamp=time.time(),
        expiry=expiry,
        status="ACTIVE"
    )
    _DIGILOCKER_ACTIVITIES.insert(0, act)
    return act

def list_activities() -> List[DigiLockerActivity]:
    return _DIGILOCKER_ACTIVITIES

def add_consent(token: str, requester: str, scopes: List[str]) -> DigiLockerConsent:
    c = DigiLockerConsent(
        id=f"cns_{int(time.time()*1000)}",
        token=token,
        requester=requester,
        scopes=scopes,
        granted_at=time.time(),
        status="GRANTED"
    )
    _DIGILOCKER_CONSENTS[token] = c
    return c

def list_consents() -> List[DigiLockerConsent]:
    return list(_DIGILOCKER_CONSENTS.values())

def revoke_consent(token: str) -> bool:
    if token in _DIGILOCKER_CONSENTS:
        _DIGILOCKER_CONSENTS[token].status = "REVOKED"
        # Update matching activity
        for act in _DIGILOCKER_ACTIVITIES:
            act.status = "REVOKED"
        return True
    return False

def reset_digilocker_state():
    _DIGILOCKER_ACTIVITIES.clear()
    _DIGILOCKER_CONSENTS.clear()
