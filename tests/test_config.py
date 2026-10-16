"""
Unit tests for configuration loading, atomic saving, and corruption recovery.
"""

from pathlib import Path
import json
import pytest
from Localex.config import ConfigManager, AppConfig


def test_config_default_creation(tmp_path: Path):
    cfg_file = tmp_path / "config.json"
    mgr = ConfigManager(config_file=cfg_file)

    assert cfg_file.exists()
    assert mgr.config.source_lang == "auto"
    assert mgr.config.target_lang == "ar"
    assert mgr.config.active_model_id == "nllb-200-distilled-600M-int8"


def test_config_update_and_persistence(tmp_path: Path):
    cfg_file = tmp_path / "config.json"
    mgr = ConfigManager(config_file=cfg_file)

    mgr.update(theme="light", cpu_threads=8, global_shortcut="Ctrl+Alt+X")

    # Reload in a new manager
    mgr2 = ConfigManager(config_file=cfg_file)
    assert mgr2.config.theme == "light"
    assert mgr2.config.cpu_threads == 8
    assert mgr2.config.global_shortcut == "Ctrl+Alt+X"


def test_config_corruption_recovery(tmp_path: Path):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text("{ this is invalid json content !!", encoding="utf-8")

    mgr = ConfigManager(config_file=cfg_file)
    # Should restore defaults without crashing
    assert mgr.config.theme == "dark"
    # And create a backup of corrupt file
    backup = tmp_path / "config.corrupt.bak"
    assert backup.exists()
