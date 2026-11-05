"""Login and vault initialization view."""

from __future__ import annotations

import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

from core.generator import calculate_entropy
from storage.vault_manager import (
    InvalidCredentialsError,
    VaultAlreadyExistsError,
    VaultManager,
    VaultNotFoundError,
    VaultTamperedError,
)
from ui.theme import (
    ACCENT_GREEN,
    ACCENT_GREEN_HOVER,
    ACCENT_PRIMARY,
    ACCENT_PRIMARY_HOVER,
    ACCENT_RED,
    ACCENT_SECONDARY,
    ACCENT_SECONDARY_HOVER,
    BG_DARKEST,
    BG_PRIMARY,
    BG_SECONDARY,
    BORDER_COLOR,
    COLOR_EXCELLENT,
    COLOR_FAIR,
    COLOR_GOOD,
    COLOR_WEAK,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    create_button,
    create_entry,
)

DEFAULT_VAULT_FILE = "vault.enc"


class LoginView(tk.Frame):
    """View handling vault unlock and new vault setup."""

    def __init__(
        self,
        parent: tk.Widget,
        vault_manager: VaultManager,
        on_unlocked: Callable[[VaultManager], None],
        default_vault_path: str = DEFAULT_VAULT_FILE,
    ) -> None:
        super().__init__(parent, bg=BG_DARKEST)
        self.vault_manager = vault_manager
        self.on_unlocked = on_unlocked
        self.vault_path: Path = Path(default_vault_path).resolve()

        self.mode: str = "LOGIN" if self.vault_path.exists() else "SETUP"

        self._build_ui()

    def _build_ui(self) -> None:
        """Constructs the centered card layout."""
        for child in self.winfo_children():
            child.destroy()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Centered card
        card = tk.Frame(
            self,
            bg=BG_SECONDARY,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=32,
            pady=32,
        )
        card.grid(row=0, column=0)

        # Branding Header
        header_frame = tk.Frame(card, bg=BG_SECONDARY)
        header_frame.pack(fill="x", pady=(0, 20))

        logo_label = tk.Label(
            header_frame,
            text="🔐",
            font=("Segoe UI", 32),
            bg=BG_SECONDARY,
            fg=TEXT_PRIMARY,
        )
        logo_label.pack()

        app_title = tk.Label(
            header_frame,
            text="Zero-Knowledge Vault",
            font=FONT_TITLE,
            bg=BG_SECONDARY,
            fg=TEXT_PRIMARY,
        )
        app_title.pack(pady=(4, 2))

        app_subtitle = tk.Label(
            header_frame,
            text="Gestor local de contraseñas con cifrado autenticado",
            font=FONT_SMALL,
            bg=BG_SECONDARY,
            fg=TEXT_MUTED,
        )
        app_subtitle.pack()

        # Path status indicator
        path_box = tk.Frame(card, bg=BG_PRIMARY, padx=10, pady=6)
        path_box.pack(fill="x", pady=(0, 16))

        tk.Label(
            path_box,
            text="Archivo de bóveda:",
            font=FONT_SMALL,
            bg=BG_PRIMARY,
            fg=TEXT_MUTED,
        ).pack(anchor="w")

        path_row = tk.Frame(path_box, bg=BG_PRIMARY)
        path_row.pack(fill="x", pady=(2, 0))

        self.path_label = tk.Label(
            path_row,
            text=self._format_path(self.vault_path),
            font=FONT_SMALL,
            bg=BG_PRIMARY,
            fg=TEXT_SECONDARY,
            anchor="w",
        )
        self.path_label.pack(side="left", fill="x", expand=True)

        change_path_btn = tk.Button(
            path_row,
            text="Examinar...",
            font=FONT_SMALL,
            bg=ACCENT_SECONDARY,
            fg=TEXT_PRIMARY,
            activebackground=ACCENT_SECONDARY_HOVER,
            activeforeground=TEXT_PRIMARY,
            bd=0,
            cursor="hand2",
            padx=6,
            pady=2,
            command=self._browse_vault_file,
        )
        change_path_btn.pack(side="right")

        # Dynamic Section: Login vs Setup
        if self.mode == "LOGIN":
            self._render_login_form(card)
        else:
            self._render_setup_form(card)

    def _format_path(self, path: Path) -> str:
        """Formats long file paths cleanly for the header."""
        path_str = str(path)
        if len(path_str) > 38:
            return "..." + path_str[-35:]
        return path_str

    def _browse_vault_file(self) -> None:
        """Allows opening or choosing a different vault file location."""
        if self.mode == "LOGIN":
            selected = filedialog.askopenfilename(
                title="Seleccionar archivo de bóveda",
                filetypes=[("Archivos de Bóveda", "*.enc *.vault"), ("Todos los archivos", "*.*")],
            )
        else:
            selected = filedialog.asksaveasfilename(
                title="Ubicación de la nueva bóveda",
                initialfile="vault.enc",
                filetypes=[("Archivos de Bóveda", "*.enc *.vault"), ("Todos los archivos", "*.*")],
            )

        if selected:
            self.vault_path = Path(selected).resolve()
            self.mode = "LOGIN" if self.vault_path.exists() else "SETUP"
            self._build_ui()

    # -------------------------------------------------------------------------
    # LOGIN MODE
    # -------------------------------------------------------------------------

    def _render_login_form(self, container: tk.Frame) -> None:
        """Renders password entry and unlock controls."""
        form = tk.Frame(container, bg=BG_SECONDARY)
        form.pack(fill="x")

        tk.Label(
            form,
            text="Contraseña Maestra",
            font=FONT_SUBTITLE,
            bg=BG_SECONDARY,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 6))

        self.login_pwd_entry = create_entry(form, show="•", width=34)
        self.login_pwd_entry.pack(fill="x", ipady=5)
        self.login_pwd_entry.focus_set()
        self.login_pwd_entry.bind("<Return>", lambda _: self._handle_unlock())

        # Error notification label
        self.error_label = tk.Label(
            form,
            text="",
            font=FONT_SMALL,
            bg=BG_SECONDARY,
            fg=ACCENT_RED,
            wraplength=280,
            justify="left",
        )
        self.error_label.pack(fill="x", pady=(6, 0))

        # Unlock Button
        unlock_btn = create_button(
            form,
            text="🔓 Desbloquear Bóveda",
            bg_color=ACCENT_PRIMARY,
            hover_color=ACCENT_PRIMARY_HOVER,
            command=self._handle_unlock,
            pady=8,
        )
        unlock_btn.pack(fill="x", pady=(14, 8))

        # Switch to create new vault
        switch_btn = tk.Button(
            form,
            text="¿Quieres crear una nueva bóveda?",
            font=FONT_SMALL,
            bg=BG_SECONDARY,
            fg=TEXT_MUTED,
            activebackground=BG_SECONDARY,
            activeforeground=TEXT_SECONDARY,
            bd=0,
            cursor="hand2",
            command=self._switch_to_setup,
        )
        switch_btn.pack(pady=(4, 0))

    def _handle_unlock(self) -> None:
        """Attempts to unlock vault with entered password."""
        password = self.login_pwd_entry.get()
        if not password:
            self.error_label.config(text="Por favor ingresa la contraseña maestra.")
            return

        self.error_label.config(text="")
        try:
            self.vault_manager.unlock_vault(self.vault_path, password)
            self.on_unlocked(self.vault_manager)
        except InvalidCredentialsError:
            self.error_label.config(text="Contraseña incorrecta o datos alterados.")
            self.login_pwd_entry.selection_range(0, tk.END)
        except (VaultNotFoundError, VaultTamperedError) as exc:
            self.error_label.config(text=str(exc))
        except Exception as exc:
            self.error_label.config(text=f"Error inesperado: {exc}")

    def _switch_to_setup(self) -> None:
        """Switches view to vault creation mode."""
        suggested = self.vault_path.parent / "nueva_boveda.enc"
        self.vault_path = suggested
        self.mode = "SETUP"
        self._build_ui()

    # -------------------------------------------------------------------------
    # SETUP MODE (Crear nueva bóveda)
    # -------------------------------------------------------------------------

    def _render_setup_form(self, container: tk.Frame) -> None:
        """Renders vault setup assistant with real-time strength meter."""
        form = tk.Frame(container, bg=BG_SECONDARY)
        form.pack(fill="x")

        tk.Label(
            form,
            text="Configurar Nueva Bóveda",
            font=FONT_SUBTITLE,
            bg=BG_SECONDARY,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 4))

        tk.Label(
            form,
            text="Define tu contraseña maestra. Nunca se almacena en disco.",
            font=FONT_SMALL,
            bg=BG_SECONDARY,
            fg=TEXT_MUTED,
        ).pack(anchor="w", pady=(0, 12))

        # Password 1
        tk.Label(
            form,
            text="Nueva Contraseña Maestra",
            font=FONT_SMALL,
            bg=BG_SECONDARY,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w")

        self.setup_pwd_entry = create_entry(form, show="•", width=34)
        self.setup_pwd_entry.pack(fill="x", ipady=5, pady=(2, 6))
        self.setup_pwd_entry.focus_set()
        self.setup_pwd_entry.bind("<KeyRelease>", self._on_password_change)

        # Real-time entropy and strength bar
        meter_frame = tk.Frame(form, bg=BG_SECONDARY)
        meter_frame.pack(fill="x", pady=(0, 10))

        self.strength_canvas = tk.Canvas(
            meter_frame,
            height=4,
            bg=BORDER_COLOR,
            highlightthickness=0,
            bd=0,
        )
        self.strength_canvas.pack(fill="x", pady=(2, 4))

        self.strength_label = tk.Label(
            meter_frame,
            text="Fuerza: Sin ingresar",
            font=FONT_SMALL,
            bg=BG_SECONDARY,
            fg=TEXT_MUTED,
        )
        self.strength_label.pack(anchor="w")

        # Password 2 (Confirm)
        tk.Label(
            form,
            text="Confirmar Contraseña",
            font=FONT_SMALL,
            bg=BG_SECONDARY,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w")

        self.setup_confirm_entry = create_entry(form, show="•", width=34)
        self.setup_confirm_entry.pack(fill="x", ipady=5, pady=(2, 4))
        self.setup_confirm_entry.bind("<Return>", lambda _: self._handle_create_vault())

        # Error / Validation Label
        self.setup_error_label = tk.Label(
            form,
            text="",
            font=FONT_SMALL,
            bg=BG_SECONDARY,
            fg=ACCENT_RED,
            wraplength=280,
            justify="left",
        )
        self.setup_error_label.pack(fill="x", pady=(4, 0))

        # Create Button
        create_btn = create_button(
            form,
            text="✨ Crear Bóveda Segura",
            bg_color=ACCENT_GREEN,
            hover_color=ACCENT_GREEN_HOVER,
            command=self._handle_create_vault,
            pady=8,
        )
        create_btn.pack(fill="x", pady=(12, 8))

        # Back to unlock if existing file chosen
        if Path(DEFAULT_VAULT_FILE).resolve().exists():
            back_btn = tk.Button(
                form,
                text="Volver a bóveda existente",
                font=FONT_SMALL,
                bg=BG_SECONDARY,
                fg=TEXT_MUTED,
                activebackground=BG_SECONDARY,
                activeforeground=TEXT_SECONDARY,
                bd=0,
                cursor="hand2",
                command=self._switch_to_login,
            )
            back_btn.pack(pady=(2, 0))

    def _on_password_change(self, _: tk.Event) -> None:
        """Updates strength bar and entropy indicators live on key release."""
        pwd = self.setup_pwd_entry.get()
        if not pwd:
            self.strength_canvas.delete("all")
            self.strength_label.config(text="Fuerza: Sin ingresar", fg=TEXT_MUTED)
            return

        entropy = calculate_entropy(pwd)
        width = self.strength_canvas.winfo_width()
        if width <= 1:
            width = 280

        # Determine tier and color
        if entropy < 50:
            tier = "Débil"
            color = COLOR_WEAK
            ratio = min(1.0, max(0.15, entropy / 50 * 0.33))
        elif entropy < 75:
            tier = "Buena"
            color = COLOR_FAIR
            ratio = 0.33 + (entropy - 50) / 25 * 0.33
        elif entropy < 100:
            tier = "Muy Buena"
            color = COLOR_GOOD
            ratio = 0.66 + (entropy - 75) / 25 * 0.25
        else:
            tier = "Excelente"
            color = COLOR_EXCELLENT
            ratio = 1.0

        self.strength_canvas.delete("all")
        bar_w = int(width * ratio)
        self.strength_canvas.create_rectangle(0, 0, bar_w, 4, fill=color, outline="")

        self.strength_label.config(
            text=f"Fuerza: {tier} ({entropy:.1f} bits de entropía)",
            fg=color,
        )

    def _handle_create_vault(self) -> None:
        """Validates passwords and initializes new encrypted vault."""
        p1 = self.setup_pwd_entry.get()
        p2 = self.setup_confirm_entry.get()

        if not p1:
            self.setup_error_label.config(text="La contraseña maestra no puede estar vacía.")
            return

        if len(p1) < 8:
            self.setup_error_label.config(text="Recomendamos al menos 8 caracteres para la contraseña maestra.")
            return

        if p1 != p2:
            self.setup_error_label.config(text="Las contraseñas no coinciden.")
            return

        self.setup_error_label.config(text="")
        try:
            self.vault_manager.create_vault(self.vault_path, p1, overwrite=True)
            self.on_unlocked(self.vault_manager)
        except Exception as exc:
            self.setup_error_label.config(text=f"Error creando bóveda: {exc}")

    def _switch_to_login(self) -> None:
        """Switches back to login view for existing default vault."""
        self.vault_path = Path(DEFAULT_VAULT_FILE).resolve()
        self.mode = "LOGIN"
        self._build_ui()

