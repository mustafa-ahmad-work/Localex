"""
Automated UI Flow and Integration tests for MainWindow and Dialogs.
Ensures zero recursion, clean language toggling, RTL/LTR layout directions, and dialog opening.
"""

import sys
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from Localex.config import ConfigManager
from Localex.database import DatabaseManager
from Localex.history import HistoryService
from Localex.model_manager import ModelManager
from Localex.paths import default_paths
from Localex.translator import TranslationEngine
from Localex.ui.main_window import MainWindow
from Localex.ui.history_window import HistoryWindow
from Localex.ui.settings_window import SettingsWindow
from Localex.ui.model_manager_window import ModelManagerWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_main_window_flow(qapp, tmp_path):
    config_mgr = ConfigManager(tmp_path / "config.json")
    model_mgr = ModelManager()
    engine = TranslationEngine()
    db_mgr = DatabaseManager(tmp_path / "test_hist.db")
    history_svc = HistoryService(db_mgr)

    win = MainWindow(
        config_manager=config_mgr,
        model_manager=model_mgr,
        engine=engine,
        history_service=history_svc,
    )

    # 1. Default should be English
    assert config_mgr.config.ui_language == "en"
    assert win.btn_lang_toggle.text().strip() == "العربية"
    assert win.layoutDirection() == Qt.LeftToRight

    # 2. Text changing should update word count and not cause recursion
    win.src_text_edit.setPlainText("Hello world, this is a test.")
    assert "28 chars" in win.lbl_src_counter.text()
    assert "6 words" in win.lbl_src_counter.text()
    assert win.src_text_edit.layoutDirection() == Qt.LeftToRight

    # 3. Arabic text detection & layout direction
    win.src_text_edit.setPlainText("مرحبا بالعالم هذا اختبار")
    assert win.src_text_edit.layoutDirection() == Qt.RightToLeft
    assert "23 chars" in win.lbl_src_counter.text() or "24 chars" in win.lbl_src_counter.text()

    # 4. Language toggle to Arabic
    win._toggle_ui_language()
    assert config_mgr.config.ui_language == "ar"
    assert win.btn_lang_toggle.text().strip() == "English"
    assert win.layoutDirection() == Qt.RightToLeft
    assert win.btn_translate.text().strip() == "ترجمة الآن"

    # 5. Language toggle back to English
    win._toggle_ui_language()
    assert config_mgr.config.ui_language == "en"
    assert win.btn_lang_toggle.text().strip() == "العربية"
    assert win.layoutDirection() == Qt.LeftToRight
    assert win.btn_translate.text().strip() == "Translate"

    # 6. Theme toggle
    assert config_mgr.config.theme == "dark"
    win._toggle_theme()
    assert config_mgr.config.theme == "light"
    win._toggle_theme()
    assert config_mgr.config.theme == "dark"

    # 7. Check dialog initializations
    hist_win = HistoryWindow(history_service=history_svc, ui_language="en", parent=win)
    assert hist_win.windowTitle() == "Translation History"
    assert hist_win.layoutDirection() == Qt.LeftToRight

    hist_win_ar = HistoryWindow(history_service=history_svc, ui_language="ar", parent=win)
    assert hist_win_ar.windowTitle() == "سجل الترجمات المحلية"
    assert hist_win_ar.layoutDirection() == Qt.RightToLeft

    settings_win = SettingsWindow(config_mgr, parent=win)
    assert settings_win.windowTitle() == "Application Settings"

    model_win = ModelManagerWindow(model_mgr, parent=win)
    assert "Model Management" in model_win.windowTitle()
