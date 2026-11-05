"""Storage package for vault lifecycle, persistence, and session management."""

from storage.vault_manager import (
    VaultAlreadyExistsError,
    VaultError,
    VaultLockedError,
    VaultManager,
    VaultNotFoundError,
    InvalidCredentialsError,
    VaultTamperedError,
)

__all__ = [
    "VaultManager",
    "VaultError",
    "VaultLockedError",
    "VaultNotFoundError",
    "VaultAlreadyExistsError",
    "InvalidCredentialsError",
    "VaultTamperedError",
]

