import base64
import os
import json
import time
from typing import Dict, Any, List
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class BankPackageExchangeService:
    """
    Implements Hybrid Encryption for customer-to-bank package exchange:
    1. Client generates random 256-bit AES-GCM key and encrypts consented files.
    2. Client encrypts that AES key with bank's RSA-OAEP public key.
    3. Bank decrypts the AES key using its private RSA key, verifies SHA-256 hash, and extracts files.
    4. Supports consent revocation: changes bank's access status to REVOKED and starts retention clock.
    """
    def __init__(self):
        # Generate bank RSA-2048 keypair for dev / mock bank
        self.bank_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.bank_public_key = self.bank_private_key.public_key()
        self.revoked_tokens = set()

    def create_encrypted_package(
        self,
        files: List[Dict[str, Any]],
        consented_scopes: List[str]
    ) -> Dict[str, Any]:
        """Simulates client-side hybrid encryption before transmission"""
        # 1. Generate random AES-256 key
        aes_key = AESGCM.generate_key(bit_length=256)
        aesgcm = AESGCM(aes_key)
        
        # 2. Encrypt files payload
        nonce = os.urandom(12)
        payload_bytes = json.dumps({
            "files": files,
            "consented_scopes": consented_scopes,
            "timestamp": time.time()
        }).encode('utf-8')
        ciphertext = aesgcm.encrypt(nonce, payload_bytes, None)

        # 3. Encrypt AES key using Bank's RSA Public Key
        encrypted_aes_key = self.bank_public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        package_hash = hashes.Hash(hashes.SHA256())
        package_hash.update(ciphertext)
        digest = package_hash.finalize().hex()

        return {
            "encrypted_aes_key_b64": base64.b64encode(encrypted_aes_key).decode('utf-8'),
            "nonce_b64": base64.b64encode(nonce).decode('utf-8'),
            "ciphertext_b64": base64.b64encode(ciphertext).decode('utf-8'),
            "package_sha256": digest,
            "scope_count": len(consented_scopes)
        }

    def decrypt_package_as_bank(self, package: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypts package on bank ingestion worker using bank's RSA private key"""
        encrypted_aes_key = base64.b64decode(package["encrypted_aes_key_b64"])
        nonce = base64.b64decode(package["nonce_b64"])
        ciphertext = base64.b64decode(package["ciphertext_b64"])

        # Verify integrity
        h = hashes.Hash(hashes.SHA256())
        h.update(ciphertext)
        computed_digest = h.finalize().hex()
        if computed_digest != package["package_sha256"]:
            raise ValueError("Tampered package rejected: SHA-256 digest mismatch")

        # Decrypt AES key with Bank Private Key
        aes_key = self.bank_private_key.decrypt(
            encrypted_aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # Decrypt files payload
        aesgcm = AESGCM(aes_key)
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(decrypted_bytes.decode('utf-8'))

    def revoke_consent(self, token: str) -> Dict[str, Any]:
        self.revoked_tokens.add(token)
        return {
            "status": "REVOKED",
            "token": token,
            "retention_clock_started": True,
            "retention_hours_remaining": 24
        }
