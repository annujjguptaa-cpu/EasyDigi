from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "providers": {
            "digilocker": settings.DIGILOCKER_PROVIDER,
            "llm": settings.LLM_PROVIDER,
            "ocr": settings.OCR_PROVIDER,
            "storage": settings.STORAGE_PROVIDER
        }
    }
