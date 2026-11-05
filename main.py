"""Application entry point orchestrating window lifecycle, view transitions, and clean shutdown."""

from __future__ import annotations

import sys
import tkinter as tk
from typing import Optional

from storage.vault_manager import VaultManager
from ui.login_view import LoginView
from ui.main_view import MainView
from ui.theme import BG_DARKEST, apply_theme
from utils.clipboard import clear_clipboard


class Application:
    """Main application controller managing views and vault lifecycle."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Zero-Knowledge Password Manager")
        self.root.geometry("1020x660")
        self.root.minsize(860, 540)
        self.root.configure(bg=BG_DARKEST)

        # Apply global dark styling
        apply_theme(self.root)

        self.vault_manager = VaultManager()
        self.current_view: Optional[tk.Frame] = None

        # Clean exit protocol on window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Start with Login/Unlock view
        self.show_login_view()

    def _clear_current_view(self) -> None:
        """Destroys active view frame before transitioning."""
        if self.current_view is not None:
            self.current_view.destroy()
            self.current_view = None

    def show_login_view(self) -> None:
        """Mounts the login / vault unlock view."""
        self._clear_current_view()
        self.current_view = LoginView(
            self.root,
            vault_manager=self.vault_manager,
            on_unlocked=self.show_main_view,
        )
        self.current_view.pack(fill="both", expand=True)

    def show_main_view(self, vault_manager: VaultManager) -> None:
        """Mounts the main vault credentials view."""
        self._clear_current_view()
        self.current_view = MainView(
            self.root,
            vault_manager=vault_manager,
            on_lock=self.show_login_view,
        )
        self.current_view.pack(fill="both", expand=True)

    def on_close(self) -> None:
        """Ensures safe cleanup: locks vault and clears memory before termination."""
        try:
            if self.vault_manager.is_unlocked:
                self.vault_manager.lock_vault()
            clear_clipboard()
        except Exception:
            pass
        finally:
            self.root.destroy()


def main() -> None:
    """Bootstrap and run the desktop application."""
    root = tk.Tk()
    app = Application(root)
    root.mainloop()


if __name__ == "__main__":
    main()
