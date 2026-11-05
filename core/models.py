"""Data models and serialization for the Zero-Knowledge password vault."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class PasswordEntry:
    """Represents a single credential record inside the vault."""

    title: str
    username: str
    password: str
    url: str = ""
    notes: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def update_password(self, new_password: str) -> None:
        """Updates the password and refreshes the updated_at timestamp."""
        self.password = new_password
        self.touch()

    def touch(self) -> None:
        """Refreshes the updated_at timestamp to current UTC time."""
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Serializes entry to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PasswordEntry:
        """Instantiates a PasswordEntry from a dictionary with validation."""
        required = ("title", "username", "password")
        for field_name in required:
            if field_name not in data:
                raise ValueError(f"Missing required field in PasswordEntry: '{field_name}'")

        return cls(
            id=str(data.get("id") or uuid.uuid4()),
            title=str(data["title"]),
            username=str(data["username"]),
            password=str(data["password"]),
            url=str(data.get("url", "")),
            notes=str(data.get("notes", "")),
            created_at=str(data.get("created_at") or datetime.now(timezone.utc).isoformat()),
            updated_at=str(data.get("updated_at") or datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class VaultData:
    """Represents the complete unencrypted vault dataset including metadata."""

    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    entries: List[PasswordEntry] = field(default_factory=list)

    def add_entry(self, entry: PasswordEntry) -> None:
        """Adds or updates a password entry in the vault."""
        for idx, existing in enumerate(self.entries):
            if existing.id == entry.id:
                self.entries[idx] = entry
                self.touch()
                return
        self.entries.append(entry)
        self.touch()

    def get_entry(self, entry_id: str) -> Optional[PasswordEntry]:
        """Retrieves an entry by its unique UUID string."""
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        return None

    def remove_entry(self, entry_id: str) -> bool:
        """Removes an entry by ID. Returns True if found and deleted, False otherwise."""
        for idx, entry in enumerate(self.entries):
            if entry.id == entry_id:
                del self.entries[idx]
                self.touch()
                return True
        return False

    def touch(self) -> None:
        """Refreshes the vault's updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the entire vault to a dictionary."""
        return {
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VaultData:
        """Instantiates a VaultData instance from a dictionary."""
        if not isinstance(data, dict):
            raise ValueError("VaultData payload must be a JSON dictionary.")

        version = int(data.get("version", 1))
        created_at = str(data.get("created_at") or datetime.now(timezone.utc).isoformat())
        updated_at = str(data.get("updated_at") or datetime.now(timezone.utc).isoformat())

        raw_entries = data.get("entries", [])
        if not isinstance(raw_entries, list):
            raise ValueError("'entries' field must be a list.")

        entries = [PasswordEntry.from_dict(item) for item in raw_entries]
        return cls(
            version=version,
            created_at=created_at,
            updated_at=updated_at,
            entries=entries,
        )

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serializes vault data to a JSON string in memory."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> VaultData:
        """Deserializes vault data from a JSON string in memory."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON string: {exc}") from exc
        return cls.from_dict(data)

