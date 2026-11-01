import hashlib
from typing import Dict
from app.providers.base import StorageProvider

# In-memory mock encrypted store
_MOCK_STORAGE_VAULT: Dict[str, bytes] = {}


class MockStorageProvider(StorageProvider):
    """
    Mock storage representing the user-owned encrypted vault.
    Stores and retrieves encrypted bytes without decrypting them.
    """
    async def store_encrypted_blob(self, blob_data: bytes, key: str) -> str:
        ref_id = hashlib.sha256(blob_data + key.encode()).hexdigest()[:24]
        _MOCK_STORAGE_VAULT[ref_id] = blob_data
        return f"vault_blob_{ref_id}"

    async def retrieve_encrypted_blob(self, ref: str) -> bytes:
        clean_ref = ref.replace("vault_blob_", "")
        if clean_ref not in _MOCK_STORAGE_VAULT:
            raise FileNotFoundError(f"Encrypted blob reference {ref} not found")
        return _MOCK_STORAGE_VAULT[clean_ref]
