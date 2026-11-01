from fastapi import APIRouter
from app.api.v1 import health, digilocker, consent, wishes, bank, customer, mock_digilocker_api, insurance

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(digilocker.router, tags=["DigiLocker"])
api_router.include_router(consent.router, tags=["Consent & Bank Slices"])
api_router.include_router(wishes.router, tags=["Djinn Wish Pack"])
api_router.include_router(bank.router)
api_router.include_router(customer.router)
api_router.include_router(mock_digilocker_api.router)
api_router.include_router(insurance.router)
