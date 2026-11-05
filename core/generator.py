"""Cryptographically secure password generation and entropy calculation."""

from __future__ import annotations

import math
import secrets
import string
from typing import List, Optional, Set

# Character pools
LOWERCASE: str = string.ascii_lowercase
UPPERCASE: str = string.ascii_uppercase
DIGITS: str = string.digits
SYMBOLS: str = "!@#$%^&*()-_=+[]{}|;:,.<>?"

# Visually ambiguous characters across fonts (i, l, 1, L, o, 0, O)
AMBIGUOUS_CHARS: Set[str] = set("iIlL1oO0")


def generate_password(
    length: int = 16,
    use_upper: bool = True,
    use_lower: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
    exclude_ambiguous: bool = False,
) -> str:
    """Generates a cryptographically secure password using secrets.

    Guarantees at least one character from each selected character set and
    performs a CSPRNG Fisher-Yates shuffle.

    Args:
        length: Desired length of the password (must be >= number of selected sets).
        use_upper: Include uppercase letters (A-Z).
        use_lower: Include lowercase letters (a-z).
        use_digits: Include numerical digits (0-9).
        use_symbols: Include special symbols.
        exclude_ambiguous: Exclude characters easily confused (e.g., 1, l, I, 0, O).

    Returns:
        Generated password string.

    Raises:
        ValueError: If no character sets are selected or length is too short.
    """
    def filter_pool(pool: str) -> str:
        if exclude_ambiguous:
            return "".join(c for c in pool if c not in AMBIGUOUS_CHARS)
        return pool

    selected_pools: List[str] = []
    if use_lower:
        pool = filter_pool(LOWERCASE)
        if pool:
            selected_pools.append(pool)
    if use_upper:
        pool = filter_pool(UPPERCASE)
        if pool:
            selected_pools.append(pool)
    if use_digits:
        pool = filter_pool(DIGITS)
        if pool:
            selected_pools.append(pool)
    if use_symbols:
        pool = filter_pool(SYMBOLS)
        if pool:
            selected_pools.append(pool)

    if not selected_pools:
        raise ValueError("At least one character set must be selected.")

    if length < len(selected_pools):
        raise ValueError(
            f"Password length ({length}) must be at least {len(selected_pools)} "
            "to guarantee one character from each selected character set."
        )

    # Guarantee at least one character from each selected pool
    password_chars: List[str] = [secrets.choice(pool) for pool in selected_pools]

    # Fill the remaining length from the combined pool
    combined_pool: str = "".join(selected_pools)
    remaining_count = length - len(password_chars)
    password_chars.extend(secrets.choice(combined_pool) for _ in range(remaining_count))

    # Cryptographically secure Fisher-Yates shuffle
    for i in range(len(password_chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        password_chars[i], password_chars[j] = password_chars[j], password_chars[i]

    return "".join(password_chars)


def calculate_entropy(password: str, pool_size: Optional[int] = None) -> float:
    """Calculates password entropy in bits using the keyspace formula E = L * log2(R).

    Args:
        password: The password string to evaluate.
        pool_size: Optional explicit pool size R. If None, pool size is computed
            based on character sets present in the password.

    Returns:
        Entropy in bits, rounded to two decimal places.
    """
    length = len(password)
    if length == 0:
        return 0.0

    if pool_size is not None:
        r = pool_size
    else:
        r = 0
        has_lower = any(c in LOWERCASE for c in password)
        has_upper = any(c in UPPERCASE for c in password)
        has_digits = any(c in DIGITS for c in password)
        # Check standard symbols / punctuation
        symbols_set = set(SYMBOLS) | set(string.punctuation)
        has_symbols = any(c in symbols_set for c in password)

        if has_lower:
            r += len(LOWERCASE)
        if has_upper:
            r += len(UPPERCASE)
        if has_digits:
            r += len(DIGITS)
        if has_symbols:
            r += len(symbols_set)

        # Account for unique characters outside standard pools (whitespace, unicode)
        accounted = set(LOWERCASE) | set(UPPERCASE) | set(DIGITS) | symbols_set
        extra = set(c for c in password if c not in accounted)
        r += len(extra)

    if r <= 1:
        return 0.0

    entropy = length * math.log2(r)
    return round(entropy, 2)

