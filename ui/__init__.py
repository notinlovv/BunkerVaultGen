"""UI package for the Zero-Knowledge password manager desktop application."""

from ui.theme import apply_theme
from ui.login_view import LoginView
from ui.main_view import MainView
from ui.dialogs import EntryDialog

__all__ = [
    "apply_theme",
    "LoginView",
    "MainView",
    "EntryDialog",
]

