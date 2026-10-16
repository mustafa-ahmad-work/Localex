"""
Modern, lightweight vector icon provider using QtAwesome with local PNG fallback.
Provides crystal-clear, high-DPI, theme-adaptive icons across all application windows.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

from Localex.paths import default_paths

logger = logging.getLogger(__name__)

# Map logical icon names to FontAwesome 6 Solid icons in QtAwesome
ICON_MAP = {
    "app_icon": "fa6s.language",
    "swap": "fa6s.arrow-right-arrow-left",
    "translate": "fa6s.wand-magic-sparkles",
    "copy": "fa6s.copy",
    "paste": "fa6s.paste",
    "clear": "fa6s.trash-can",
    "speaker": "fa6s.volume-high",
    "retranslate": "fa6s.arrows-rotate",
    "history": "fa6s.clock-rotate-left",
    "models": "fa6s.cubes",
    "settings": "fa6s.gear",
    "theme": "fa6s.circle-half-stroke",
    "pin": "fa6s.thumbtack",
    "file": "fa6s.file-lines",
    "close": "fa6s.xmark",
    "search": "fa6s.magnifying-glass",
    "open": "fa6s.up-right-from-square",
}

# Theme-aware default icon colors
DARK_ICON_COLOR = "#E2E2E8"
LIGHT_ICON_COLOR = "#2D3139"
PRIMARY_COLOR = "#0078D4"


def get_icon(name: str, color: Optional[str] = None, theme: str = "dark") -> QIcon:
    """
    Returns a high-quality QIcon. Uses QtAwesome vector fonts if available,
    with adaptive theme coloring, and falls back to tinted local PNGs.
    """
    if color is None:
        color = DARK_ICON_COLOR if theme.lower() == "dark" else LIGHT_ICON_COLOR

    # 1. Try QtAwesome
    try:
        import qtawesome as qta
        fa_name = ICON_MAP.get(name)
        if fa_name:
            return qta.icon(fa_name, color=color)
    except Exception as e:
        logger.debug(f"QtAwesome icon '{name}' failed ({e}), trying fallback")

    # 2. Fallback to local PNG in resources/icons
    png_path = default_paths.icons_dir / f"{name}.png"
    if png_path.exists():
        if name == "app_icon":
            return QIcon(str(png_path))
        # Tint monochrome PNG to theme color
        pixmap = QPixmap(str(png_path))
        if not pixmap.isNull():
            tinted = QPixmap(pixmap.size())
            tinted.fill(Qt.transparent)
            p = QPainter(tinted)
            p.drawPixmap(0, 0, pixmap)
            p.setCompositionMode(QPainter.CompositionMode_SourceIn)
            p.fillRect(tinted.rect(), QColor(color))
            p.end()
            return QIcon(tinted)
        return QIcon(str(png_path))

    return QIcon()
