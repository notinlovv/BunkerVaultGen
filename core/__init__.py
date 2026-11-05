"""Core package for the offline Zero-Knowledge password manager.

Exposes cryptographic primitives, secure password generation, and data models.
"""

from core.models import PasswordEntry, VaultData
from core.generator import generate_password, calculate_entropy
from core.crypto import (
    encrypt_vault,
    decrypt_vault,
    derive_key,
    CryptoError,
    DecryptionError,
    InvalidVaultFormatError,
)

__all__ = [
    "PasswordEntry",
    "VaultData",
    "generate_password",
    "calculate_entropy",
    "encrypt_vault",
    "decrypt_vault",
    "derive_key",
    "CryptoError",
    "DecryptionError",
    "InvalidVaultFormatError",
]

