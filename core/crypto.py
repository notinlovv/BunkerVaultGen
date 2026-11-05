"""Cryptographic primitives for Zero-Knowledge offline vault encryption.

Implements Argon2id / PBKDF2-HMAC-SHA256 key derivation and AES-256-GCM
authenticated encryption.
"""

from __future__ import annotations

import secrets
from typing import Optional

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

try:
    import argon2.low_level as argon2_ll

    HAS_ARGON2: bool = True
except ImportError:
    HAS_ARGON2 = False

# Protocol header constants
MAGIC_BYTES: bytes = b"ZKPV"  # Zero-Knowledge Password Vault
FORMAT_VERSION: int = 1

# KDF identifiers
KDF_ARGON2ID: int = 1
KDF_PBKDF2: int = 2

# Cryptographic sizes
SALT_SIZE: int = 16
NONCE_SIZE: int = 12
KEY_SIZE: int = 32  # 256-bit key for AES-256
TAG_SIZE: int = 16  # AES-GCM authentication tag size

HEADER_SIZE: int = 4 + 1 + 1 + SALT_SIZE + NONCE_SIZE  # 34 bytes
MIN_PAYLOAD_SIZE: int = HEADER_SIZE + TAG_SIZE  # 50 bytes

# KDF default parameters (OWASP-aligned)
PBKDF2_MIN_ITERATIONS: int = 600_000
ARGON2_TIME_COST: int = 3
ARGON2_MEMORY_COST: int = 65536  # 64 MiB
ARGON2_PARALLELISM: int = 4


class CryptoError(Exception):
    """Base exception for cryptographic operations."""


class DecryptionError(CryptoError):
    """Raised when decryption fails due to invalid password or tampered data."""


class InvalidVaultFormatError(CryptoError):
    """Raised when the vault container format is invalid, corrupted, or unsupported."""


def derive_key(
    master_password: str,
    salt: bytes,
    kdf_type: int = KDF_ARGON2ID,
    iterations: int = PBKDF2_MIN_ITERATIONS,
    argon2_time_cost: int = ARGON2_TIME_COST,
    argon2_memory_cost: int = ARGON2_MEMORY_COST,
    argon2_parallelism: int = ARGON2_PARALLELISM,
) -> bytes:
    """Derives a 256-bit symmetric encryption key from a master password and salt.

    Args:
        master_password: Plaintext master password.
        salt: Cryptographic random salt of at least 16 bytes.
        kdf_type: KDF identifier (KDF_ARGON2ID or KDF_PBKDF2).
        iterations: Number of PBKDF2 iterations (if PBKDF2 is selected).
        argon2_time_cost: Argon2id time cost (iterations).
        argon2_memory_cost: Argon2id memory cost in KiB.
        argon2_parallelism: Argon2id parallelism degree (threads).

    Returns:
        32-byte derived key.

    Raises:
        ValueError: If arguments are invalid.
        CryptoError: If the requested KDF is unsupported or unavailable.
    """
    if not master_password:
        raise ValueError("Master password must not be empty.")
    if len(salt) < SALT_SIZE:
        raise ValueError(f"Salt must be at least {SALT_SIZE} bytes.")

    password_bytes = master_password.encode("utf-8")

    if kdf_type == KDF_ARGON2ID:
        if not HAS_ARGON2:
            raise CryptoError(
                "Argon2id requested but argon2-cffi is not installed. Use PBKDF2 fallback."
            )
        return argon2_ll.hash_secret_raw(
            secret=password_bytes,
            salt=salt,
            time_cost=argon2_time_cost,
            memory_cost=argon2_memory_cost,
            parallelism=argon2_parallelism,
            hash_len=KEY_SIZE,
            type=argon2_ll.Type.ID,
        )

    if kdf_type == KDF_PBKDF2:
        if iterations < PBKDF2_MIN_ITERATIONS:
            raise ValueError(
                f"PBKDF2 iterations ({iterations}) below minimum security threshold ({PBKDF2_MIN_ITERATIONS})."
            )
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=salt,
            iterations=iterations,
        )
        return kdf.derive(password_bytes)

    raise ValueError(f"Unsupported KDF type identifier: {kdf_type}")


def encrypt_vault(
    master_password: str,
    raw_data: bytes,
    kdf_type: Optional[int] = None,
    salt: Optional[bytes] = None,
    nonce: Optional[bytes] = None,
    pbkdf2_iterations: int = PBKDF2_MIN_ITERATIONS,
) -> bytes:
    """Encrypts raw binary data using AES-256-GCM with authenticated metadata.

    Binary payload format:
        [0..4]   : Magic bytes (b"ZKPV")
        [4]      : Format version (0x01)
        [5]      : KDF algorithm ID (0x01 = Argon2id, 0x02 = PBKDF2)
        [6..22]  : Salt (16 bytes)
        [22..34] : Nonce / IV (12 bytes)
        [34..end]: AES-256-GCM ciphertext + 16-byte authentication tag

    Args:
        master_password: Plaintext master password.
        raw_data: Plaintext data to encrypt.
        kdf_type: Optional explicit KDF type. Defaults to Argon2id if available,
            otherwise falls back to PBKDF2.
        salt: Optional salt (auto-generated if omitted).
        nonce: Optional nonce (auto-generated if omitted).
        pbkdf2_iterations: Number of iterations if PBKDF2 is used.

    Returns:
        Packaged binary ciphertext payload.
    """
    if not master_password:
        raise ValueError("Master password must not be empty.")
    if not isinstance(raw_data, bytes):
        raise TypeError("raw_data must be bytes.")

    if kdf_type is None:
        kdf_type = KDF_ARGON2ID if HAS_ARGON2 else KDF_PBKDF2

    salt_bytes = salt if salt is not None else secrets.token_bytes(SALT_SIZE)
    nonce_bytes = nonce if nonce is not None else secrets.token_bytes(NONCE_SIZE)

    if len(salt_bytes) != SALT_SIZE:
        raise ValueError(f"Salt must be exactly {SALT_SIZE} bytes.")
    if len(nonce_bytes) != NONCE_SIZE:
        raise ValueError(f"Nonce must be exactly {NONCE_SIZE} bytes.")

    key = derive_key(
        master_password,
        salt=salt_bytes,
        kdf_type=kdf_type,
        iterations=pbkdf2_iterations,
    )

    header = (
        MAGIC_BYTES
        + bytes([FORMAT_VERSION, kdf_type])
        + salt_bytes
        + nonce_bytes
    )

    aesgcm = AESGCM(key)
    # The header is passed as associated_data to cryptographically bind metadata
    ciphertext_and_tag = aesgcm.encrypt(nonce_bytes, raw_data, associated_data=header)

    return header + ciphertext_and_tag


def decrypt_vault(master_password: str, encrypted_payload: bytes) -> bytes:
    """Decrypts a binary vault payload using AES-256-GCM and verifies authentication tag.

    Args:
        master_password: Plaintext master password.
        encrypted_payload: Packaged binary payload previously returned by encrypt_vault.

    Returns:
        Decrypted plaintext bytes.

    Raises:
        ValueError: If input arguments are invalid.
        InvalidVaultFormatError: If payload header is malformed, truncated, or invalid.
        DecryptionError: If the password is wrong or ciphertext has been altered.
    """
    if not master_password:
        raise ValueError("Master password must not be empty.")
    if not isinstance(encrypted_payload, bytes):
        raise TypeError("encrypted_payload must be bytes.")

    if len(encrypted_payload) < MIN_PAYLOAD_SIZE:
        raise InvalidVaultFormatError(
            f"Payload too short ({len(encrypted_payload)} bytes). Minimum valid size is {MIN_PAYLOAD_SIZE} bytes."
        )

    magic = encrypted_payload[:4]
    if magic != MAGIC_BYTES:
        raise InvalidVaultFormatError(
            f"Invalid magic header: expected {MAGIC_BYTES!r}, received {magic!r}."
        )

    version = encrypted_payload[4]
    if version != FORMAT_VERSION:
        raise InvalidVaultFormatError(
            f"Unsupported vault format version {version}. Supported: {FORMAT_VERSION}."
        )

    kdf_type = encrypted_payload[5]
    if kdf_type not in (KDF_ARGON2ID, KDF_PBKDF2):
        raise InvalidVaultFormatError(f"Unknown or unsupported KDF identifier: {kdf_type}.")

    salt = encrypted_payload[6:22]
    nonce = encrypted_payload[22:34]
    header = encrypted_payload[:HEADER_SIZE]
    ciphertext_and_tag = encrypted_payload[HEADER_SIZE:]

    try:
        key = derive_key(master_password, salt=salt, kdf_type=kdf_type)
    except CryptoError as exc:
        raise exc
    except Exception as exc:
        raise CryptoError(f"Key derivation failed: {exc}") from exc

    aesgcm = AESGCM(key)
    try:
        decrypted_data = aesgcm.decrypt(nonce, ciphertext_and_tag, associated_data=header)
        return decrypted_data
    except (InvalidTag, InvalidSignature) as exc:
        raise DecryptionError(
            "Decryption failed: incorrect master password or altered/corrupted data."
        ) from exc

