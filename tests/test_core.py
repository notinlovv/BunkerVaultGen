"""Unit test suite for Phase 1: Cryptographic core, models, and secure generator."""

import json
import math
import string
import uuid
import pytest

from core.crypto import (
    FORMAT_VERSION,
    HEADER_SIZE,
    KDF_ARGON2ID,
    KDF_PBKDF2,
    MAGIC_BYTES,
    MIN_PAYLOAD_SIZE,
    CryptoError,
    DecryptionError,
    InvalidVaultFormatError,
    decrypt_vault,
    derive_key,
    encrypt_vault,
)
from core.generator import (
    AMBIGUOUS_CHARS,
    DIGITS,
    LOWERCASE,
    SYMBOLS,
    UPPERCASE,
    calculate_entropy,
    generate_password,
)
from core.models import PasswordEntry, VaultData


# ============================================================================
# Models Tests (PasswordEntry & VaultData)
# ============================================================================


class TestModels:
    """Tests for data structures and serialization."""

    def test_password_entry_creation_and_defaults(self):
        entry = PasswordEntry(
            title="ProtonMail",
            username="alice@proton.me",
            password="UltraSecretPassword123!",
        )

        assert entry.title == "ProtonMail"
        assert entry.username == "alice@proton.me"
        assert entry.password == "UltraSecretPassword123!"
        assert entry.url == ""
        assert entry.notes == ""
        # Verify valid UUID4
        uuid_obj = uuid.UUID(entry.id, version=4)
        assert str(uuid_obj) == entry.id
        assert entry.created_at != ""
        assert entry.updated_at != ""

    def test_password_entry_touch_and_update(self):
        entry = PasswordEntry(
            title="GitHub",
            username="octocat",
            password="old-password",
        )
        old_updated = entry.updated_at
        entry.update_password("new-secure-password")
        assert entry.password == "new-secure-password"
        assert entry.updated_at >= old_updated

    def test_password_entry_dict_roundtrip(self):
        entry = PasswordEntry(
            id="00000000-0000-0000-0000-000000000001",
            title="Bitbucket",
            username="dev",
            password="secret_pass_123",
            url="https://bitbucket.org",
            notes="Work account",
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )
        data = entry.to_dict()
        restored = PasswordEntry.from_dict(data)
        assert restored == entry

    def test_password_entry_from_dict_missing_fields_raises(self):
        with pytest.raises(ValueError, match="Missing required field"):
            PasswordEntry.from_dict({"title": "Test", "username": "user"})

    def test_vault_data_add_get_remove_entry(self):
        vault = VaultData()
        assert vault.entries == []

        entry1 = PasswordEntry(title="Bank", username="user1", password="pw1")
        entry2 = PasswordEntry(title="Email", username="user2", password="pw2")

        vault.add_entry(entry1)
        vault.add_entry(entry2)
        assert len(vault.entries) == 2

        # Get existing
        assert vault.get_entry(entry1.id) == entry1
        # Get non-existing
        assert vault.get_entry("non-existent-uuid") is None

        # Update entry by adding entry with same ID
        updated_entry1 = PasswordEntry(
            id=entry1.id,
            title="Bank Updated",
            username="user1",
            password="pw1_updated",
        )
        vault.add_entry(updated_entry1)
        assert len(vault.entries) == 2
        assert vault.get_entry(entry1.id).title == "Bank Updated"

        # Remove entry
        assert vault.remove_entry(entry1.id) is True
        assert len(vault.entries) == 1
        assert vault.get_entry(entry1.id) is None
        assert vault.remove_entry("non-existent-uuid") is False

    def test_vault_data_json_roundtrip(self):
        vault = VaultData(version=1)
        entry1 = PasswordEntry(
            title="Service A", username="alice", password="pass_a", url="https://a.com"
        )
        entry2 = PasswordEntry(
            title="Service B", username="bob", password="pass_b", notes="Some notes"
        )
        vault.add_entry(entry1)
        vault.add_entry(entry2)

        json_str = vault.to_json(indent=2)
        assert isinstance(json_str, str)

        restored = VaultData.from_json(json_str)
        assert restored.version == vault.version
        assert len(restored.entries) == 2
        assert restored.entries[0] == entry1
        assert restored.entries[1] == entry2

    def test_vault_data_from_json_invalid(self):
        with pytest.raises(ValueError, match="Invalid JSON string"):
            VaultData.from_json("not valid json {")

        with pytest.raises(ValueError, match="must be a JSON dictionary"):
            VaultData.from_json("[]")


# ============================================================================
# Generator & Entropy Tests
# ============================================================================


class TestGenerator:
    """Tests for secure password generation and entropy calculation."""

    def test_generate_password_default_length_and_types(self):
        pw = generate_password()
        assert len(pw) == 16
        assert any(c in LOWERCASE for c in pw)
        assert any(c in UPPERCASE for c in pw)
        assert any(c in DIGITS for c in pw)
        assert any(c in SYMBOLS for c in pw)

    def test_generate_password_custom_lengths(self):
        for length in (4, 12, 24, 64, 128):
            pw = generate_password(length=length)
            assert len(pw) == length

    def test_generate_password_guarantees_all_selected_sets(self):
        # Run 100 generations to guarantee all sets are present every single time
        for _ in range(100):
            pw = generate_password(
                length=16,
                use_upper=True,
                use_lower=True,
                use_digits=True,
                use_symbols=True,
            )
            assert any(c in LOWERCASE for c in pw), f"Lowercase missing in {pw}"
            assert any(c in UPPERCASE for c in pw), f"Uppercase missing in {pw}"
            assert any(c in DIGITS for c in pw), f"Digit missing in {pw}"
            assert any(c in SYMBOLS for c in pw), f"Symbol missing in {pw}"

    def test_generate_password_single_set(self):
        pw_digits = generate_password(
            length=10,
            use_upper=False,
            use_lower=False,
            use_digits=True,
            use_symbols=False,
        )
        assert len(pw_digits) == 10
        assert all(c in DIGITS for c in pw_digits)

        pw_lower = generate_password(
            length=10,
            use_upper=False,
            use_lower=True,
            use_digits=False,
            use_symbols=False,
        )
        assert len(pw_lower) == 10
        assert all(c in LOWERCASE for c in pw_lower)

    def test_generate_password_exclude_ambiguous(self):
        for _ in range(100):
            pw = generate_password(
                length=20,
                use_upper=True,
                use_lower=True,
                use_digits=True,
                use_symbols=True,
                exclude_ambiguous=True,
            )
            for ambig in AMBIGUOUS_CHARS:
                assert ambig not in pw, f"Ambiguous char '{ambig}' found in {pw}"

    def test_generate_password_invalid_parameters(self):
        # No sets selected
        with pytest.raises(ValueError, match="At least one character set must be selected"):
            generate_password(
                use_upper=False, use_lower=False, use_digits=False, use_symbols=False
            )

        # Length shorter than number of selected sets
        with pytest.raises(ValueError, match="must be at least 4"):
            generate_password(
                length=3,
                use_upper=True,
                use_lower=True,
                use_digits=True,
                use_symbols=True,
            )

    def test_calculate_entropy_empty(self):
        assert calculate_entropy("") == 0.0

    def test_calculate_entropy_digits_only(self):
        # 10 digits pool -> E = 8 * log2(10) ≈ 8 * 3.321928 = 26.58
        pw = "12345678"
        expected = round(8 * math.log2(10), 2)
        assert calculate_entropy(pw) == expected

    def test_calculate_entropy_lowercase_only(self):
        # 26 lowercase pool -> E = 8 * log2(26) ≈ 8 * 4.700439 = 37.60
        pw = "abcdefgh"
        expected = round(8 * math.log2(26), 2)
        assert calculate_entropy(pw) == expected

    def test_calculate_entropy_mixed(self):
        # lower + upper + digits -> R = 26 + 26 + 10 = 62
        pw = "aA1bB2cC3d"
        expected = round(10 * math.log2(62), 2)
        assert calculate_entropy(pw) == expected

    def test_calculate_entropy_custom_pool(self):
        pw = "secret"
        expected = round(len(pw) * math.log2(100), 2)
        assert calculate_entropy(pw, pool_size=100) == expected


# ============================================================================
# Crypto & Security Tests
# ============================================================================


class TestCrypto:
    """Tests for Argon2id/PBKDF2 key derivation and AES-256-GCM encryption."""

    def test_derive_key_argon2id(self):
        salt = b"\x00" * 16
        key = derive_key("MyMasterPassword123!", salt, kdf_type=KDF_ARGON2ID)
        assert isinstance(key, bytes)
        assert len(key) == 32

        # Deterministic with same salt and password
        key2 = derive_key("MyMasterPassword123!", salt, kdf_type=KDF_ARGON2ID)
        assert key == key2

        # Different password produces different key
        diff_key = derive_key("DifferentPassword456!", salt, kdf_type=KDF_ARGON2ID)
        assert key != diff_key

    def test_derive_key_pbkdf2(self):
        salt = b"\x01" * 16
        key = derive_key(
            "MyMasterPassword123!",
            salt,
            kdf_type=KDF_PBKDF2,
            iterations=600_000,
        )
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_derive_key_invalid_args(self):
        with pytest.raises(ValueError, match="must not be empty"):
            derive_key("", b"0" * 16)

        with pytest.raises(ValueError, match="at least 16 bytes"):
            derive_key("pass", b"short_salt")

        with pytest.raises(ValueError, match="below minimum security threshold"):
            derive_key("pass", b"0" * 16, kdf_type=KDF_PBKDF2, iterations=1000)

        with pytest.raises(ValueError, match="Unsupported KDF"):
            derive_key("pass", b"0" * 16, kdf_type=99)

    def test_encrypt_decrypt_roundtrip_argon2id(self):
        password = "VeryStrongMasterPassword!99#"
        plaintext = b"Zero-Knowledge secret raw payload test."

        encrypted = encrypt_vault(password, plaintext, kdf_type=KDF_ARGON2ID)

        assert isinstance(encrypted, bytes)
        assert len(encrypted) >= MIN_PAYLOAD_SIZE
        assert encrypted[:4] == MAGIC_BYTES
        assert encrypted[4] == FORMAT_VERSION
        assert encrypted[5] == KDF_ARGON2ID

        decrypted = decrypt_vault(password, encrypted)
        assert decrypted == plaintext

    def test_encrypt_decrypt_roundtrip_pbkdf2(self):
        password = "MasterPasswordPBKDF2!"
        plaintext = b"Testing PBKDF2 HMAC SHA-256 fallback."

        encrypted = encrypt_vault(password, plaintext, kdf_type=KDF_PBKDF2)
        assert encrypted[5] == KDF_PBKDF2

        decrypted = decrypt_vault(password, encrypted)
        assert decrypted == plaintext

    def test_full_cycle_vault_data(self):
        """Tests complete cycle: VaultData -> JSON -> encrypt -> decrypt -> VaultData."""
        master_password = "MasterPasswordForFullCycle!#"
        vault = VaultData(version=1)
        vault.add_entry(
            PasswordEntry(
                title="Amazon",
                username="shopper@example.com",
                password=generate_password(length=20),
                url="https://amazon.com",
                notes="Personal account",
            )
        )
        vault.add_entry(
            PasswordEntry(
                title="GitHub",
                username="coder",
                password=generate_password(length=24),
                url="https://github.com",
                notes="2FA recovery codes stored in vault",
            )
        )

        raw_json_bytes = vault.to_json().encode("utf-8")
        encrypted_payload = encrypt_vault(master_password, raw_json_bytes)

        # Ensure ciphertext is not plaintext
        assert b"shopper@example.com" not in encrypted_payload
        assert b"Amazon" not in encrypted_payload

        decrypted_bytes = decrypt_vault(master_password, encrypted_payload)
        restored_vault = VaultData.from_json(decrypted_bytes.decode("utf-8"))

        assert restored_vault.version == vault.version
        assert len(restored_vault.entries) == 2
        assert restored_vault.entries[0].title == "Amazon"
        assert restored_vault.entries[0].password == vault.entries[0].password
        assert restored_vault.entries[1].title == "GitHub"
        assert restored_vault.entries[1].password == vault.entries[1].password

    def test_decrypt_fails_with_wrong_password(self):
        password = "CorrectPassword123!"
        wrong_password = "WrongPassword456!"
        plaintext = b"Sensitive data"

        encrypted = encrypt_vault(password, plaintext)

        with pytest.raises(DecryptionError, match="incorrect master password or altered"):
            decrypt_vault(wrong_password, encrypted)

    def test_decrypt_fails_with_tampered_ciphertext(self):
        password = "MasterPassword123!"
        plaintext = b"Highly confidential payload"

        encrypted = bytearray(encrypt_vault(password, plaintext))

        # Tamper with the ciphertext portion (after HEADER_SIZE)
        tamper_idx = HEADER_SIZE + 2
        encrypted[tamper_idx] ^= 0x01

        with pytest.raises(DecryptionError):
            decrypt_vault(password, bytes(encrypted))

    def test_decrypt_fails_with_tampered_tag(self):
        password = "MasterPassword123!"
        plaintext = b"Protected data"

        encrypted = bytearray(encrypt_vault(password, plaintext))

        # Tamper with the last byte (authentication tag)
        encrypted[-1] ^= 0xFF

        with pytest.raises(DecryptionError):
            decrypt_vault(password, bytes(encrypted))

    def test_decrypt_fails_with_tampered_header_or_salt(self):
        password = "MasterPassword123!"
        plaintext = b"Secret text"

        encrypted = bytearray(encrypt_vault(password, plaintext))

        # Tamper with salt (bytes 6..22)
        encrypted[10] ^= 0x55

        with pytest.raises(DecryptionError):
            decrypt_vault(password, bytes(encrypted))

    def test_decrypt_fails_with_corrupt_magic(self):
        password = "MasterPassword123!"
        encrypted = bytearray(encrypt_vault(password, b"Data"))

        # Corrupt magic bytes b"ZKPV" -> b"XXXX"
        encrypted[0:4] = b"XXXX"

        with pytest.raises(InvalidVaultFormatError, match="Invalid magic header"):
            decrypt_vault(password, bytes(encrypted))

    def test_decrypt_fails_with_unsupported_version(self):
        password = "MasterPassword123!"
        encrypted = bytearray(encrypt_vault(password, b"Data"))

        # Set version to 99
        encrypted[4] = 99

        with pytest.raises(InvalidVaultFormatError, match="Unsupported vault format version"):
            decrypt_vault(password, bytes(encrypted))

    def test_decrypt_fails_with_truncated_payload(self):
        password = "MasterPassword123!"

        with pytest.raises(InvalidVaultFormatError, match="Payload too short"):
            decrypt_vault(password, b"short_data")

    def test_crypto_empty_password_or_type_errors(self):
        with pytest.raises(ValueError, match="Master password must not be empty"):
            encrypt_vault("", b"data")

        with pytest.raises(TypeError, match="raw_data must be bytes"):
            encrypt_vault("pass", "string_data")  # type: ignore

        with pytest.raises(ValueError, match="Master password must not be empty"):
            decrypt_vault("", b"payload")

        with pytest.raises(TypeError, match="encrypted_payload must be bytes"):
            decrypt_vault("pass", "not_bytes")  # type: ignore

