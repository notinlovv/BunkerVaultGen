"""Secure clipboard management with delayed auto-clear across Linux environments."""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from typing import Optional

# Internal in-memory fallback for headless/CI/test environments
_MEMORY_CLIPBOARD: str = ""
_LOCK: threading.Lock = threading.Lock()


def _is_display_available() -> bool:
    """Returns True if an X11 or Wayland graphical display is available."""
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _tk_set(text: str) -> bool:
    """Attempts to set clipboard via Tkinter."""
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        return True
    except Exception:
        return False


def _tk_get() -> Optional[str]:
    """Attempts to get clipboard text via Tkinter."""
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        val = root.clipboard_get()
        root.destroy()
        return str(val)
    except Exception:
        return None


def _cli_set(text: str) -> bool:
    """Attempts to set clipboard via wl-copy (Wayland) or xclip (X11)."""
    if os.environ.get("WAYLAND_DISPLAY") and shutil.which("wl-copy"):
        try:
            subprocess.run(
                ["wl-copy"],
                input=text.encode("utf-8"),
                check=True,
                timeout=1,
            )
            return True
        except Exception:
            pass

    if os.environ.get("DISPLAY") and shutil.which("xclip"):
        try:
            subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=text.encode("utf-8"),
                check=True,
                timeout=1,
            )
            return True
        except Exception:
            pass

    return False


def _cli_get() -> Optional[str]:
    """Attempts to get clipboard text via wl-paste (Wayland) or xclip (X11)."""
    if os.environ.get("WAYLAND_DISPLAY") and shutil.which("wl-paste"):
        try:
            res = subprocess.check_output(["wl-paste"], timeout=1)
            return res.decode("utf-8")
        except Exception:
            pass

    if os.environ.get("DISPLAY") and shutil.which("xclip"):
        try:
            res = subprocess.check_output(
                ["xclip", "-selection", "clipboard", "-o"], timeout=1
            )
            return res.decode("utf-8")
        except Exception:
            pass

    return None


def set_clipboard(text: str) -> None:
    """Copies text to the system clipboard, falling back to memory in headless mode."""
    global _MEMORY_CLIPBOARD
    with _LOCK:
        _MEMORY_CLIPBOARD = text

    if _is_display_available():
        if not _tk_set(text):
            _cli_set(text)


def get_clipboard() -> str:
    """Reads current clipboard text, checking GUI backends before in-memory state."""
    global _MEMORY_CLIPBOARD
    if _is_display_available():
        content = _tk_get()
        if content is not None:
            return content
        content = _cli_get()
        if content is not None:
            return content

    with _LOCK:
        return _MEMORY_CLIPBOARD


def clear_clipboard() -> None:
    """Overwrites and clears the clipboard content."""
    set_clipboard("")


def copy_with_autoclear(
    text: str, timeout_seconds: int = 20
) -> threading.Thread:
    """Copies text to the clipboard and launches a background thread to clear it after timeout.

    The background thread checks if the clipboard still contains the exact text
    before clearing it, preventing accidental deletion of newer user clipboard data.

    Args:
        text: Plaintext string to copy.
        timeout_seconds: Duration in seconds before automatic wipe (default: 20s).

    Returns:
        The running daemon Thread instance.
    """
    set_clipboard(text)

    def _autoclear_worker() -> None:
        time.sleep(timeout_seconds)
        try:
            current = get_clipboard()
            if current == text:
                clear_clipboard()
        except Exception:
            pass

    worker_thread = threading.Thread(
        target=_autoclear_worker,
        daemon=True,
        name="ClipboardAutoClearThread",
    )
    worker_thread.start()
    return worker_thread

