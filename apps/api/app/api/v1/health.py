from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "urls": {
            "bank_url": settings.BANK_URL,
            "customer_url": settings.CUSTOMER_URL,
            "digilocker_url": settings.DIGILOCKER_URL,
            "api_url": settings.API_URL,
        },
        "providers": {
            "digilocker": settings.DIGILOCKER_PROVIDER,
            "llm": settings.LLM_PROVIDER,
            "ocr": settings.OCR_PROVIDER,
            "storage": settings.STORAGE_PROVIDER
        }
    }
