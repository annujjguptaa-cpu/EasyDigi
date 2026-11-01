from app.core.config import settings
from app.providers.base import DigiLockerProvider, LLMProvider, OCRProvider, StorageProvider
from app.providers.digilocker import MockDigiLockerProvider, AggregatorProvider
from app.providers.llm import MockLLMProvider, GeminiLLMProvider
from app.providers.ocr import MockOCRProvider
from app.providers.storage import MockStorageProvider


def get_digilocker_provider() -> DigiLockerProvider:
    if settings.DIGILOCKER_PROVIDER == "real":
        return AggregatorProvider(
            client_id=settings.DIGILOCKER_CLIENT_ID,
            client_secret=settings.DIGILOCKER_CLIENT_SECRET
        )
    return MockDigiLockerProvider()


def get_llm_provider() -> LLMProvider:
    if settings.LLM_PROVIDER == "gemini":
        return GeminiLLMProvider()
    return MockLLMProvider()


def get_ocr_provider() -> OCRProvider:
    return MockOCRProvider()


def get_storage_provider() -> StorageProvider:
    return MockStorageProvider()
