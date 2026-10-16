"""
Clipboard manager for capturing selected text from any Windows application
and restoring previous clipboard contents safely.
"""

from __future__ import annotations

import ctypes
import logging
import time
from typing import Optional

from PySide6.QtGui import QClipboard, QGuiApplication

logger = logging.getLogger(__name__)

# Win32 Virtual Key Codes
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12       # Alt
VK_C = 0x43
VK_LWIN = 0x5B
VK_RWIN = 0x5C
KEYEVENTF_KEYUP = 0x0002


def release_pressed_modifiers() -> None:
    """
    Releases any modifier keys (Alt, Shift, Windows, Ctrl) that may be physically held down
    by the user at the exact moment the global hotkey fires.
    Without this, sending Ctrl+C while Alt/Shift is held registers as Ctrl+Alt+C or Ctrl+Shift+C!
    """
    user32 = ctypes.windll.user32
    for vk in (VK_MENU, VK_SHIFT, VK_LWIN, VK_RWIN, VK_CONTROL):
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


def send_ctrl_c() -> None:
    """Simulates pressing pure Ctrl+C using Win32 keybd_event after modifier release."""
    user32 = ctypes.windll.user32
    release_pressed_modifiers()
    time.sleep(0.04)

    # Press Ctrl + C
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_C, 0, 0, 0)
    time.sleep(0.02)
    # Release C + Ctrl
    user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


class ClipboardManager:
    """
    Manages safe reading, writing, and selection capture from the Windows clipboard.
    """

    def __init__(self) -> None:
        pass

    def get_text(self) -> str:
        """Returns the current text in the system clipboard."""
        app = QGuiApplication.instance()
        if app:
            clipboard = QGuiApplication.clipboard()
            return clipboard.text() or ""
        return ""

    def set_text(self, text: str) -> None:
        """Copies text to the system clipboard."""
        app = QGuiApplication.instance()
        if app:
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(text)

    def capture_selected_text(
        self,
        delay_ms: int = 250,
        restore_previous: bool = False,
    ) -> str:
        """
        Attempts to capture currently selected text in whatever active Windows application
        is focused by simulating pure Ctrl+C and inspecting clipboard sequence changes.
        """
        app = QGuiApplication.instance()
        if not app:
            return ""

        clipboard = QGuiApplication.clipboard()
        original_text = clipboard.text() or ""

        user32 = ctypes.windll.user32
        old_seq = user32.GetClipboardSequenceNumber()

        send_ctrl_c()

        # Responsive polling: loop checking if Windows clipboard sequence number changed
        max_checks = max(6, int(delay_ms / 20))
        for _ in range(max_checks):
            time.sleep(0.025)
            app.processEvents()
            if user32.GetClipboardSequenceNumber() != old_seq:
                break

        new_text = clipboard.text() or ""

        # If sequence changed or new text is present, return it
        if new_text and new_text != original_text:
            return new_text

        # If sequence changed even if text happens to be same, return it
        if user32.GetClipboardSequenceNumber() != old_seq and new_text:
            return new_text

        return new_text

    def restore_clipboard(self, text_to_restore: str) -> None:
        """Restores previously saved clipboard content."""
        if text_to_restore is not None:
            self.set_text(text_to_restore)


default_clipboard = ClipboardManager()
