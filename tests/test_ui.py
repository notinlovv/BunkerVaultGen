"""Unit tests for UI theme, layout constants, and interface configurations."""

import re
import pytest

from ui.theme import (
    ACCENT_GREEN,
    ACCENT_PRIMARY,
    ACCENT_RED,
    ACCENT_SECONDARY,
    BG_DARKEST,
    BG_INPUT,
    BG_PRIMARY,
    BG_SECONDARY,
    COLOR_EXCELLENT,
    COLOR_FAIR,
    COLOR_GOOD,
    COLOR_WEAK,
    FONT_BODY,
    FONT_MONO,
    FONT_TITLE,
)
from ui.login_view import DEFAULT_VAULT_FILE


class TestUITheme:
    """Verifies that the dark theme palette is consistent and uses valid hex colors."""

    def test_hex_colors_are_valid(self):
        hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
        colors = [
            BG_DARKEST,
            BG_PRIMARY,
            BG_SECONDARY,
            BG_INPUT,
            ACCENT_PRIMARY,
            ACCENT_GREEN,
            ACCENT_RED,
            ACCENT_SECONDARY,
            COLOR_WEAK,
            COLOR_FAIR,
            COLOR_GOOD,
            COLOR_EXCELLENT,
        ]
        for color in colors:
            assert hex_pattern.match(color) is not None, f"Invalid hex color: {color}"

    def test_fonts_are_tuples(self):
        assert isinstance(FONT_TITLE, tuple)
        assert isinstance(FONT_BODY, tuple)
        assert isinstance(FONT_MONO, tuple)

    def test_default_vault_file(self):
        assert DEFAULT_VAULT_FILE == "vault.enc"

