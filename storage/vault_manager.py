"""Session management, atomic disk persistence, and CRUD operations for the password vault."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.crypto import (
    DecryptionError,
    InvalidVaultFormatError,
    decrypt_vault,
    encrypt_vault,
)
from core.models import PasswordEntry, VaultData


class VaultError(Exception):
    """Base exception for all vault storage and session errors."""


class VaultLockedError(VaultError):
    """Raised when an operation requiring an open vault is executed while locked."""


class VaultNotFoundError(VaultError):
    """Raised when the specified vault file does not exist on disk."""


class VaultAlreadyExistsError(VaultError):
    """Raised when attempting to create a vault at an existing path without overwrite."""


class InvalidCredentialsError(VaultError):
    """Raised when master password fails decryption or authentication tag check."""


class VaultTamperedError(VaultError):
    """Raised when vault data is corrupted or contains an invalid header."""


class VaultManager:
    """Manages active vault session state, atomic storage, and CRUD operations."""

    def __init__(self) -> None:
        self._vault_data: Optional[VaultData] = None
        self._master_password: Optional[str] = None
        self._filepath: Optional[Path] = None

    @property
    def is_unlocked(self) -> bool:
        """Returns True if a vault is currently unlocked and ready for operations."""
        return self._vault_data is not None and self._master_password is not None

    @property
    def vault_path(self) -> Optional[Path]:
        """Returns the Path to the active vault file, or None if locked."""
        return self._filepath

    @property
    def entries(self) -> List[PasswordEntry]:
        """Returns a copy of the password entries list. Vault must be unlocked."""
        self._ensure_unlocked()
        assert self._vault_data is not None
        return list(self._vault_data.entries)

    def _ensure_unlocked(self) -> None:
        """Internal guard ensuring that the vault is unlocked."""
        if not self.is_unlocked:
            raise VaultLockedError("Vault is locked. Unlock or create a vault first.")

    @staticmethod
    def _atomic_write(target_path: Path, data: bytes) -> None:
        """Atomically writes data to disk using a temporary file and atomic replace.

        Flushes and fsyncs data to ensure persistence even in case of power loss.
        """
        target_path = Path(target_path).resolve()
        parent_dir = target_path.parent
        parent_dir.mkdir(parents=True, exist_ok=True)

        temp_file = tempfile.NamedTemporaryFile(
            dir=parent_dir, delete=False, prefix=".vault_tmp_"
        )
        temp_path = Path(temp_file.name)
        try:
            temp_file.write(data)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_file.close()
            temp_path.replace(target_path)
        except Exception:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise

    def create_vault(
        self,
        filepath: Union[str, Path],
        master_password: str,
        overwrite: bool = False,
    ) -> None:
        """Initializes a new encrypted vault file on disk and unlocks the session.

        Args:
            filepath: Destination file path for the vault (e.g., 'passwords.vault').
            master_password: Plaintext master password for key derivation.
            overwrite: If True, existing file at filepath will be replaced.

        Raises:
            ValueError: If master password is empty.
            VaultAlreadyExistsError: If target file exists and overwrite is False.
        """
        if not master_password:
            raise ValueError("Master password must not be empty.")

        resolved_path = Path(filepath).resolve()
        if resolved_path.exists() and not overwrite:
            raise VaultAlreadyExistsError(
                f"Vault file already exists at '{resolved_path}'. Set overwrite=True to replace."
            )

        new_vault = VaultData()
        raw_json = new_vault.to_json().encode("utf-8")
        encrypted_payload = encrypt_vault(master_password, raw_json)

        self._atomic_write(resolved_path, encrypted_payload)

        # Establish active unlocked session
        self._vault_data = new_vault
        self._master_password = master_password
        self._filepath = resolved_path

    def unlock_vault(self, filepath: Union[str, Path], master_password: str) -> bool:
        """Unlocks an existing encrypted vault file and populates in-memory session.

        Args:
            filepath: Path to the encrypted vault file.
            master_password: Plaintext master password to decrypt the vault.

        Returns:
            True upon successful unlock.

        Raises:
            ValueError: If master password is empty.
            VaultNotFoundError: If the vault file does not exist.
            InvalidCredentialsError: If password is wrong or tag verification fails.
            VaultTamperedError: If file container is corrupted or header is invalid.
        """
        if not master_password:
            raise ValueError("Master password must not be empty.")

        resolved_path = Path(filepath).resolve()
        if not resolved_path.exists() or not resolved_path.is_file():
            raise VaultNotFoundError(f"Vault file not found at: '{resolved_path}'.")

        encrypted_payload = resolved_path.read_bytes()

        try:
            decrypted_bytes = decrypt_vault(master_password, encrypted_payload)
        except DecryptionError as exc:
            raise InvalidCredentialsError(
                "Failed to unlock vault: invalid master password or corrupted data."
            ) from exc
        except InvalidVaultFormatError as exc:
            raise VaultTamperedError(
                f"Failed to unlock vault: container format is invalid ({exc})."
            ) from exc

        try:
            vault_data = VaultData.from_json(decrypted_bytes.decode("utf-8"))
        except Exception as exc:
            raise VaultTamperedError(
                f"Decrypted payload is not valid vault JSON: {exc}"
            ) from exc

        # Set active session
        self._vault_data = vault_data
        self._master_password = master_password
        self._filepath = resolved_path
        return True

    def lock_vault(self) -> None:
        """Closes the current session, clearing all sensitive data from memory."""
        self._vault_data = None
        self._master_password = None
        self._filepath = None

    def save_changes(self) -> None:
        """Serializes, encrypts, and atomically persists current vault changes to disk.

        Raises:
            VaultLockedError: If vault is not currently unlocked.
        """
        self._ensure_unlocked()
        assert self._vault_data is not None
        assert self._master_password is not None
        assert self._filepath is not None

        raw_json = self._vault_data.to_json().encode("utf-8")
        encrypted_payload = encrypt_vault(self._master_password, raw_json)
        self._atomic_write(self._filepath, encrypted_payload)

    def add_entry(
        self,
        title: str,
        username: str,
        password: str,
        url: str = "",
        notes: str = "",
    ) -> PasswordEntry:
        """Adds a new password entry to the vault and persists changes to disk.

        Args:
            title: Title / service name (e.g. 'ProtonMail').
            username: Account username or email.
            password: Password string.
            url: Optional website URL.
            notes: Optional text notes.

        Returns:
            The created PasswordEntry instance.
        """
        self._ensure_unlocked()
        assert self._vault_data is not None

        if not title or not username or not password:
            raise ValueError("Entry title, username, and password must not be empty.")

        entry = PasswordEntry(
            title=title.strip(),
            username=username.strip(),
            password=password,
            url=url.strip(),
            notes=notes.strip(),
        )
        self._vault_data.add_entry(entry)
        self.save_changes()
        return entry

    def get_entry(self, entry_id: str) -> Optional[PasswordEntry]:
        """Retrieves an entry by its UUID. Returns None if not found."""
        self._ensure_unlocked()
        assert self._vault_data is not None
        return self._vault_data.get_entry(entry_id)

    def update_entry(self, entry_id: str, **kwargs: Any) -> bool:
        """Updates fields of an existing entry and persists changes to disk.

        Supported kwargs: title, username, password, url, notes.

        Returns:
            True if entry was found and updated, False otherwise.
        """
        self._ensure_unlocked()
        assert self._vault_data is not None

        entry = self._vault_data.get_entry(entry_id)
        if entry is None:
            return False

        allowed_fields = {"title", "username", "password", "url", "notes"}
        modified = False

        for field_name, value in kwargs.items():
            if field_name in allowed_fields:
                if field_name == "password":
                    entry.update_password(str(value))
                else:
                    setattr(entry, field_name, str(value).strip())
                modified = True

        if modified:
            entry.touch()
            self._vault_data.touch()
            self.save_changes()

        return modified

    def delete_entry(self, entry_id: str) -> bool:
        """Deletes an entry by its ID and persists changes to disk.

        Returns:
            True if entry was found and deleted, False otherwise.
        """
        self._ensure_unlocked()
        assert self._vault_data is not None

        removed = self._vault_data.remove_entry(entry_id)
        if removed:
            self.save_changes()
        return removed

    def search_entries(self, query: str) -> List[PasswordEntry]:
        """Case-insensitive search over title, username, url, and notes.

        Args:
            query: Substring to search for. If empty, returns all entries.

        Returns:
            List of matching PasswordEntry objects.
        """
        self._ensure_unlocked()
        assert self._vault_data is not None

        q = query.strip().lower()
        if not q:
            return list(self._vault_data.entries)

        matches: List[PasswordEntry] = []
        for entry in self._vault_data.entries:
            if (
                q in entry.title.lower()
                or q in entry.username.lower()
                or q in entry.url.lower()
                or q in entry.notes.lower()
            ):
                matches.append(entry)

        return matches

    def list_entries(self) -> List[PasswordEntry]:
        """Returns all entries currently stored in the vault."""
        return self.entries

    def __enter__(self) -> VaultManager:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.lock_vault()

