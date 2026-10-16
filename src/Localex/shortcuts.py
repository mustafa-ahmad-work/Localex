"""
Global Hotkey Manager using native Win32 RegisterHotKey via ctypes and PySide6 QAbstractNativeEventFilter.
Provides zero-dependency system-wide hotkeys with collision detection and clean unregistration.
"""

from __future__ import annotations

import ctypes
import logging
from ctypes import wintypes
from typing import Callable, Dict, Optional, Tuple

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication

logger = logging.getLogger(__name__)

# Win32 Constants
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

# Common Virtual Key Code Mappings
VK_MAP: Dict[str, int] = {
    "SPACE": 0x20,
    "RETURN": 0x0D,
    "ENTER": 0x0D,
    "ESCAPE": 0x1B,
    "ESC": 0x1B,
    "TAB": 0x09,
    "BACKSPACE": 0x08,
    "INSERT": 0x2D,
    "DELETE": 0x2E,
    "HOME": 0x24,
    "END": 0x23,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "F1": 0x70,
    "F2": 0x71,
    "F3": 0x72,
    "F4": 0x73,
    "F5": 0x74,
    "F6": 0x75,
    "F7": 0x76,
    "F8": 0x77,
    "F9": 0x78,
    "F10": 0x79,
    "F11": 0x7A,
    "F12": 0x7B,
}


def parse_hotkey_string(hotkey_str: str) -> Tuple[int, int]:
    """
    Parses a hotkey string like 'Ctrl+Alt+T' or 'Win+Shift+F' into (modifiers, vk_code).
    """
    parts = [p.strip().upper() for p in hotkey_str.split("+") if p.strip()]
    modifiers = MOD_NOREPEAT
    vk_code = 0

    for part in parts:
        if part in ("CTRL", "CONTROL"):
            modifiers |= MOD_CONTROL
        elif part in ("ALT", "MENU"):
            modifiers |= MOD_ALT
        elif part == "SHIFT":
            modifiers |= MOD_SHIFT
        elif part in ("WIN", "WINDOWS", "SUPER"):
            modifiers |= MOD_WIN
        elif part in VK_MAP:
            vk_code = VK_MAP[part]
        elif len(part) == 1 and (part.isalnum() or part in ",.-/"):
            vk_code = ord(part)
        else:
            logger.warning(f"Unrecognized key token in shortcut: {part}")

    return modifiers, vk_code


class Win32NativeEventFilter(QAbstractNativeEventFilter):
    """
    PySide6 native event filter to intercept Windows WM_HOTKEY messages on the Qt loop.
    Captures both generic thread messages and window-dispatched messages.
    """

    def __init__(self, callback: Callable[[int], None]) -> None:
        super().__init__()
        self.callback = callback

    def nativeEventFilter(self, event_type, message):
        try:
            ev = bytes(event_type) if hasattr(event_type, "__bytes__") or isinstance(event_type, (bytes, bytearray)) else str(event_type).encode()
            if b"windows" in ev:
                addr = int(message)
                msg = wintypes.MSG.from_address(addr)
                if msg.message == WM_HOTKEY:
                    hotkey_id = int(msg.wParam)
                    self.callback(hotkey_id)
                    return True, 0
        except Exception as e:
            logger.error(f"Error in nativeEventFilter: {e}")
        return False, 0


class GlobalShortcutManager:
    """
    Registers and tracks system-wide Windows hotkeys.
    """

    def __init__(self) -> None:
        self._user32 = ctypes.windll.user32
        self._registered_shortcuts: Dict[int, Tuple[str, Callable[[], None]]] = {}
        self._next_id = 100
        self._event_filter: Optional[Win32NativeEventFilter] = None
        self._hwnd: int = 0

    def initialize(self, hwnd: int = 0) -> None:
        self._hwnd = hwnd
        if self._event_filter is None:
            self._event_filter = Win32NativeEventFilter(self._handle_hotkey_triggered)
            app = QCoreApplication.instance()
            if app:
                app.installNativeEventFilter(self._event_filter)

    def _handle_hotkey_triggered(self, hotkey_id: int) -> None:
        if hotkey_id in self._registered_shortcuts:
            _, callback = self._registered_shortcuts[hotkey_id]
            try:
                callback()
            except Exception as e:
                logger.error(f"Error running hotkey callback: {e}")

    def register(
        self,
        hotkey_str: str,
        callback: Callable[[], None],
        allow_fallback: bool = True,
    ) -> Tuple[bool, int, str]:
        """
        Registers a global shortcut.
        If the primary shortcut conflicts with another app (Win32 1409),
        gracefully attempts free fallbacks (Ctrl+Shift+T, Ctrl+Alt+F).
        Returns (success, hotkey_id, active_hotkey_string_or_error).
        """
        candidates = [hotkey_str]
        if allow_fallback:
            fallbacks = ["Ctrl+Shift+T", "Ctrl+Alt+F", "Ctrl+Shift+X"]
            for fb in fallbacks:
                if fb not in candidates:
                    candidates.append(fb)

        last_err = ""
        for candidate in candidates:
            modifiers, vk_code = parse_hotkey_string(candidate)
            if vk_code == 0:
                continue

            self.initialize(self._hwnd)

            hotkey_id = self._next_id
            self._next_id += 1

            success = self._user32.RegisterHotKey(self._hwnd, hotkey_id, modifiers, vk_code)
            if success:
                self._registered_shortcuts[hotkey_id] = (candidate, callback)
                logger.info(f"Successfully registered global shortcut '{candidate}' (ID={hotkey_id})")
                return True, hotkey_id, candidate

            err = ctypes.GetLastError()
            last_err = f"Windows error {err}"

        return False, -1, last_err

    def unregister(self, hotkey_id: int) -> bool:
        """Unregisters a specific hotkey."""
        if hotkey_id in self._registered_shortcuts:
            self._user32.UnregisterHotKey(self._hwnd, hotkey_id)
            del self._registered_shortcuts[hotkey_id]
            return True
        return False

    def unregister_all(self) -> None:
        """Unregisters all active hotkeys."""
        for hotkey_id in list(self._registered_shortcuts.keys()):
            self.unregister(hotkey_id)


default_shortcuts = GlobalShortcutManager()
