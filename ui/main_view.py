"""Main vault interface: account search, list, detail viewer, and clipboard lifecycle."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Dict, List, Optional
import webbrowser

from core.models import PasswordEntry
from storage.vault_manager import VaultManager
from ui.dialogs import EntryDialog
from ui.theme import (
    ACCENT_GREEN,
    ACCENT_GREEN_HOVER,
    ACCENT_PRIMARY,
    ACCENT_PRIMARY_HOVER,
    ACCENT_RED,
    ACCENT_RED_HOVER,
    ACCENT_SECONDARY,
    ACCENT_SECONDARY_HOVER,
    BG_DARKEST,
    BG_INPUT,
    BG_PRIMARY,
    BG_SECONDARY,
    BG_TERTIARY,
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
    FONT_SMALL_BOLD,
    FONT_SUBTITLE,
    FONT_TITLE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    create_button,
    create_entry,
)
from utils.clipboard import copy_with_autoclear, set_clipboard


class MainView(tk.Frame):
    """Main window displaying the unlocked vault credentials and detail panel."""

    def __init__(
        self,
        parent: tk.Widget,
        vault_manager: VaultManager,
        on_lock: Callable[[], None],
    ) -> None:
        super().__init__(parent, bg=BG_DARKEST)
        self.vault_manager = vault_manager
        self.on_lock = on_lock

        self.current_selected_entry: Optional[PasswordEntry] = None
        self.is_password_revealed: bool = False
        self._clipboard_timer_id: Optional[str] = None
        self._clipboard_countdown: int = 0

        self._build_ui()
        self._refresh_list()

    def _build_ui(self) -> None:
        """Constructs header bar and two-column split layout."""
        # =====================================================================
        # TOP TOOLBAR
        # =====================================================================
        top_bar = tk.Frame(self, bg=BG_SECONDARY, height=56, padx=16, pady=10)
        top_bar.pack(fill="x", side="top")

        # Search Bar
        search_frame = tk.Frame(top_bar, bg=BG_SECONDARY)
        search_frame.pack(side="left", fill="x", expand=True, padx=(0, 16))

        tk.Label(
            search_frame,
            text="🔍",
            font=FONT_BODY,
            bg=BG_SECONDARY,
            fg=TEXT_MUTED,
        ).pack(side="left", padx=(0, 6))

        self.search_entry = create_entry(search_frame, font=FONT_BODY)
        self.search_entry.pack(side="left", fill="x", expand=True, ipady=4)
        self.search_entry.bind("<KeyRelease>", lambda _: self._on_search_change())

        clear_btn = tk.Button(
            search_frame,
            text="✕",
            font=FONT_SMALL,
            bg=BG_INPUT,
            fg=TEXT_MUTED,
            activebackground=BG_INPUT,
            activeforeground=TEXT_PRIMARY,
            bd=0,
            cursor="hand2",
            padx=6,
            command=self._clear_search,
        )
        clear_btn.pack(side="left", padx=(2, 0))

        # + Nueva Entrada Button
        new_btn = create_button(
            top_bar,
            text="+ Nueva Entrada",
            bg_color=ACCENT_GREEN,
            hover_color=ACCENT_GREEN_HOVER,
            command=self._open_new_entry_dialog,
            padx=14,
            pady=6,
        )
        new_btn.pack(side="left", padx=(0, 16))

        # Clipboard Status Badge
        self.clipboard_status_label = tk.Label(
            top_bar,
            text="Portapapeles: inactivo",
            font=FONT_SMALL,
            bg=BG_SECONDARY,
            fg=TEXT_MUTED,
            padx=8,
        )
        self.clipboard_status_label.pack(side="left", padx=(0, 16))

        # Lock / Logout Button
        lock_btn = create_button(
            top_bar,
            text="🔒 Bloquear",
            bg_color=ACCENT_SECONDARY,
            hover_color=ACCENT_SECONDARY_HOVER,
            command=self._handle_lock,
            padx=12,
            pady=6,
        )
        lock_btn.pack(side="right")

        # =====================================================================
        # MAIN BODY (2 PANELS)
        # =====================================================================
        content_frame = tk.Frame(self, bg=BG_DARKEST)
        content_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # LEFT PANEL: Account List
        left_panel = tk.Frame(content_frame, bg=BG_PRIMARY, width=320)
        left_panel.pack(side="left", fill="both", expand=False, padx=(0, 10))
        left_panel.pack_propagate(False)

        # Left panel header
        list_header = tk.Frame(left_panel, bg=BG_PRIMARY, padx=12, pady=8)
        list_header.pack(fill="x")

        self.count_label = tk.Label(
            list_header,
            text="Cuentas guardadas (0)",
            font=FONT_SMALL_BOLD,
            bg=BG_PRIMARY,
            fg=TEXT_SECONDARY,
        )
        self.count_label.pack(side="left")

        # Treeview list container
        tree_container = tk.Frame(left_panel, bg=BG_PRIMARY)
        tree_container.pack(fill="both", expand=True)

        columns = ("title", "username")
        self.tree = ttk.Treeview(
            tree_container,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Treeview",
        )
        self.tree.heading("title", text="Título", anchor="w")
        self.tree.heading("username", text="Usuario", anchor="w")
        self.tree.column("title", width=140, anchor="w")
        self.tree.column("username", width=140, anchor="w")

        scrollbar = ttk.Scrollbar(
            tree_container,
            orient="vertical",
            command=self.tree.yview,
            style="Vertical.TScrollbar",
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_entry_selected)
        self.tree.bind("<Double-1>", lambda _: self._open_edit_entry_dialog())
        self.tree.bind("<Return>", lambda _: self._open_edit_entry_dialog())
        self.tree.bind("<Delete>", lambda _: self._delete_current_entry())

        # RIGHT PANEL: Detail Viewer
        self.right_panel = tk.Frame(content_frame, bg=BG_PRIMARY)
        self.right_panel.pack(side="right", fill="both", expand=True)

        self._render_empty_detail()

    # -------------------------------------------------------------------------
    # LIST & SEARCH MANAGEMENT
    # -------------------------------------------------------------------------

    def _refresh_list(self, query: str = "") -> None:
        """Reloads entries from vault and populates the Treeview."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        entries = self.vault_manager.search_entries(query)
        self.count_label.config(text=f"Cuentas guardadas ({len(entries)})")

        for entry in entries:
            self.tree.insert(
                "",
                "end",
                iid=entry.id,
                values=(entry.title, entry.username),
            )

        # Maintain or restore selection
        if self.current_selected_entry and self.tree.exists(self.current_selected_entry.id):
            self.tree.selection_set(self.current_selected_entry.id)
            self.tree.see(self.current_selected_entry.id)
        elif entries:
            # Select first entry
            first_id = entries[0].id
            self.tree.selection_set(first_id)
            self._select_entry_by_id(first_id)
        else:
            self.current_selected_entry = None
            self._render_empty_detail()

    def _on_search_change(self) -> None:
        """Filters list on keyboard input."""
        q = self.search_entry.get().strip()
        self._refresh_list(query=q)

    def _clear_search(self) -> None:
        """Clears the search input field."""
        self.search_entry.delete(0, tk.END)
        self._refresh_list()

    def _on_entry_selected(self, _: tk.Event) -> None:
        """Handles selection change in Treeview."""
        selected = self.tree.selection()
        if not selected:
            return
        entry_id = selected[0]
        self._select_entry_by_id(entry_id)

    def _select_entry_by_id(self, entry_id: str) -> None:
        """Loads and displays the entry details."""
        entry = self.vault_manager.get_entry(entry_id)
        if entry:
            self.current_selected_entry = entry
            self.is_password_revealed = False
            self._render_entry_detail(entry)

    # -------------------------------------------------------------------------
    # DETAIL VIEWER
    # -------------------------------------------------------------------------

    def _render_empty_detail(self) -> None:
        """Displays friendly empty state placeholder."""
        for child in self.right_panel.winfo_children():
            child.destroy()

        placeholder = tk.Frame(self.right_panel, bg=BG_PRIMARY)
        placeholder.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            placeholder,
            text="📂",
            font=("Segoe UI", 36),
            bg=BG_PRIMARY,
            fg=TEXT_MUTED,
        ).pack(pady=(0, 8))

        tk.Label(
            placeholder,
            text="Ninguna cuenta seleccionada",
            font=FONT_SUBTITLE,
            bg=BG_PRIMARY,
            fg=TEXT_SECONDARY,
        ).pack()

        tk.Label(
            placeholder,
            text="Selecciona una cuenta de la lista o crea una nueva con '+ Nueva Entrada'.",
            font=FONT_SMALL,
            bg=BG_PRIMARY,
            fg=TEXT_MUTED,
        ).pack(pady=(4, 0))

    def _render_entry_detail(self, entry: PasswordEntry) -> None:
        """Renders the comprehensive detail view for an entry."""
        for child in self.right_panel.winfo_children():
            child.destroy()

        container = tk.Frame(self.right_panel, bg=BG_SECONDARY, padx=24, pady=20)
        container.pack(fill="both", expand=True)

        # Header: Title & Action Buttons
        header = tk.Frame(container, bg=BG_SECONDARY)
        header.pack(fill="x", pady=(0, 20))

        title_label = tk.Label(
            header,
            text=entry.title,
            font=FONT_TITLE,
            bg=BG_SECONDARY,
            fg=TEXT_PRIMARY,
        )
        title_label.pack(side="left")

        # Edit & Delete Buttons
        del_btn = create_button(
            header,
            text="🗑️ Eliminar",
            bg_color=ACCENT_RED,
            hover_color=ACCENT_RED_HOVER,
            command=self._delete_current_entry,
            padx=10,
            pady=4,
        )
        del_btn.pack(side="right", padx=(8, 0))

        edit_btn = create_button(
            header,
            text="✏️ Editar",
            bg_color=ACCENT_SECONDARY,
            hover_color=ACCENT_SECONDARY_HOVER,
            command=self._open_edit_entry_dialog,
            padx=12,
            pady=4,
        )
        edit_btn.pack(side="right")

        # Content Box
        content = tk.Frame(container, bg=BG_SECONDARY)
        content.pack(fill="both", expand=True)

        # 1. Username Field
        self._create_detail_field(
            content,
            label="Usuario / Correo",
            value=entry.username,
            copy_action=lambda: self._copy_text(entry.username, "Usuario copiado"),
        )

        # 2. Password Field
        pwd_box = tk.Frame(content, bg=BG_SECONDARY)
        pwd_box.pack(fill="x", pady=(0, 14))

        tk.Label(
            pwd_box,
            text="Contraseña",
            font=FONT_SMALL_BOLD,
            bg=BG_SECONDARY,
            fg=TEXT_MUTED,
        ).pack(anchor="w")

        pwd_row = tk.Frame(pwd_box, bg=BG_INPUT, padx=8, pady=6)
        pwd_row.pack(fill="x", pady=(3, 0))

        self.pwd_display_label = tk.Label(
            pwd_row,
            text="••••••••••••",
            font=FONT_MONO_LARGE,
            bg=BG_INPUT,
            fg=TEXT_PRIMARY,
        )
        self.pwd_display_label.pack(side="left", fill="x", expand=True, anchor="w")

        self.reveal_btn = tk.Button(
            pwd_row,
            text="👁️ Revelar",
            font=FONT_SMALL,
            bg=ACCENT_SECONDARY,
            fg=TEXT_PRIMARY,
            activebackground=ACCENT_SECONDARY_HOVER,
            activeforeground=TEXT_PRIMARY,
            bd=0,
            cursor="hand2",
            padx=8,
            pady=3,
            command=self._toggle_reveal_password,
        )
        self.reveal_btn.pack(side="left", padx=(6, 4))

        copy_pwd_btn = create_button(
            pwd_row,
            text="📋 Copiar",
            bg_color=ACCENT_PRIMARY,
            hover_color=ACCENT_PRIMARY_HOVER,
            command=lambda: self._copy_password_with_autoclear(entry.password),
            padx=10,
            pady=3,
        )
        copy_pwd_btn.pack(side="left")

        # 3. URL Field
        if entry.url:
            self._create_detail_field(
                content,
                label="Sitio Web / URL",
                value=entry.url,
                copy_action=lambda: self._copy_text(entry.url, "URL copiada"),
                open_url_action=lambda: self._open_browser(entry.url),
            )

        # 4. Notes Field
        if entry.notes:
            notes_box = tk.Frame(content, bg=BG_SECONDARY)
            notes_box.pack(fill="both", expand=True, pady=(0, 14))

            tk.Label(
                notes_box,
                text="Notas",
                font=FONT_SMALL_BOLD,
                bg=BG_SECONDARY,
                fg=TEXT_MUTED,
            ).pack(anchor="w")

            notes_display = tk.Text(
                notes_box,
                bg=BG_INPUT,
                fg=TEXT_PRIMARY,
                font=FONT_BODY,
                relief="flat",
                bd=0,
                padx=8,
                pady=6,
                height=4,
                wrap="word",
            )
            notes_display.insert("1.0", entry.notes)
            notes_display.config(state="disabled")
            notes_display.pack(fill="both", expand=True, pady=(3, 0))

        # Metadata Footer
        footer = tk.Frame(container, bg=BG_SECONDARY)
        footer.pack(fill="x", side="bottom", pady=(12, 0))

        meta_text = f"Creado: {entry.created_at[:10]} | Modificado: {entry.updated_at[:10]}"
        tk.Label(
            footer,
            text=meta_text,
            font=FONT_SMALL,
            bg=BG_SECONDARY,
            fg=TEXT_MUTED,
        ).pack(side="left")

    def _create_detail_field(
        self,
        parent: tk.Frame,
        label: str,
        value: str,
        copy_action: Optional[Callable[[], None]] = None,
        open_url_action: Optional[Callable[[], None]] = None,
    ) -> None:
        """Helper to create consistent labeled detail field with action buttons."""
        box = tk.Frame(parent, bg=BG_SECONDARY)
        box.pack(fill="x", pady=(0, 14))

        tk.Label(box, text=label, font=FONT_SMALL_BOLD, bg=BG_SECONDARY, fg=TEXT_MUTED).pack(anchor="w")

        row = tk.Frame(box, bg=BG_INPUT, padx=8, pady=6)
        row.pack(fill="x", pady=(3, 0))

        val_label = tk.Label(
            row,
            text=value,
            font=FONT_BODY,
            bg=BG_INPUT,
            fg=TEXT_PRIMARY,
            anchor="w",
        )
        val_label.pack(side="left", fill="x", expand=True)

        if open_url_action:
            open_btn = tk.Button(
                row,
                text="🌐 Abrir",
                font=FONT_SMALL,
                bg=ACCENT_SECONDARY,
                fg=TEXT_PRIMARY,
                activebackground=ACCENT_SECONDARY_HOVER,
                activeforeground=TEXT_PRIMARY,
                bd=0,
                cursor="hand2",
                padx=8,
                pady=3,
                command=open_url_action,
            )
            open_btn.pack(side="left", padx=(0, 4))

        if copy_action:
            cp_btn = create_button(
                row,
                text="📋 Copiar",
                bg_color=ACCENT_SECONDARY,
                hover_color=ACCENT_SECONDARY_HOVER,
                command=copy_action,
                padx=10,
                pady=3,
            )
            cp_btn.pack(side="left")

    def _toggle_reveal_password(self) -> None:
        """Toggles between masked and revealed password text."""
        if not self.current_selected_entry:
            return

        if self.is_password_revealed:
            self.pwd_display_label.config(text="••••••••••••", font=FONT_MONO_LARGE)
            self.reveal_btn.config(text="👁️ Revelar")
            self.is_password_revealed = False
        else:
            self.pwd_display_label.config(
                text=self.current_selected_entry.password,
                font=FONT_MONO_LARGE,
            )
            self.reveal_btn.config(text="🔒 Ocultar")
            self.is_password_revealed = True

    def _open_browser(self, url: str) -> None:
        """Opens URL in system default browser safely."""
        target = url
        if not target.startswith(("http://", "https://")):
            target = "https://" + target
        webbrowser.open(target)

    # -------------------------------------------------------------------------
    # CLIPBOARD ACTIONS & TIMERS
    # -------------------------------------------------------------------------

    def _copy_text(self, text: str, feedback: str) -> None:
        """Copies plain text without autoclear timeout."""
        set_clipboard(text)
        self.clipboard_status_label.config(text=f"✓ {feedback}", fg=COLOR_EXCELLENT)
        self.after(2500, lambda: self.clipboard_status_label.config(text="Portapapeles: inactivo", fg=TEXT_MUTED))

    def _copy_password_with_autoclear(self, password: str) -> None:
        """Copies password and triggers delayed 20-second autoclear with countdown."""
        timeout_seconds = 20
        copy_with_autoclear(password, timeout_seconds=timeout_seconds)

        if self._clipboard_timer_id is not None:
            self.after_cancel(self._clipboard_timer_id)

        self._clipboard_countdown = timeout_seconds
        self._tick_clipboard_countdown()

    def _tick_clipboard_countdown(self) -> None:
        """Updates status badge every second until clipboard is wiped."""
        if self._clipboard_countdown > 0:
            self.clipboard_status_label.config(
                text=f"⏱️ Contraseña copiada (se limpiará en {self._clipboard_countdown}s)",
                fg=COLOR_FAIR,
            )
            self._clipboard_countdown -= 1
            self._clipboard_timer_id = self.after(1000, self._tick_clipboard_countdown)
        else:
            self.clipboard_status_label.config(
                text="✓ Portapapeles limpiado",
                fg=TEXT_MUTED,
            )
            self._clipboard_timer_id = self.after(
                2000,
                lambda: self.clipboard_status_label.config(text="Portapapeles: inactivo", fg=TEXT_MUTED),
            )

    # -------------------------------------------------------------------------
    # CRUD OPERATIONS VIA DIALOGS
    # -------------------------------------------------------------------------

    def _open_new_entry_dialog(self) -> None:
        """Opens modal dialog to add a new credential."""
        def handle_save(data: Dict[str, str]) -> None:
            new_entry = self.vault_manager.add_entry(
                title=data["title"],
                username=data["username"],
                password=data["password"],
                url=data.get("url", ""),
                notes=data.get("notes", ""),
            )
            self.current_selected_entry = new_entry
            self._refresh_list()

        EntryDialog(self.winfo_toplevel(), entry=None, on_save=handle_save)

    def _open_edit_entry_dialog(self) -> None:
        """Opens modal dialog to edit the currently selected credential."""
        if not self.current_selected_entry:
            return

        entry_to_edit = self.current_selected_entry

        def handle_save(data: Dict[str, str]) -> None:
            self.vault_manager.update_entry(
                entry_to_edit.id,
                title=data["title"],
                username=data["username"],
                password=data["password"],
                url=data.get("url", ""),
                notes=data.get("notes", ""),
            )
            updated = self.vault_manager.get_entry(entry_to_edit.id)
            if updated:
                self.current_selected_entry = updated
            self._refresh_list()
            if updated:
                self._render_entry_detail(updated)

        EntryDialog(self.winfo_toplevel(), entry=entry_to_edit, on_save=handle_save)

    def _delete_current_entry(self) -> None:
        """Prompts confirmation and removes the selected credential."""
        if not self.current_selected_entry:
            return

        entry = self.current_selected_entry
        confirm = messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Estás seguro de que deseas eliminar permanentemente la cuenta '{entry.title}'?",
            icon="warning",
            parent=self.winfo_toplevel(),
        )
        if confirm:
            self.vault_manager.delete_entry(entry.id)
            self.current_selected_entry = None
            self._refresh_list()
            self._render_empty_detail()

    def _handle_lock(self) -> None:
        """Locks the vault and notifies parent callback."""
        if self._clipboard_timer_id is not None:
            self.after_cancel(self._clipboard_timer_id)
        self.vault_manager.lock_vault()
        self.on_lock()

