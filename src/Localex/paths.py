"""
Paths and portable storage resolver for Offline Windows Translator.
Ensures zero-installation portability, isolated data storage, and write permission checks.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Optional


def get_app_dir() -> Path:
    """
    Returns the root directory of the application.
    - When frozen by PyInstaller: directory containing the executable.
    - When running from source: directory containing the project root.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # src/Localex/paths.py -> project root is 3 levels up
    return Path(__file__).resolve().parent.parent.parent


def test_write_permission(directory: Path) -> bool:
    """
    Tests whether the application has write permissions inside the given directory.
    Creates a temporary probe file and immediately deletes it.
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe_file = directory / f".write_test_{os.getpid()}.tmp"
        with open(probe_file, "w", encoding="utf-8") as f:
            f.write("probe")
        if probe_file.exists():
            probe_file.unlink()
        return True
    except (OSError, PermissionError):
        return False


class PathManager:
    """
    Manages all filesystem paths used by the application in a portable, self-contained manner.
    """

    def __init__(self, custom_data_dir: Optional[Path | str] = None) -> None:
        self.app_dir = get_app_dir()
        self._custom_data_dir = Path(custom_data_dir).resolve() if custom_data_dir else None

    @property
    def is_app_dir_writable(self) -> bool:
        return test_write_permission(self.app_dir)

    @property
    def base_data_dir(self) -> Path:
        """
        Determines the base directory for storing user data, settings, database, and models.
        Defaults to portable mode inside the application directory.
        If custom data dir is set and writable, uses it.
        If app dir is not writable and no custom dir is given, falls back to LocalAppData safely.
        """
        if self._custom_data_dir and test_write_permission(self._custom_data_dir):
            return self._custom_data_dir

        if self.is_app_dir_writable:
            return self.app_dir

        # Fallback only when running in restricted environment (e.g. C:\Program Files)
        fallback = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "Localex"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback

    @property
    def data_dir(self) -> Path:
        p = self.base_data_dir / "data"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def models_dir(self) -> Path:
        p = self.base_data_dir / "models"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def logs_dir(self) -> Path:
        p = self.base_data_dir / "logs"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def resources_dir(self) -> Path:
        # If frozen, MEIPASS contains resources if bundled, or app_dir/resources
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            meipass_res = Path(sys._MEIPASS) / "resources"
            if meipass_res.exists():
                return meipass_res
        res = self.app_dir / "resources"
        res.mkdir(parents=True, exist_ok=True)
        return res

    @property
    def icons_dir(self) -> Path:
        icons = self.resources_dir / "icons"
        icons.mkdir(parents=True, exist_ok=True)
        return icons

    @property
    def config_path(self) -> Path:
        return self.data_dir / "config.json"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "history.db"

    @property
    def log_file_path(self) -> Path:
        return self.logs_dir / "app.log"

    def set_custom_data_dir(self, path: Optional[Path | str]) -> bool:
        if path:
            candidate = Path(path).resolve()
            if test_write_permission(candidate):
                self._custom_data_dir = candidate
                return True
            return False
        self._custom_data_dir = None
        return True


default_paths = PathManager()
