"""Tests for Phase 2: VaultManager persistence, session lifecycle, and secure clipboard."""

import time
from pathlib import Path
import pytest

from core.crypto import MAGIC_BYTES
from storage.vault_manager import (
    InvalidCredentialsError,
    VaultAlreadyExistsError,
    VaultLockedError,
    VaultManager,
    VaultNotFoundError,
    VaultTamperedError,
)
from utils.clipboard import (
    clear_clipboard,
    copy_with_autoclear,
    get_clipboard,
    set_clipboard,
)


# ============================================================================
# VaultManager Lifecycle & Persistence Tests
# ============================================================================


class TestVaultManagerLifecycle:
    """Tests for vault creation, unlocking, locking, and atomic persistence."""

    def test_create_and_unlock_vault(self, tmp_path: Path):
        vault_file = tmp_path / "test.vault"
        manager = VaultManager()

        assert not manager.is_unlocked
        assert manager.vault_path is None

        manager.create_vault(vault_file, "MasterPass123!")

        assert manager.is_unlocked
        assert manager.vault_path == vault_file.resolve()
        assert vault_file.exists()

        # Verify disk file format starts with magic bytes
        raw_bytes = vault_file.read_bytes()
        assert raw_bytes.startswith(MAGIC_BYTES)

        # Lock the vault
        manager.lock_vault()
        assert not manager.is_unlocked
        assert manager.vault_path is None

        # Reopen with correct password
        new_manager = VaultManager()
        success = new_manager.unlock_vault(vault_file, "MasterPass123!")
        assert success is True
        assert new_manager.is_unlocked
        assert len(new_manager.list_entries()) == 0

    def test_create_vault_already_exists_raises(self, tmp_path: Path):
        vault_file = tmp_path / "existing.vault"
        manager = VaultManager()
        manager.create_vault(vault_file, "MasterPass123!")

        # Attempt to create again without overwrite
        with pytest.raises(VaultAlreadyExistsError, match="already exists"):
            manager.create_vault(vault_file, "AnotherPass!")

        # Overwrite=True should succeed
        manager.create_vault(vault_file, "AnotherPass!", overwrite=True)
        assert manager.is_unlocked

    def test_unlock_non_existent_file_raises(self, tmp_path: Path):
        manager = VaultManager()
        with pytest.raises(VaultNotFoundError, match="not found"):
            manager.unlock_vault(tmp_path / "does_not_exist.vault", "pass")

    def test_unlock_with_wrong_password_raises(self, tmp_path: Path):
        vault_file = tmp_path / "secure.vault"
        manager = VaultManager()
        manager.create_vault(vault_file, "CorrectPassword99#")
        manager.lock_vault()

        with pytest.raises(InvalidCredentialsError, match="invalid master password"):
            manager.unlock_vault(vault_file, "WrongPassword!")

    def test_unlock_tampered_file_raises(self, tmp_path: Path):
        vault_file = tmp_path / "tampered.vault"
        manager = VaultManager()
        manager.create_vault(vault_file, "CorrectPassword99#")
        manager.lock_vault()

        # Tamper with file on disk
        data = bytearray(vault_file.read_bytes())
        data[40] ^= 0xFF
        vault_file.write_bytes(bytes(data))

        with pytest.raises((InvalidCredentialsError, VaultTamperedError)):
            manager.unlock_vault(vault_file, "CorrectPassword99#")

    def test_context_manager_auto_locks(self, tmp_path: Path):
        vault_file = tmp_path / "ctx.vault"
        with VaultManager() as manager:
            manager.create_vault(vault_file, "Password123!")
            assert manager.is_unlocked

        assert not manager.is_unlocked


# ============================================================================
# VaultManager CRUD Operations & Persistence
# ============================================================================


class TestVaultManagerCRUD:
    """Tests for adding, updating, searching, and deleting credentials."""

    def test_crud_full_flow(self, tmp_path: Path):
        vault_file = tmp_path / "crud.vault"
        manager = VaultManager()
        manager.create_vault(vault_file, "Pass1234!")

        # 1. Add Entry
        entry = manager.add_entry(
            title="GitHub",
            username="dev_user",
            password="InitialSecretPassword123!",
            url="https://github.com",
            notes="SSH keys and 2FA info",
        )
        assert entry.title == "GitHub"
        assert entry.username == "dev_user"
        assert len(manager.list_entries()) == 1

        # 2. Get Entry
        fetched = manager.get_entry(entry.id)
        assert fetched is not None
        assert fetched.id == entry.id
        assert fetched.password == "InitialSecretPassword123!"

        # 3. Update Entry
        updated = manager.update_entry(
            entry.id,
            password="RotatedPassword999$",
            notes="Updated notes",
        )
        assert updated is True
        refetched = manager.get_entry(entry.id)
        assert refetched is not None
        assert refetched.password == "RotatedPassword999$"
        assert refetched.notes == "Updated notes"

        # Update non-existent entry
        assert manager.update_entry("unknown-id", password="p") is False

        # 4. Search Entries
        manager.add_entry(
            title="ProtonMail",
            username="personal@pm.me",
            password="MailPassword!",
            url="https://mail.proton.me",
        )
        manager.add_entry(
            title="Work VPN",
            username="company_user",
            password="VpnPassword!",
            url="https://vpn.company.com",
        )

        # Case-insensitive title search
        assert len(manager.search_entries("github")) == 1
        assert len(manager.search_entries("GIT")) == 1

        # Search username
        assert len(manager.search_entries("pm.me")) == 1

        # Search URL
        assert len(manager.search_entries("company.com")) == 1

        # Search empty returns all
        assert len(manager.search_entries("")) == 3

        # Search non-matching returns empty list
        assert len(manager.search_entries("non-existent-service")) == 0

        # 5. Delete Entry
        assert manager.delete_entry(entry.id) is True
        assert manager.get_entry(entry.id) is None
        assert len(manager.list_entries()) == 2
        assert manager.delete_entry("non-existent-id") is False

    def test_real_persistence_across_sessions(self, tmp_path: Path):
        """Verifies that all changes persist to disk through lock and unlock cycles."""
        vault_file = tmp_path / "persistent.vault"
        master_password = "SuperSecretMasterKey2026!"

        # Session 1: Create and populate
        session1 = VaultManager()
        session1.create_vault(vault_file, master_password)
        entry1 = session1.add_entry("AWS", "root", "AwsPass1!", url="https://aws.amazon.com")
        entry2 = session1.add_entry("Google", "user@gmail.com", "GooglePass2!")
        session1.lock_vault()

        # Session 2: Unlock and verify
        session2 = VaultManager()
        session2.unlock_vault(vault_file, master_password)
        assert len(session2.list_entries()) == 2

        e1 = session2.get_entry(entry1.id)
        assert e1 is not None
        assert e1.title == "AWS"
        assert e1.password == "AwsPass1!"

        e2 = session2.get_entry(entry2.id)
        assert e2 is not None
        assert e2.title == "Google"

        # Modify in Session 2
        session2.update_entry(e1.id, password="AwsPassRotated3!")
        session2.delete_entry(e2.id)
        session2.add_entry("Slack", "worker", "SlackPass4!")
        session2.lock_vault()

        # Session 3: Unlock and verify modifications
        session3 = VaultManager()
        session3.unlock_vault(vault_file, master_password)
        assert len(session3.list_entries()) == 2

        updated_e1 = session3.get_entry(entry1.id)
        assert updated_e1 is not None
        assert updated_e1.password == "AwsPassRotated3!"

        deleted_e2 = session3.get_entry(entry2.id)
        assert deleted_e2 is None

        slack_entries = session3.search_entries("Slack")
        assert len(slack_entries) == 1
        assert slack_entries[0].password == "SlackPass4!"

    def test_locked_operations_raise_vault_locked_error(self):
        manager = VaultManager()
        assert not manager.is_unlocked

        with pytest.raises(VaultLockedError):
            manager.add_entry("T", "U", "P")

        with pytest.raises(VaultLockedError):
            manager.get_entry("some-id")

        with pytest.raises(VaultLockedError):
            manager.update_entry("some-id", password="p")

        with pytest.raises(VaultLockedError):
            manager.delete_entry("some-id")

        with pytest.raises(VaultLockedError):
            manager.search_entries("query")

        with pytest.raises(VaultLockedError):
            manager.save_changes()

        with pytest.raises(VaultLockedError):
            _ = manager.entries


# ============================================================================
# Secure Clipboard Tests
# ============================================================================


class TestClipboard:
    """Tests for secure clipboard handling and delayed autoclear."""

    def setup_method(self):
        clear_clipboard()

    def teardown_method(self):
        clear_clipboard()

    def test_clipboard_set_and_get(self):
        set_clipboard("MySecretData123")
        assert get_clipboard() == "MySecretData123"

        clear_clipboard()
        assert get_clipboard() == ""

    def test_copy_with_autoclear_clears_after_timeout(self):
        secret = "TemporaryPasswordToBeCleared"
        thread = copy_with_autoclear(secret, timeout_seconds=0.08)

        # Content must be immediately available
        assert get_clipboard() == secret

        # Wait for thread to finish
        thread.join(timeout=1.0)
        time.sleep(0.02)

        # Clipboard must now be wiped
        assert get_clipboard() == ""

    def test_copy_with_autoclear_preserves_new_user_clipboard(self):
        initial = "FirstPassword"
        thread = copy_with_autoclear(initial, timeout_seconds=0.10)

        # User copies something else shortly after
        time.sleep(0.03)
        set_clipboard("SubsequentUserCopiedText")

        # Wait for the first autoclear thread to expire
        thread.join(timeout=1.0)
        time.sleep(0.02)

        # The subsequent copy must NOT have been overwritten
        assert get_clipboard() == "SubsequentUserCopiedText"

