"""
System Tray Integration using PySide6 QSystemTrayIcon.
Supports background minimization, quick actions, context menu, and desktop notifications.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from Localex.paths import default_paths
from Localex.ui.icons import get_icon

logger = logging.getLogger(__name__)


def create_fallback_icon(text: str = "T", bg_color: str = "#2563EB") -> QIcon:
    """Generates an in-memory high-res icon if resource icons are absent."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(bg_color))
    painter.setPen(QColor(0, 0, 0, 0))
    painter.drawRoundedRect(4, 4, 56, 56, 14, 14)

    painter.setPen(QColor("#FFFFFF"))
    font = QFont("Segoe UI", 30, QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), 0x0084, text)  # AlignCenter
    painter.end()

    return QIcon(pixmap)


class AppTrayIcon(QSystemTrayIcon):
    """
    Application System Tray Icon with action menu and desktop notifications.
    """
    show_main_window_requested = Signal()
    open_models_requested = Signal()
    open_history_requested = Signal()
    open_settings_requested = Signal()
    trigger_quick_translate_requested = Signal()
    shortcut_toggled = Signal(bool)
    stop_tts_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._init_icon()
        self._build_menu()
        self.activated.connect(self._on_tray_activated)

    def _init_icon(self) -> None:
        icon_path = default_paths.icons_dir / "app_icon.png"
        if icon_path.exists():
            self.setIcon(QIcon(str(icon_path)))
        else:
            self.setIcon(create_fallback_icon("T", "#2563EB"))
        self.setToolTip("المترجم الفوري المستقل - Offline Windows Translator")

    def _build_menu(self) -> None:
        menu = QMenu()

        # Show / Hide Main Window
        self.action_show_hide = QAction(get_icon("open"), "إظهار النافذة الرئيسية", menu)
        self.action_show_hide.triggered.connect(self.show_main_window_requested.emit)
        menu.addAction(self.action_show_hide)

        # Quick Translate
        self.action_quick_tr = QAction(get_icon("translate"), "ترجمة النص المحدد (عائم)", menu)
        self.action_quick_tr.triggered.connect(self.trigger_quick_translate_requested.emit)
        menu.addAction(self.action_quick_tr)

        menu.addSeparator()

        # Models Manager
        action_models = QAction(get_icon("models"), "إدارة النماذج...", menu)
        action_models.triggered.connect(self.open_models_requested.emit)
        menu.addAction(action_models)

        # History
        action_history = QAction(get_icon("history"), "سجل الترجمات...", menu)
        action_history.triggered.connect(self.open_history_requested.emit)
        menu.addAction(action_history)

        # Settings
        action_settings = QAction(get_icon("settings"), "الإعدادات...", menu)
        action_settings.triggered.connect(self.open_settings_requested.emit)
        menu.addAction(action_settings)

        menu.addSeparator()

        # Shortcut Toggle
        self.action_shortcut = QAction(get_icon("pin"), "تفعيل الاختصار العام", menu)
        self.action_shortcut.setCheckable(True)
        self.action_shortcut.setChecked(True)
        self.action_shortcut.toggled.connect(self.shortcut_toggled.emit)
        menu.addAction(self.action_shortcut)

        # Stop TTS
        action_stop_tts = QAction(get_icon("speaker"), "إيقاف القراءة الصوتية", menu)
        action_stop_tts.triggered.connect(self.stop_tts_requested.emit)
        menu.addAction(action_stop_tts)

        menu.addSeparator()

        # Quit
        action_quit = QAction(get_icon("close"), "خروج نهائي", menu)
        action_quit.triggered.connect(self.quit_requested.emit)
        menu.addAction(action_quit)

        self.setContextMenu(menu)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_main_window_requested.emit()

    def notify(self, title: str, message: str, is_error: bool = False) -> None:
        icon = QSystemTrayIcon.Critical if is_error else QSystemTrayIcon.Information
        self.showMessage(title, message, icon, 4000)
