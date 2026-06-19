"""Cryptographic utilities for phone encryption"""

import os
import hmac
import hashlib
import base64
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import SecretStr


class CryptoService:
    """AES-256-GCM encryption + HMAC-SHA256 for phone data"""

    def __init__(self, pepper: Optional[str] = None):
        self.pepper = pepper.encode() if pepper else os.environ.get("CRYPTO_PEPPER", "").encode()
        self.key = hashlib.sha256(self.pepper).digest()[:32]
        self.aesgcm = AESGCM(self.key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext with random nonce"""
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext.encode(), None)
        return base64.b64encode(nonce + ciphertext).decode()

    def decrypt(self, encrypted: str) -> str:
        """Decrypt ciphertext"""
        data = base64.b64decode(encrypted)
        nonce, ciphertext = data[:12], data[12:]
        return self.aesgcm.decrypt(nonce, ciphertext, None).decode()

    def hash_phone(self, phone: str) -> str:
        """Create phone hash for UNIQUE constraint"""
        normalized = phone.replace(" ", "").replace("-", "")
        return hashlib.sha256(normalized.encode()).hexdigest()

    def hmac_phone(self, phone: str) -> str:
        """Generate HMAC for phone verification"""
        normalized = phone.replace(" ", "").replace("-", "")
        return hmac.new(self.pepper, normalized.encode(), hashlib.sha256).hexdigest()


# Singleton instance
_crypto: Optional[CryptoService] = None


def get_crypto() -> CryptoService:
    global _crypto
    if _crypto is None:
        pepper = os.environ.get("CRYPTO_PEPPER", "dev_pepper_change_in_production")
        _crypto = CryptoService(pepper)
    return _crypto
