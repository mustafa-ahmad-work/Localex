"""
Unit tests for global shortcut string parsing.
"""

import pytest
from Localex.shortcuts import (
    parse_hotkey_string,
    MOD_ALT,
    MOD_CONTROL,
    MOD_SHIFT,
    MOD_WIN,
    MOD_NOREPEAT,
)


def test_parse_hotkey_ctrl_alt_t():
    mods, vk = parse_hotkey_string("Ctrl+Alt+T")
    assert (mods & MOD_CONTROL) != 0
    assert (mods & MOD_ALT) != 0
    assert (mods & MOD_NOREPEAT) != 0
    assert vk == ord("T")


def test_parse_hotkey_win_shift_f1():
    mods, vk = parse_hotkey_string("Win+Shift+F1")
    assert (mods & MOD_WIN) != 0
    assert (mods & MOD_SHIFT) != 0
    assert vk == 0x70  # VK_F1


def test_parse_hotkey_invalid():
    mods, vk = parse_hotkey_string("Invalid+KeyName")
    assert vk == 0
