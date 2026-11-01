from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class DigiLockerProvider(ABC):
    """
    Abstract interface for DigiLocker / Account Aggregator OAuth2 exchange.
    Hard Rule: Real integration redirects to official aggregator. Mock is DEMO ONLY.
    """
    @abstractmethod
    async def create_authorization_url(self, session_id: str, scopes: List[str]) -> Dict[str, str]:
        """Generate OAuth 2.0 authorization URL with state & PKCE"""
        pass

    @abstractmethod
    async def exchange_code_for_token(self, code: str, state: str) -> Dict[str, Any]:
        """Exchange authorization code for token (token must never appear in raw logs)"""
        pass

    @abstractmethod
    async def get_issued_documents(self, token: str) -> List[Dict[str, Any]]:
        """List verified documents issued to the citizen"""
        pass

    @abstractmethod
    async def fetch_document_content(self, token: str, uri: str) -> Dict[str, Any]:
        """Fetch document metadata & encrypted blob reference"""
        pass


class LLMProvider(ABC):
    """
    Abstract interface for LLM (Gemini / Claude / Mock).
    Hard Rule: LLM never sees raw files, tokens, or unmasked IDs/OTPs.
    Hard Rule: LLM never decides eligibility.
    """
    @abstractmethod
    async def explain_eligibility(
        self,
        deterministic_outcome: Dict[str, Any],
        masked_customer_data: Dict[str, Any],
        citations: List[Dict[str, str]]
    ) -> str:
        """Generate user-friendly, cited explanation of deterministic code decision"""
        pass

    @abstractmethod
    async def analyze_document_gaps(
        self,
        required_doc_types: List[str],
        present_masked_docs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Identify missing documents and formulate conversational questions for customer"""
        pass


class OCRProvider(ABC):
    """
    Abstract OCR / Document Parser interface.
    Hard Rule: Masks full Aadhaar down to last 4 digits before returning.
    """
    @abstractmethod
    async def extract_masked_fields(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Extract only sanitized and masked metadata from a document"""
        pass


class StorageProvider(ABC):
    """
    Abstract vault storage provider for encrypted blobs.
    """
    @abstractmethod
    async def store_encrypted_blob(self, blob_data: bytes, key: str) -> str:
        """Store pre-encrypted blob and return reference ID"""
        pass

    @abstractmethod
    async def retrieve_encrypted_blob(self, ref: str) -> bytes:
        """Retrieve pre-encrypted blob bytes"""
        pass


class PolicyProvider(ABC):
    """
    Abstract interface for Policy data providers.
    Fetches policy schedules, coverage limits, terms, and verifies policyholder validity.
    """
    @abstractmethod
    async def get_policy(self, policy_number: str, holder_ref: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch policy details by policy number, optionally validating against holder reference"""
        pass

    @abstractmethod
    async def verify_policy_for_claim(
        self,
        policy_number: str,
        holder_name: str,
        incident_date: Any
    ) -> Dict[str, Any]:
        """
        Verify policy eligibility for a prospective claim:
        - belongs to claimant/holder
        - policy is ACTIVE
        - incident occurred within [start_date, end_date]
        """
        pass

