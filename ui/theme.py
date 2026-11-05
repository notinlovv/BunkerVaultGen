"""Theme constants, color palette, typography, and widget styling for Tkinter/ttk."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Optional, Tuple

# Color Palette (Dark Hard / VS Code inspired sober palette)
BG_DARKEST: str = "#181818"       # Main window root background
BG_PRIMARY: str = "#1e1e1e"       # Main surface / panels
BG_SECONDARY: str = "#252526"     # Sidebar / Cards
BG_TERTIARY: str = "#2d2d30"      # Elevated surfaces
BG_INPUT: str = "#333333"         # Entry fields and inputs
BG_HOVER: str = "#3c3c3c"         # Subtle hover state
BG_SELECTED: str = "#094771"      # Active selection in lists
BORDER_COLOR: str = "#3e3e42"     # Subtle borders and dividers

TEXT_PRIMARY: str = "#f3f3f3"     # High-contrast primary text
TEXT_SECONDARY: str = "#cccccc"   # Secondary labels
TEXT_MUTED: str = "#858585"       # Placeholder and disabled text

# Accent colors
ACCENT_PRIMARY: str = "#0e639c"       # Primary action blue
ACCENT_PRIMARY_HOVER: str = "#1177bb"
ACCENT_GREEN: str = "#238636"         # Success / Add green
ACCENT_GREEN_HOVER: str = "#2ea043"
ACCENT_RED: str = "#da3633"           # Delete / Danger red
ACCENT_RED_HOVER: str = "#f85149"
ACCENT_SECONDARY: str = "#3c3c3c"     # Neutral action button
ACCENT_SECONDARY_HOVER: str = "#4a4a4a"

# Password Strength Colors
COLOR_WEAK: str = "#da3633"           # < 50 bits (Débil)
COLOR_FAIR: str = "#d29922"           # 50 - 75 bits (Buena)
COLOR_GOOD: str = "#238636"           # 75 - 100 bits (Muy Buena)
COLOR_EXCELLENT: str = "#2ea043"      # > 100 bits (Excelente)

# Typography
FONT_FAMILY: str = "Segoe UI"
FONT_TITLE: Tuple[str, int, str] = (FONT_FAMILY, 15, "bold")
FONT_SUBTITLE: Tuple[str, int, str] = (FONT_FAMILY, 11, "bold")
FONT_BODY: Tuple[str, int] = (FONT_FAMILY, 10)
FONT_BODY_BOLD: Tuple[str, int, str] = (FONT_FAMILY, 10, "bold")
FONT_SMALL: Tuple[str, int] = (FONT_FAMILY, 9)
FONT_SMALL_BOLD: Tuple[str, int, str] = (FONT_FAMILY, 9, "bold")
FONT_MONO: Tuple[str, int] = ("DejaVu Sans Mono", 10)
FONT_MONO_LARGE: Tuple[str, int, str] = ("DejaVu Sans Mono", 12, "bold")


def apply_theme(root: tk.Tk) -> None:
    """Configures root background, options database, and ttk styles."""
    root.configure(bg=BG_DARKEST)

    # General options database styling
    root.option_add("*Background", BG_PRIMARY)
    root.option_add("*Foreground", TEXT_PRIMARY)
    root.option_add("*Font", FONT_BODY)

    style = ttk.Style(root)
    # Use 'clam' or 'alt' as modern flat base theme
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # TFrame
    style.configure("TFrame", background=BG_PRIMARY)
    style.configure("Dark.TFrame", background=BG_DARKEST)
    style.configure("Card.TFrame", background=BG_SECONDARY, relief="flat")

    # TLabel
    style.configure("TLabel", background=BG_PRIMARY, foreground=TEXT_PRIMARY, font=FONT_BODY)
    style.configure("Title.TLabel", font=FONT_TITLE, foreground=TEXT_PRIMARY, background=BG_PRIMARY)
    style.configure("Subtitle.TLabel", font=FONT_SUBTITLE, foreground=TEXT_SECONDARY, background=BG_PRIMARY)
    style.configure("Muted.TLabel", font=FONT_SMALL, foreground=TEXT_MUTED, background=BG_PRIMARY)
    style.configure("Card.TLabel", background=BG_SECONDARY, foreground=TEXT_PRIMARY)
    style.configure("CardMuted.TLabel", background=BG_SECONDARY, foreground=TEXT_MUTED, font=FONT_SMALL)

    # Treeview (Account List)
    style.configure(
        "Treeview",
        background=BG_SECONDARY,
        foreground=TEXT_PRIMARY,
        fieldbackground=BG_SECONDARY,
        font=FONT_BODY,
        rowheight=36,
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        background=BG_TERTIARY,
        foreground=TEXT_SECONDARY,
        font=FONT_SMALL_BOLD,
        borderwidth=0,
        relief="flat",
        padding=(8, 6),
    )
    style.map(
        "Treeview",
        background=[("selected", BG_SELECTED)],
        foreground=[("selected", TEXT_PRIMARY)],
    )

    # Scrollbar
    style.configure(
        "Vertical.TScrollbar",
        background=BG_TERTIARY,
        troughcolor=BG_SECONDARY,
        borderwidth=0,
        arrowsize=12,
        relief="flat",
    )
    style.map("Vertical.TScrollbar", background=[("active", BG_HOVER)])

    # Progressbar (Entropy Bar)
    style.configure(
        "Horizontal.TProgressbar",
        troughcolor=BG_INPUT,
        background=ACCENT_GREEN,
        borderwidth=0,
        thickness=6,
    )

    # Scale / Slider
    style.configure(
        "Horizontal.TScale",
        background=BG_PRIMARY,
        troughcolor=BG_INPUT,
        sliderrelief="flat",
        sliderlength=16,
    )

    # Checkbuttons
    style.configure(
        "TCheckbutton",
        background=BG_PRIMARY,
        foreground=TEXT_PRIMARY,
        font=FONT_BODY,
        focuscolor=BG_PRIMARY,
    )
    style.map(
        "TCheckbutton",
        background=[("active", BG_PRIMARY)],
        foreground=[("active", TEXT_PRIMARY)],
    )


def create_button(
    parent: Any,
    text: str,
    command: Optional[Callable[[], None]] = None,
    bg_color: str = ACCENT_PRIMARY,
    hover_color: str = ACCENT_PRIMARY_HOVER,
    fg_color: str = TEXT_PRIMARY,
    font: Any = FONT_BODY_BOLD,
    padx: int = 12,
    pady: int = 6,
    width: Optional[int] = None,
    **kwargs: Any,
) -> tk.Button:
    """Creates a modern flat Tkinter button with hover highlight and hand cursor."""
    btn_kwargs: dict[str, Any] = {
        "text": text,
        "command": command,
        "bg": bg_color,
        "fg": fg_color,
        "activebackground": hover_color,
        "activeforeground": fg_color,
        "font": font,
        "relief": "flat",
        "bd": 0,
        "highlightthickness": 0,
        "cursor": "hand2",
        "padx": padx,
        "pady": pady,
    }
    if width is not None:
        btn_kwargs["width"] = width
    btn_kwargs.update(kwargs)

    btn = tk.Button(parent, **btn_kwargs)

    def on_enter(_: tk.Event) -> None:
        if btn["state"] != "disabled":
            btn.configure(bg=hover_color)

    def on_leave(_: tk.Event) -> None:
        if btn["state"] != "disabled":
            btn.configure(bg=bg_color)

    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    return btn


def create_entry(
    parent: Any,
    show: Optional[str] = None,
    font: Any = FONT_BODY,
    width: Optional[int] = None,
    **kwargs: Any,
) -> tk.Entry:
    """Creates a clean, styled entry field with modern border and dark input background."""
    entry_kwargs: dict[str, Any] = {
        "bg": BG_INPUT,
        "fg": TEXT_PRIMARY,
        "insertbackground": TEXT_PRIMARY,
        "font": font,
        "relief": "flat",
        "highlightthickness": 1,
        "highlightbackground": BORDER_COLOR,
        "highlightcolor": ACCENT_PRIMARY,
        "bd": 0,
    }
    if show is not None:
        entry_kwargs["show"] = show
    if width is not None:
        entry_kwargs["width"] = width
    entry_kwargs.update(kwargs)

    return tk.Entry(parent, **entry_kwargs)

