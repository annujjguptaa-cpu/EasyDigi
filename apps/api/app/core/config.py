import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "DocFlow API"
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./docflow.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Provider Selection via ENV
    DIGILOCKER_PROVIDER: str = "mock"  # mock | real
    LLM_PROVIDER: str = "mock"         # mock | gemini | claude
    OCR_PROVIDER: str = "mock"         # mock | tesseract
    STORAGE_PROVIDER: str = "mock"     # mock | s3
    
    # Security & Encryption (AES key for local encrypted vault)
    VAULT_SECRET_KEY: str = "demo-super-secret-vault-key-32b!"
    
    # Service Base URLs for Inter-App Navigation
    BANK_URL: str = "http://localhost:3000"
    CUSTOMER_URL: str = "http://localhost:3001"
    DIGILOCKER_URL: str = "http://localhost:3002"
    API_URL: str = "http://localhost:8000/api/v1"

    # Frontend public URL fallback (used for customer links)
    PUBLIC_BASE_URL: str = "http://localhost:3001"

    # DigiLocker Real Integration Stubs (Empty in demo)
    DIGILOCKER_CLIENT_ID: Optional[str] = None
    DIGILOCKER_CLIENT_SECRET: Optional[str] = None
    DIGILOCKER_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/digilocker/callback"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
