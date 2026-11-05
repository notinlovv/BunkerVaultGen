"""Dialogs for adding/editing password entries with an integrated secure generator."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Dict, Optional

from core.generator import (
    calculate_entropy,
    generate_password,
)
from core.models import PasswordEntry
from ui.theme import (
    ACCENT_GREEN,
    ACCENT_GREEN_HOVER,
    ACCENT_PRIMARY,
    ACCENT_PRIMARY_HOVER,
    ACCENT_SECONDARY,
    ACCENT_SECONDARY_HOVER,
    BG_DARKEST,
    BG_INPUT,
    BG_PRIMARY,
    BG_SECONDARY,
    BORDER_COLOR,
    COLOR_EXCELLENT,
    COLOR_FAIR,
    COLOR_GOOD,
    COLOR_WEAK,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_MONO,
    FONT_MONO_LARGE,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    create_button,
    create_entry,
)


class EntryDialog(tk.Toplevel):
    """Modal dialog for creating or updating a vault credential entry."""

    def __init__(
        self,
        parent: tk.Widget,
        entry: Optional[PasswordEntry] = None,
        on_save: Optional[Callable[[Dict[str, str]], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.entry = entry
        self.on_save = on_save
        self.is_edit = entry is not None

        self.title("Editar Entrada" if self.is_edit else "Nueva Entrada")
        self.configure(bg=BG_PRIMARY)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Generator control variables
        self.gen_length_var = tk.IntVar(value=16)
        self.gen_upper_var = tk.BooleanVar(value=True)
        self.gen_lower_var = tk.BooleanVar(value=True)
        self.gen_digits_var = tk.BooleanVar(value=True)
        self.gen_symbols_var = tk.BooleanVar(value=True)
        self.gen_no_ambig_var = tk.BooleanVar(value=False)
        self.gen_password_str = tk.StringVar(value="")
        self.show_password_var = tk.BooleanVar(value=False)

        self._build_ui()
        self._center_window(parent)

    def _center_window(self, parent: tk.Widget) -> None:
        """Centers the dialog over the parent window."""
        self.update_idletasks()
        w = 540
        h = self.winfo_reqheight() + 20
        px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{max(0, px)}+{max(0, py)}")

    def _build_ui(self) -> None:
        """Builds modal form and generator panel."""
        container = tk.Frame(self, bg=BG_PRIMARY, padx=24, pady=20)
        container.pack(fill="both", expand=True)

        # Header Title
        title_text = "Editar Credencial" if self.is_edit else "Nueva Credencial"
        tk.Label(
            container,
            text=title_text,
            font=FONT_TITLE,
            bg=BG_PRIMARY,
            fg=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 16))

        # Form Fields Frame
        form = tk.Frame(container, bg=BG_PRIMARY)
        form.pack(fill="x", pady=(0, 10))

        # Title
        tk.Label(form, text="Título *", font=FONT_BODY_BOLD, bg=BG_PRIMARY, fg=TEXT_PRIMARY).pack(anchor="w")
        self.title_entry = create_entry(form)
        self.title_entry.pack(fill="x", ipady=4, pady=(2, 10))
        if self.entry:
            self.title_entry.insert(0, self.entry.title)

        # Username
        tk.Label(form, text="Usuario / Correo *", font=FONT_BODY_BOLD, bg=BG_PRIMARY, fg=TEXT_PRIMARY).pack(anchor="w")
        self.username_entry = create_entry(form)
        self.username_entry.pack(fill="x", ipady=4, pady=(2, 10))
        if self.entry:
            self.username_entry.insert(0, self.entry.username)

        # Password + Inline actions
        pwd_label_row = tk.Frame(form, bg=BG_PRIMARY)
        pwd_label_row.pack(fill="x")
        tk.Label(pwd_label_row, text="Contraseña *", font=FONT_BODY_BOLD, bg=BG_PRIMARY, fg=TEXT_PRIMARY).pack(side="left")

        pwd_row = tk.Frame(form, bg=BG_PRIMARY)
        pwd_row.pack(fill="x", pady=(2, 10))

        self.pwd_entry = create_entry(pwd_row, show="•")
        self.pwd_entry.pack(side="left", fill="x", expand=True, ipady=4)
        if self.entry:
            self.pwd_entry.insert(0, self.entry.password)

        self.toggle_pwd_btn = tk.Button(
            pwd_row,
            text="👁️",
            font=FONT_SMALL,
            bg=ACCENT_SECONDARY,
            fg=TEXT_PRIMARY,
            activebackground=ACCENT_SECONDARY_HOVER,
            activeforeground=TEXT_PRIMARY,
            bd=0,
            cursor="hand2",
            padx=8,
            pady=4,
            command=self._toggle_password_visibility,
        )
        self.toggle_pwd_btn.pack(side="left", padx=(6, 4))

        self.gen_toggle_btn = tk.Button(
            pwd_row,
            text="⚡ Generador",
            font=FONT_BODY_BOLD,
            bg=ACCENT_PRIMARY,
            fg=TEXT_PRIMARY,
            activebackground=ACCENT_PRIMARY_HOVER,
            activeforeground=TEXT_PRIMARY,
            bd=0,
            cursor="hand2",
            padx=10,
            pady=4,
            command=self._toggle_generator_panel,
        )
        self.gen_toggle_btn.pack(side="left")

        # Integrated Generator Panel (Collapsible)
        self.gen_frame = tk.Frame(
            container,
            bg=BG_SECONDARY,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=14,
            pady=12,
        )
        self._build_generator_controls(self.gen_frame)

        # URL
        tk.Label(form, text="Sitio Web / URL", font=FONT_BODY_BOLD, bg=BG_PRIMARY, fg=TEXT_PRIMARY).pack(anchor="w")
        self.url_entry = create_entry(form)
        self.url_entry.pack(fill="x", ipady=4, pady=(2, 10))
        if self.entry:
            self.url_entry.insert(0, self.entry.url)

        # Notes
        tk.Label(form, text="Notas adicionales", font=FONT_BODY_BOLD, bg=BG_PRIMARY, fg=TEXT_PRIMARY).pack(anchor="w")
        self.notes_text = tk.Text(
            form,
            height=3,
            bg=BG_INPUT,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            font=FONT_BODY,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
            highlightcolor=ACCENT_PRIMARY,
            bd=0,
            padx=6,
            pady=4,
        )
        self.notes_text.pack(fill="x", pady=(2, 14))
        if self.entry and self.entry.notes:
            self.notes_text.insert("1.0", self.entry.notes)

        # Bottom Action Buttons
        btn_bar = tk.Frame(container, bg=BG_PRIMARY)
        btn_bar.pack(fill="x", pady=(6, 0))

        cancel_btn = create_button(
            btn_bar,
            text="Cancelar",
            bg_color=ACCENT_SECONDARY,
            hover_color=ACCENT_SECONDARY_HOVER,
            command=self.destroy,
            width=10,
        )
        cancel_btn.pack(side="right", padx=(8, 0))

        save_btn = create_button(
            btn_bar,
            text="Guardar",
            bg_color=ACCENT_GREEN,
            hover_color=ACCENT_GREEN_HOVER,
            command=self._handle_save,
            width=12,
        )
        save_btn.pack(side="right")

        self.title_entry.focus_set()

    def _build_generator_controls(self, frame: tk.Frame) -> None:
        """Constructs generator controls, sliders, checkboxes, and entropy bar."""
        top_row = tk.Frame(frame, bg=BG_SECONDARY)
        top_row.pack(fill="x", pady=(0, 6))

        tk.Label(
            top_row,
            text="Generador Criptográfico Seguro",
            font=FONT_SUBTITLE,
            bg=BG_SECONDARY,
            fg=TEXT_PRIMARY,
        ).pack(side="left")

        # Slider length
        slider_row = tk.Frame(frame, bg=BG_SECONDARY)
        slider_row.pack(fill="x", pady=(2, 6))

        self.length_label = tk.Label(
            slider_row,
            text="Longitud: 16",
            font=FONT_BODY_BOLD,
            bg=BG_SECONDARY,
            fg=TEXT_PRIMARY,
            width=14,
            anchor="w",
        )
        self.length_label.pack(side="left")

        length_scale = ttk.Scale(
            slider_row,
            from_=8,
            to=64,
            variable=self.gen_length_var,
            orient="horizontal",
            command=self._on_scale_change,
        )
        length_scale.pack(side="left", fill="x", expand=True, padx=6)

        # Checkboxes
        chk_row1 = tk.Frame(frame, bg=BG_SECONDARY)
        chk_row1.pack(fill="x", pady=(2, 2))

        ttk.Checkbutton(
            chk_row1,
            text="Mayúsculas (A-Z)",
            variable=self.gen_upper_var,
            command=self._regenerate_password,
        ).pack(side="left", padx=(0, 10))

        ttk.Checkbutton(
            chk_row1,
            text="Minúsculas (a-z)",
            variable=self.gen_lower_var,
            command=self._regenerate_password,
        ).pack(side="left", padx=(0, 10))

        ttk.Checkbutton(
            chk_row1,
            text="Números (0-9)",
            variable=self.gen_digits_var,
            command=self._regenerate_password,
        ).pack(side="left")

        chk_row2 = tk.Frame(frame, bg=BG_SECONDARY)
        chk_row2.pack(fill="x", pady=(2, 6))

        ttk.Checkbutton(
            chk_row2,
            text="Símbolos (!@#$)",
            variable=self.gen_symbols_var,
            command=self._regenerate_password,
        ).pack(side="left", padx=(0, 10))

        ttk.Checkbutton(
            chk_row2,
            text="Excluir ambiguos (1, l, I, 0, O)",
            variable=self.gen_no_ambig_var,
            command=self._regenerate_password,
        ).pack(side="left")

        # Preview box
        preview_box = tk.Frame(
            frame,
            bg=BG_INPUT,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=8,
            pady=6,
        )
        preview_box.pack(fill="x", pady=(4, 6))

        self.preview_label = tk.Label(
            preview_box,
            textvariable=self.gen_password_str,
            font=FONT_MONO_LARGE,
            bg=BG_INPUT,
            fg=TEXT_PRIMARY,
            anchor="w",
        )
        self.preview_label.pack(side="left", fill="x", expand=True)

        regen_btn = tk.Button(
            preview_box,
            text="🔄",
            font=FONT_SMALL,
            bg=ACCENT_SECONDARY,
            fg=TEXT_PRIMARY,
            activebackground=ACCENT_SECONDARY_HOVER,
            activeforeground=TEXT_PRIMARY,
            bd=0,
            cursor="hand2",
            padx=6,
            pady=2,
            command=self._regenerate_password,
        )
        regen_btn.pack(side="right")

        # Entropy Info
        entropy_row = tk.Frame(frame, bg=BG_SECONDARY)
        entropy_row.pack(fill="x", pady=(0, 8))

        self.entropy_label = tk.Label(
            entropy_row,
            text="Entropía: 0 bits",
            font=FONT_SMALL,
            bg=BG_SECONDARY,
            fg=COLOR_EXCELLENT,
        )
        self.entropy_label.pack(side="left")

        # Use Password button
        use_btn = create_button(
            frame,
            text="✓ Usar esta contraseña",
            bg_color=ACCENT_PRIMARY,
            hover_color=ACCENT_PRIMARY_HOVER,
            command=self._use_generated_password,
            pady=4,
        )
        use_btn.pack(fill="x")

    def _toggle_generator_panel(self) -> None:
        """Shows or hides the integrated generator frame."""
        if self.gen_frame.winfo_ismapped():
            self.gen_frame.pack_forget()
            self.gen_toggle_btn.config(text="⚡ Generador", bg=ACCENT_PRIMARY)
        else:
            self.gen_frame.pack(after=self.pwd_entry.master, fill="x", pady=(0, 12))
            self.gen_toggle_btn.config(text="▲ Ocultar", bg=ACCENT_SECONDARY)
            self._regenerate_password()

    def _on_scale_change(self, val: str) -> None:
        """Handles length slider updates."""
        length = int(float(val))
        self.gen_length_var.set(length)
        self.length_label.config(text=f"Longitud: {length}")
        self._regenerate_password()

    def _regenerate_password(self) -> None:
        """Regenerates password and updates entropy indicator."""
        try:
            pw = generate_password(
                length=self.gen_length_var.get(),
                use_upper=self.gen_upper_var.get(),
                use_lower=self.gen_lower_var.get(),
                use_digits=self.gen_digits_var.get(),
                use_symbols=self.gen_symbols_var.get(),
                exclude_ambiguous=self.gen_no_ambig_var.get(),
            )
            self.gen_password_str.set(pw)
            entropy = calculate_entropy(pw)

            if entropy < 50:
                tier = "Débil"
                color = COLOR_WEAK
            elif entropy < 75:
                tier = "Buena"
                color = COLOR_FAIR
            elif entropy < 100:
                tier = "Muy Buena"
                color = COLOR_GOOD
            else:
                tier = "Excelente"
                color = COLOR_EXCELLENT

            self.entropy_label.config(
                text=f"Entropía: {entropy:.1f} bits ({tier})",
                fg=color,
            )
        except ValueError:
            self.gen_password_str.set("[Selecciona al menos un set]")
            self.entropy_label.config(text="Entropía: 0 bits", fg=COLOR_WEAK)

    def _use_generated_password(self) -> None:
        """Applies generated password to the password form field."""
        pwd = self.gen_password_str.get()
        if pwd and not pwd.startswith("["):
            self.pwd_entry.delete(0, tk.END)
            self.pwd_entry.insert(0, pwd)
            self._toggle_generator_panel()

    def _toggle_password_visibility(self) -> None:
        """Toggles between masked bullets and plaintext in entry."""
        if self.show_password_var.get():
            self.pwd_entry.config(show="•")
            self.toggle_pwd_btn.config(text="👁️")
            self.show_password_var.set(False)
        else:
            self.pwd_entry.config(show="")
            self.toggle_pwd_btn.config(text="🔒")
            self.show_password_var.set(True)

    def _handle_save(self) -> None:
        """Validates input fields and triggers save callback."""
        title = self.title_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.pwd_entry.get()
        url = self.url_entry.get().strip()
        notes = self.notes_text.get("1.0", tk.END).strip()

        if not title:
            messagebox.showwarning("Campo requerido", "Por favor ingresa un título para la entrada.", parent=self)
            self.title_entry.focus_set()
            return

        if not username:
            messagebox.showwarning("Campo requerido", "Por favor ingresa el nombre de usuario o correo.", parent=self)
            self.username_entry.focus_set()
            return

        if not password:
            messagebox.showwarning("Campo requerido", "Por favor ingresa o genera una contraseña.", parent=self)
            self.pwd_entry.focus_set()
            return

        data: Dict[str, str] = {
            "title": title,
            "username": username,
            "password": password,
            "url": url,
            "notes": notes,
        }

        if self.on_save:
            self.on_save(data)

        self.destroy()

