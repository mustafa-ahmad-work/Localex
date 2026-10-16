"""
Configuration manager for Offline Windows Translator.
Supports atomic JSON persistence, safe schema defaults, and corrupted config recovery.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from Localex.paths import default_paths

logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    # Language & Detection
    source_lang: str = "auto"
    target_lang: str = "ar"
    auto_detect: bool = True

    # Hotkey & Clipboard
    global_shortcut: str = "Ctrl+Shift+T"
    global_shortcut_enabled: bool = True
    clipboard_restore_previous: bool = True
    clipboard_capture_delay_ms: int = 150

    # Floating Window
    floating_position: str = "cursor"  # cursor, center, saved
    floating_max_screen_ratio: float = 0.33  # max 1/3 of screen
    floating_pinned: bool = False
    floating_last_width: int = 420
    floating_last_height: int = 280

    # Translation Engine & Performance
    active_model_id: str = "nllb-200-distilled-600M-int8"
    custom_model_dir: Optional[str] = None
    cpu_threads: int = 4
    beam_size: int = 1  # 1 for greedy fast CPU inference, 2-4 for higher quality
    batch_size: int = 16

    # Text-to-Speech (TTS)
    tts_voice_id: Optional[str] = None
    tts_rate: int = 0  # SAPI Rate: -10 to 10
    tts_volume: int = 100  # SAPI Volume: 0 to 100

    # History & Privacy
    history_enabled: bool = True
    history_retention_days: int = 0  # 0 = infinite

    # UI & Appearance
    ui_language: str = "en"  # "en" by default, or "ar"
    theme: str = "dark"  # dark, light
    font_size_delta: int = 0
    minimize_to_tray: bool = True
    show_tray_icon: bool = True
    start_with_windows: bool = False

    # Storage paths
    custom_data_dir: Optional[str] = None

    # First run onboarding flag
    first_run_completed: bool = False


class ConfigManager:
    """
    Handles loading, validating, and atomically saving configuration settings.
    """

    def __init__(self, config_file: Optional[Path] = None) -> None:
        self.config_file = config_file or default_paths.config_path
        self.config = AppConfig()
        self.load()

    def load(self) -> AppConfig:
        if not self.config_file.exists():
            self.save()
            return self.config

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
            
            # Filter keys to only those recognized by AppConfig
            valid_keys = AppConfig.__annotations__.keys()
            filtered_data = {k: v for k, v in data.items() if k in valid_keys}
            self.config = AppConfig(**filtered_data)
        except Exception as e:
            logger.error(f"Error loading config file {self.config_file}: {e}. Creating backup and restoring defaults.")
            try:
                backup = self.config_file.with_suffix(".corrupt.bak")
                shutil.copyfile(self.config_file, backup)
            except Exception:
                pass
            self.config = AppConfig()
            self.save()

        return self.config

    def save(self) -> bool:
        """
        Atomically saves current configuration to disk.
        """
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            tmp_file = self.config_file.with_suffix(".tmp")
            data = asdict(self.config)
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            # Atomic replace
            os.replace(tmp_file, self.config_file)
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False

    def update(self, **kwargs: Any) -> bool:
        for k, v in kwargs.items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)
        return self.save()
