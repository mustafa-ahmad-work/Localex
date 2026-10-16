"""
Main Window for Offline Windows Translator.
Features text translation, document/file translation, language swap, status pills,
real graphical icons, full RTL/LTR support, and dual English/Arabic interface control.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QPoint, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QCloseEvent, QFont, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from Localex.clipboard import default_clipboard
from Localex.config import ConfigManager
from Localex.history import HistoryService, default_history_service
from Localex.model_manager import ModelManager, ModelStatus
from Localex.paths import default_paths
from Localex.speech import default_speech
from Localex.translator import (
    ModelNotFoundError,
    TranslationEngine,
    TranslationError,
    TranslationResult,
)
from Localex.ui.floating_window import FloatingTranslationWindow
from Localex.ui.history_window import HistoryWindow
from Localex.ui.icons import get_icon
from Localex.ui.model_manager_window import ModelManagerWindow
from Localex.ui.settings_window import SettingsWindow
from Localex.ui.theme import STRINGS, get_theme_stylesheet
from Localex.utils import (
    detect_language,
    get_text_direction,
    is_arabic_script,
    set_text_edit_content,
    update_text_edit_direction,
)
from Localex.workers import FileTranslationWorker, TranslationWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Primary application window with real icons, semi-traditional desktop design,
    and dynamic English/Arabic RTL/LTR support.
    """
    def __init__(
        self,
        config_manager: ConfigManager,
        model_manager: ModelManager,
        engine: TranslationEngine,
        history_service: Optional[HistoryService] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.config_manager = config_manager
        self.model_manager = model_manager
        self.engine = engine
        self.history_service = history_service or default_history_service

        self.translation_worker: Optional[TranslationWorker] = None
        self.file_worker: Optional[FileTranslationWorker] = None
        self.floating_worker: Optional[TranslationWorker] = None

        # Child windows
        self.floating_window = FloatingTranslationWindow()
        self.floating_window.open_in_main_requested.connect(self._on_open_from_floating)

        self.settings_window: Optional[SettingsWindow] = None
        self.history_window: Optional[HistoryWindow] = None
        self.model_manager_window: Optional[ModelManagerWindow] = None

        self.resize(960, 640)
        self.setMinimumSize(780, 500)
        self.setWindowIcon(get_icon("app_icon"))

        # Live instant translation debounce timer
        self._auto_translate_timer = QTimer(self)
        self._auto_translate_timer.setSingleShot(True)
        self._auto_translate_timer.setInterval(450)
        self._auto_translate_timer.timeout.connect(self._do_auto_translate)

        self._init_ui()
        self._init_shortcuts()
        self._apply_ui_language()
        self._apply_theme()
        self.refresh_model_status()

    def _tr(self, key: str) -> str:
        lang = getattr(self.config_manager.config, "ui_language", "en")
        return STRINGS.get(lang, STRINGS["en"]).get(key, key)

    def _init_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # Top Navigation & Status Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        # App Logo & Title
        self.lbl_logo = QLabel()
        self.lbl_logo.setPixmap(get_icon("app_icon").pixmap(24, 24))
        top_bar.addWidget(self.lbl_logo)

        self.lbl_app_title = QLabel("Offline Translator")
        self.lbl_app_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078D4;")
        top_bar.addWidget(self.lbl_app_title)

        # Model Status Pill
        self.btn_model_pill = QPushButton()
        self.btn_model_pill.setCursor(Qt.PointingHandCursor)
        self.btn_model_pill.clicked.connect(self.open_model_manager)
        top_bar.addWidget(self.btn_model_pill)

        top_bar.addStretch()

        # Language Switcher Button (English / Arabic)
        self.btn_lang_toggle = QPushButton()
        self.btn_lang_toggle.setToolTip("Switch UI Language / تبديل لغة الواجهة")
        self.btn_lang_toggle.clicked.connect(self._toggle_ui_language)
        top_bar.addWidget(self.btn_lang_toggle)

        # Top Navigation Buttons with real icons
        self.btn_history = QPushButton()
        self.btn_history.setIcon(get_icon("history"))
        self.btn_history.setIconSize(QSize(16, 16))
        self.btn_history.clicked.connect(self.open_history)
        top_bar.addWidget(self.btn_history)

        self.btn_models = QPushButton()
        self.btn_models.setIcon(get_icon("models"))
        self.btn_models.setIconSize(QSize(16, 16))
        self.btn_models.clicked.connect(self.open_model_manager)
        top_bar.addWidget(self.btn_models)

        self.btn_settings = QPushButton()
        self.btn_settings.setIcon(get_icon("settings"))
        self.btn_settings.setIconSize(QSize(16, 16))
        self.btn_settings.clicked.connect(self.open_settings)
        top_bar.addWidget(self.btn_settings)

        self.btn_theme = QPushButton()
        self.btn_theme.setIcon(get_icon("theme"))
        self.btn_theme.setIconSize(QSize(16, 16))
        self.btn_theme.setToolTip("Toggle Dark/Light Mode")
        self.btn_theme.clicked.connect(self._toggle_theme)
        top_bar.addWidget(self.btn_theme)

        main_layout.addLayout(top_bar)

        # Main Tabs
        self.tabs = QTabWidget()
        self.tab_text_widget = self._create_text_translation_tab()
        self.tab_text_widget.setStyleSheet("border-radius: 0;")
        self.tab_file_widget = self._create_file_translation_tab()
        self.tabs.addTab(self.tab_text_widget, "Text Translation")
        self.tabs.addTab(self.tab_file_widget, "Document Translation")
        main_layout.addWidget(self.tabs)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.lbl_status_device = QLabel("Engine: CTranslate2 INT8 CPU")
        self.lbl_status_device.setStyleSheet("color: #888888; padding: 0 8px;")
        self.lbl_status_offline = QLabel("100% Offline")
        self.lbl_status_offline.setStyleSheet("color: #107C41; font-weight: bold; padding: 0 8px;")
        self.status_bar.addPermanentWidget(self.lbl_status_device)
        self.status_bar.addPermanentWidget(self.lbl_status_offline)

    def _create_text_translation_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 10, 6, 6)
        layout.setSpacing(8)

        # Language Bar
        lang_bar = QHBoxLayout()
        lang_bar.setSpacing(8)

        # Source Lang Combo
        self.combo_source = QComboBox()
        self.combo_source.addItem("Auto Detect", "auto")
        self.combo_source.addItem("Arabic", "ar")
        self.combo_source.addItem("English", "en")
        lang_bar.addWidget(self.combo_source, stretch=2)

        # Swap Button with real icon
        self.btn_swap = QPushButton("Swap")
        self.btn_swap.setIcon(get_icon("swap"))
        self.btn_swap.setIconSize(QSize(16, 16))
        self.btn_swap.clicked.connect(self._swap_languages)
        lang_bar.addWidget(self.btn_swap, stretch=1)

        # Target Lang Combo
        self.combo_target = QComboBox()
        self.combo_target.addItem("Arabic", "ar")
        self.combo_target.addItem("English", "en")
        self.combo_target.currentIndexChanged.connect(self._on_target_lang_changed)
        lang_bar.addWidget(self.combo_target, stretch=2)

        lang_bar.addStretch()

        # Translate Action Button
        self.btn_translate = QPushButton("Translate")
        self.btn_translate.setProperty("class", "primary")
        self.btn_translate.setIcon(get_icon("translate", color="#FFFFFF"))
        self.btn_translate.setIconSize(QSize(16, 16))
        self.btn_translate.setStyleSheet("min-width: 130px; font-weight: bold;")
        self.btn_translate.clicked.connect(self.translate_current_text)
        lang_bar.addWidget(self.btn_translate)

        layout.addLayout(lang_bar)

        # Text Boxes Splitter
        splitter = QSplitter(Qt.Horizontal)

        # Source Box Container
        src_container = QWidget()
        src_layout = QVBoxLayout(src_container)
        src_layout.setContentsMargins(0, 0, 0, 0)
        src_layout.setSpacing(4)

        src_header = QHBoxLayout()
        self.lbl_src_title = QLabel("Source Text:")
        self.lbl_src_title.setStyleSheet("font-weight: 600; color: #888888;")
        src_header.addWidget(self.lbl_src_title)

        self.lbl_src_counter = QLabel("0 chars | 0 words")
        self.lbl_src_counter.setStyleSheet("color: #888888; font-size: 11px;")
        src_header.addWidget(self.lbl_src_counter)
        src_header.addStretch()

        src_header.setSpacing(8)
        self.btn_paste = QPushButton("Paste")
        self.btn_paste.setIcon(get_icon("paste"))
        self.btn_paste.setIconSize(QSize(16, 16))
        self.btn_paste.setProperty("class", "icon-btn")
        self.btn_paste.clicked.connect(self._paste_source)
        src_header.addWidget(self.btn_paste)

        self.btn_speak_source = QPushButton("Listen")
        self.btn_speak_source.setIcon(get_icon("speaker"))
        self.btn_speak_source.setIconSize(QSize(16, 16))
        self.btn_speak_source.setProperty("class", "icon-btn")
        self.btn_speak_source.clicked.connect(self._speak_source)
        src_header.addWidget(self.btn_speak_source)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setIcon(get_icon("clear"))
        self.btn_clear.setIconSize(QSize(16, 16))
        self.btn_clear.setProperty("class", "icon-btn")
        self.btn_clear.clicked.connect(self._clear_source)
        src_header.addWidget(self.btn_clear)

        src_layout.addLayout(src_header)

        self.src_text_edit = QTextEdit()
        self.src_text_edit.setAcceptRichText(False)
        self.src_text_edit.setPlaceholderText("Enter or paste text to translate...")
        self.src_text_edit.textChanged.connect(self._on_source_text_changed)
        src_layout.addWidget(self.src_text_edit)

        splitter.addWidget(src_container)

        # Target Box Container
        tgt_container = QWidget()
        tgt_layout = QVBoxLayout(tgt_container)
        tgt_layout.setContentsMargins(0, 0, 0, 0)
        tgt_layout.setSpacing(4)

        tgt_header = QHBoxLayout()
        tgt_header.setSpacing(8)
        self.lbl_tgt_title = QLabel("Translation:")
        self.lbl_tgt_title.setStyleSheet("font-weight: 600; color: #0078D4;")
        tgt_header.addWidget(self.lbl_tgt_title)

        self.lbl_tgt_counter = QLabel("0 chars")
        self.lbl_tgt_counter.setStyleSheet("color: #888888; font-size: 11px;")
        tgt_header.addWidget(self.lbl_tgt_counter)
        tgt_header.addStretch()

        self.btn_copy_target = QPushButton("Copy")
        self.btn_copy_target.setIcon(get_icon("copy"))
        self.btn_copy_target.setIconSize(QSize(16, 16))
        self.btn_copy_target.setProperty("class", "icon-btn")
        self.btn_copy_target.clicked.connect(self._copy_target)
        tgt_header.addWidget(self.btn_copy_target)

        self.btn_speak_target = QPushButton("Listen")
        self.btn_speak_target.setIcon(get_icon("speaker"))
        self.btn_speak_target.setIconSize(QSize(16, 16))
        self.btn_speak_target.setProperty("class", "icon-btn")
        self.btn_speak_target.clicked.connect(self._speak_target)
        tgt_header.addWidget(self.btn_speak_target)

        self.btn_retranslate = QPushButton("Re-translate")
        self.btn_retranslate.setIcon(get_icon("retranslate"))
        self.btn_retranslate.setIconSize(QSize(16, 16))
        self.btn_retranslate.setProperty("class", "icon-btn")
        self.btn_retranslate.clicked.connect(self.translate_current_text)
        tgt_header.addWidget(self.btn_retranslate)

        tgt_layout.addLayout(tgt_header)

        self.tgt_text_edit = QTextEdit()
        self.tgt_text_edit.setReadOnly(True)
        self.tgt_text_edit.setAcceptRichText(False)
        self.tgt_text_edit.setPlaceholderText("Translation will appear here instantly...")
        tgt_layout.addWidget(self.tgt_text_edit)

        splitter.addWidget(tgt_container)
        splitter.setSizes([480, 480])

        layout.addWidget(splitter)
        self._reset_target_direction()
        return widget

    def _create_file_translation_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(10)

        self.lbl_file_info = QLabel()
        self.lbl_file_info.setProperty("class", "info-banner")
        self.lbl_file_info.setWordWrap(True)
        layout.addWidget(self.lbl_file_info)


        # File Chooser
        file_box = QHBoxLayout()
        self.btn_pick_file = QPushButton("Choose File...")
        self.btn_pick_file.setIcon(get_icon("file"))
        self.btn_pick_file.setIconSize(QSize(16, 16))
        self.btn_pick_file.clicked.connect(self._pick_file_for_translation)
        file_box.addWidget(self.btn_pick_file)

        self.lbl_chosen_file = QLabel("No file selected.")
        self.lbl_chosen_file.setStyleSheet("color: #888888;")
        file_box.addWidget(self.lbl_chosen_file, stretch=1)
        layout.addLayout(file_box)

        # Direction Box
        dir_box = QHBoxLayout()
        self.lbl_file_dir = QLabel("Direction:")
        dir_box.addWidget(self.lbl_file_dir)
        self.combo_file_direction = QComboBox()
        self.combo_file_direction.addItems(["Auto → Arabic", "Auto → English", "Arabic → English", "English → Arabic"])
        dir_box.addWidget(self.combo_file_direction)
        dir_box.addStretch()

        self.btn_start_file_tr = QPushButton("Start File Translation")
        self.btn_start_file_tr.setProperty("class", "primary")
        self.btn_start_file_tr.setEnabled(False)
        self.btn_start_file_tr.clicked.connect(self._start_file_translation)
        dir_box.addWidget(self.btn_start_file_tr)

        self.btn_cancel_file_tr = QPushButton("Cancel")
        self.btn_cancel_file_tr.setProperty("class", "danger")
        self.btn_cancel_file_tr.setEnabled(False)
        self.btn_cancel_file_tr.clicked.connect(self._cancel_file_translation)
        dir_box.addWidget(self.btn_cancel_file_tr)

        layout.addLayout(dir_box)

        # Progress
        self.file_progress_bar = QProgressBar()
        self.file_progress_bar.setRange(0, 100)
        self.file_progress_bar.setValue(0)
        layout.addWidget(self.file_progress_bar)

        self.lbl_file_stats = QLabel("Ready.")
        self.lbl_file_stats.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(self.lbl_file_stats)

        # Live Preview
        self.lbl_file_preview_title = QLabel("Live Translation Preview:")
        layout.addWidget(self.lbl_file_preview_title)
        self.file_preview_edit = QTextEdit()
        self.file_preview_edit.setReadOnly(True)
        self.file_preview_edit.setAcceptRichText(False)
        layout.addWidget(self.file_preview_edit)

        return widget

    def _init_shortcuts(self) -> None:
        shortcut_tr = QShortcut(QKeySequence("Ctrl+Return"), self)
        shortcut_tr.activated.connect(self.translate_current_text)

        shortcut_tr2 = QShortcut(QKeySequence("Ctrl+Enter"), self)
        shortcut_tr2.activated.connect(self.translate_current_text)

        shortcut_swap = QShortcut(QKeySequence("Ctrl+L"), self)
        shortcut_swap.activated.connect(self._swap_languages)

    def _update_icons(self) -> None:
        th = self.config_manager.config.theme
        self.btn_lang_toggle.setIcon(get_icon("swap", theme=th))
        self.btn_history.setIcon(get_icon("history", theme=th))
        self.btn_models.setIcon(get_icon("models", theme=th))
        self.btn_settings.setIcon(get_icon("settings", theme=th))
        self.btn_theme.setIcon(get_icon("theme", theme=th))

        self.btn_swap.setIcon(get_icon("swap", theme=th))
        self.btn_translate.setIcon(get_icon("translate", color="#FFFFFF"))

        self.btn_paste.setIcon(get_icon("paste", theme=th))
        self.btn_speak_source.setIcon(get_icon("speaker", theme=th))
        self.btn_clear.setIcon(get_icon("clear", theme=th))
        self.btn_copy_target.setIcon(get_icon("copy", theme=th))
        self.btn_speak_target.setIcon(get_icon("speaker", theme=th))
        self.btn_retranslate.setIcon(get_icon("retranslate", theme=th))

        self.btn_pick_file.setIcon(get_icon("file", theme=th))
        if hasattr(self, "floating_window") and self.floating_window:
            self.floating_window.apply_theme(th)

    def _apply_theme(self) -> None:
        theme_name = self.config_manager.config.theme
        sheet = get_theme_stylesheet(theme_name)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(sheet)
        self.setStyleSheet(sheet)
        zoom = self.config_manager.config.font_size_delta
        font = self.font()
        font.setPixelSize(max(11, 13 + zoom))
        self.setFont(font)
        self._update_icons()

    def _toggle_theme(self) -> None:
        curr = self.config_manager.config.theme
        new_theme = "light" if curr == "dark" else "dark"
        self.config_manager.config.theme = new_theme
        self.config_manager.save()
        self._apply_theme()

    def _toggle_ui_language(self) -> None:
        curr = getattr(self.config_manager.config, "ui_language", "en")
        new_lang = "ar" if curr == "en" else "en"
        self.config_manager.config.ui_language = new_lang
        self.config_manager.save()
        self._apply_ui_language()

    def _apply_ui_language(self) -> None:
        lang = getattr(self.config_manager.config, "ui_language", "en")
        is_ar = (lang == "ar")

        # Explicitly set layout direction on global application, window, and widgets
        direction = Qt.RightToLeft if is_ar else Qt.LeftToRight
        app = QApplication.instance()
        if app:
            app.setLayoutDirection(direction)
        self.setLayoutDirection(direction)
        self.centralWidget().setLayoutDirection(direction)
        self.tabs.setLayoutDirection(direction)

        # Update text strings with generous, comfortable space between icons and text
        self.setWindowTitle(self._tr("app_title"))
        self.lbl_app_title.setText(self._tr("app_title"))
        self.btn_lang_toggle.setText("  " + self._tr("language_toggle"))
        self.btn_history.setText("  " + self._tr("history"))
        self.btn_models.setText("  " + self._tr("models"))
        self.btn_settings.setText("  " + self._tr("settings"))

        self.tabs.setTabText(0, self._tr("tab_text"))
        self.tabs.setTabText(1, self._tr("tab_file"))

        # Language dropdowns
        src_idx = self.combo_source.currentIndex()
        tgt_idx = self.combo_target.currentIndex()
        self.combo_source.setItemText(0, self._tr("auto_detect"))
        self.combo_source.setItemText(1, self._tr("arabic"))
        self.combo_source.setItemText(2, self._tr("english"))
        self.combo_target.setItemText(0, self._tr("arabic"))
        self.combo_target.setItemText(1, self._tr("english"))
        self.combo_source.setCurrentIndex(src_idx if src_idx >= 0 else 0)
        self.combo_target.setCurrentIndex(tgt_idx if tgt_idx >= 0 else 0)

        self.btn_swap.setText("  " + self._tr("swap"))
        self.btn_translate.setText("  " + self._tr("translate_now"))
        self.lbl_src_title.setText(self._tr("source_label"))
        self.lbl_tgt_title.setText(self._tr("target_label"))
        self.btn_paste.setText("  " + self._tr("paste"))
        self.btn_clear.setText("  " + self._tr("clear"))
        self.btn_copy_target.setText("  " + self._tr("copy"))
        self.btn_speak_target.setText("  " + self._tr("listen"))
        self.btn_retranslate.setText("  " + self._tr("retranslate"))

        self.src_text_edit.setPlaceholderText(self._tr("source_placeholder"))
        self.tgt_text_edit.setPlaceholderText(self._tr("target_placeholder"))

        # File Tab
        self.lbl_file_info.setText(self._tr("file_info"))
        self.btn_pick_file.setText("  " + self._tr("pick_file"))
        self.lbl_file_dir.setText(self._tr("file_direction"))
        self.btn_start_file_tr.setText("  " + self._tr("start_file_tr"))
        self.btn_cancel_file_tr.setText("  " + self._tr("cancel"))
        self.lbl_file_preview_title.setText(self._tr("file_preview"))

        self.lbl_status_device.setText(self._tr("cpu_int8"))
        self.lbl_status_offline.setText(self._tr("offline_badge"))

        # Floating window strings
        self.floating_window.apply_language(lang)

        self.refresh_model_status()

    def refresh_model_status(self) -> None:
        cfg = self.config_manager.config
        status = self.model_manager.get_model_status(
            cfg.active_model_id,
            Path(cfg.custom_model_dir) if cfg.custom_model_dir else None,
        )

        if status == ModelStatus.INSTALLED:
            self.btn_model_pill.setText(self._tr("model_status_ready"))
            self.btn_model_pill.setStyleSheet("""
                background-color: #0E5A35;
                color: #FFFFFF;
                border: 1px solid #107C41;
                padding: 3px 10px;
                font-weight: 600;
            """)
            self.btn_translate.setEnabled(True)
        else:
            self.btn_model_pill.setText(self._tr("model_status_missing"))
            self.btn_model_pill.setStyleSheet("""
                background-color: #7A4D00;
                color: #FFFFFF;
                border: 1px solid #D83B01;
                padding: 3px 10px;
                font-weight: 600;
            """)

    def _on_source_text_changed(self) -> None:
        if getattr(self, "_is_updating_text", False):
            return
        self._is_updating_text = True
        try:
            text = self.src_text_edit.toPlainText()
            chars = len(text)
            words = len(text.split()) if text.strip() else 0
            self.lbl_src_counter.setText(self._tr("chars_words").format(chars=chars, words=words))

            # Dynamic RTL / LTR layout direction
            if text.strip():
                detected = detect_language(text)
                is_ar = (detected == "ar") or is_arabic_script(text)
                update_text_edit_direction(self.src_text_edit, is_ar)

                if self.combo_source.currentData() == "auto":
                    if is_ar and self.combo_target.currentData() == "ar":
                        self.combo_target.setCurrentIndex(1)  # switch to English
                    elif not is_ar and self.combo_target.currentData() == "en":
                        self.combo_target.setCurrentIndex(0)  # switch to Arabic

        # Dynamic debounce: 800ms for large texts, 450ms for short texts
                debounce_ms = 800 if chars > 350 else 450
                self._auto_translate_timer.start(debounce_ms)
            else:
                self._auto_translate_timer.stop()
                self.tgt_text_edit.clear()
                self._reset_target_direction()
                self.lbl_tgt_counter.setText(self._tr("chars").format(chars=0))
        finally:
            self._is_updating_text = False

    def _reset_target_direction(self) -> None:
        """Sets the target edit direction and alignment to match the selected target language."""
        is_ar = (self.combo_target.currentData() == "ar")
        direction = Qt.RightToLeft if is_ar else Qt.LeftToRight
        alignment = Qt.AlignRight if is_ar else Qt.AlignLeft
        self.tgt_text_edit.setLayoutDirection(direction)
        if self.tgt_text_edit.viewport():
            self.tgt_text_edit.viewport().setLayoutDirection(direction)
        doc = self.tgt_text_edit.document()
        opt = doc.defaultTextOption()
        opt.setTextDirection(direction)
        opt.setAlignment(alignment)
        doc.setDefaultTextOption(opt)
        self.tgt_text_edit.setAlignment(alignment)

    def _on_target_lang_changed(self) -> None:
        """Updates target box layout direction whenever the user switches target language."""
        tgt_txt = self.tgt_text_edit.toPlainText().strip()
        if not tgt_txt:
            self._reset_target_direction()
        else:
            is_ar = (
                (self.combo_target.currentData() == "ar")
                or is_arabic_script(tgt_txt)
                or (get_text_direction(tgt_txt) == "rtl")
            )
            set_text_edit_content(self.tgt_text_edit, tgt_txt, is_arabic=is_ar)

    def _do_auto_translate(self) -> None:
        text = self.src_text_edit.toPlainText().strip()
        if not text:
            return
        # If already translating, do not interrupt
        if self.translation_worker and self.translation_worker.isRunning():
            return
        cfg = self.config_manager.config
        model_dir = (
            Path(cfg.custom_model_dir)
            if cfg.custom_model_dir
            else self.model_manager.get_model_directory(cfg.active_model_id)
        )
        if self.model_manager.get_model_status(cfg.active_model_id, model_dir) != ModelStatus.INSTALLED:
            return
        self._start_translation(text, is_manual=False)

    def _swap_languages(self) -> None:
        src_data = self.combo_source.currentData()
        tgt_data = self.combo_target.currentData()

        if src_data != "auto":
            new_tgt_idx = 0 if src_data == "ar" else 1
            new_src_idx = 1 if tgt_data == "ar" else 2
            self.combo_source.setCurrentIndex(new_src_idx)
            self.combo_target.setCurrentIndex(new_tgt_idx)
        else:
            current_text = self.src_text_edit.toPlainText()
            detected = detect_language(current_text) if current_text else "en"
            new_tgt_idx = 0 if detected == "ar" else 1
            self.combo_target.setCurrentIndex(new_tgt_idx)

        src_txt = self.src_text_edit.toPlainText()
        tgt_txt = self.tgt_text_edit.toPlainText()
        src_is_ar = (
            (self.combo_source.currentData() == "ar")
            or is_arabic_script(tgt_txt)
            or (get_text_direction(tgt_txt) == "rtl")
        )
        tgt_is_ar = (
            (self.combo_target.currentData() == "ar")
            or is_arabic_script(src_txt)
            or (get_text_direction(src_txt) == "rtl")
        )
        set_text_edit_content(self.src_text_edit, tgt_txt, is_arabic=src_is_ar)
        set_text_edit_content(self.tgt_text_edit, src_txt, is_arabic=tgt_is_ar)

    def _paste_source(self) -> None:
        clip_text = default_clipboard.get_text()
        if clip_text:
            set_text_edit_content(self.src_text_edit, clip_text)

    def _clear_source(self) -> None:
        self._auto_translate_timer.stop()
        self.src_text_edit.clear()
        self.tgt_text_edit.clear()
        self._reset_target_direction()
        self.lbl_tgt_counter.setText(self._tr("chars").format(chars=0))

    def _copy_target(self) -> None:
        txt = self.tgt_text_edit.toPlainText().strip()
        if txt:
            default_clipboard.set_text(txt)
            self.statusBar().showMessage(self._tr("copied_msg"), 3000)

    def _speak_source(self) -> None:
        txt = self.src_text_edit.toPlainText().strip()
        if txt:
            default_speech.speak(txt)

    def _speak_target(self) -> None:
        txt = self.tgt_text_edit.toPlainText().strip()
        if txt:
            default_speech.speak(txt)

    def translate_current_text(self) -> None:
        text = self.src_text_edit.toPlainText().strip()
        if not text:
            return
        self._auto_translate_timer.stop()
        self._start_translation(text, is_manual=True)

    def _start_translation(self, text: str, is_manual: bool = True) -> None:
        cfg = self.config_manager.config
        model_dir = (
            Path(cfg.custom_model_dir)
            if cfg.custom_model_dir
            else self.model_manager.get_model_directory(cfg.active_model_id)
        )
        status = self.model_manager.get_model_status(cfg.active_model_id, model_dir)
        if status != ModelStatus.INSTALLED:
            if is_manual:
                is_ar = (getattr(cfg, "ui_language", "en") == "ar")
                title = "نموذج الترجمة مفقود" if is_ar else "Model Not Found"
                msg = (
                    "النموذج غير مثبت بعد.\nهل تريد فتح صفحة إدارة النماذج لتنزيله الآن؟"
                    if is_ar
                    else "Translation model is not installed yet.\nWould you like to open the Model Manager to download it now?"
                )
                ans = QMessageBox.question(self, title, msg, QMessageBox.Yes | QMessageBox.No)
                if ans == QMessageBox.Yes:
                    self.open_model_manager()
            return

        self.engine.set_model_path(model_dir)
        self.engine.cpu_threads = cfg.cpu_threads
        self.engine.beam_size = cfg.beam_size
        self.engine.batch_size = cfg.batch_size

        src_l = self.combo_source.currentData()
        tgt_l = self.combo_target.currentData()

        # If previous translation is still running, safely handle without terminate()
        if self.translation_worker and self.translation_worker.isRunning():
            if not is_manual:
                return
            self.translation_worker.wait(300)
            if self.translation_worker.isRunning():
                self.statusBar().showMessage(self._tr("translating"), 2000)
                return

        self.btn_translate.setEnabled(False)
        self.btn_translate.setText("  " + self._tr("translating"))

        self.translation_worker = TranslationWorker(
            engine=self.engine,
            text=text,
            source_lang=src_l,
            target_lang=tgt_l,
            parent=self,
        )
        self.translation_worker.translation_finished.connect(
            lambda res: self._on_translation_success(res, is_manual)
        )
        self.translation_worker.translation_failed.connect(
            lambda err: self._on_translation_failed(err, is_manual)
        )
        self.translation_worker.start()

    def _on_translation_success(self, result: TranslationResult, is_manual: bool = True) -> None:
        self.btn_translate.setEnabled(True)
        is_ar = (
            (result.target_lang == "ar")
            or is_arabic_script(result.translated_text)
            or (get_text_direction(result.translated_text) == "rtl")
        )
        set_text_edit_content(self.tgt_text_edit, result.translated_text, is_arabic=is_ar)
        self.lbl_tgt_counter.setText(self._tr("chars").format(chars=len(result.translated_text)))

        cache_note = self._tr("cached") if result.is_cached else ""
        self.statusBar().showMessage(
            self._tr("completed_in").format(sec=result.duration_seconds, cached=cache_note),
            4000,
        )

        if self.config_manager.config.history_enabled and len(result.source_text.strip()) > 1:
            self.history_service.record_translation(
                source_text=result.source_text,
                translated_text=result.translated_text,
                source_lang=result.source_lang,
                target_lang=result.target_lang,
                model_name=result.model_name,
            )

    def _on_translation_failed(self, error_msg: str, is_manual: bool = True) -> None:
        self.btn_translate.setEnabled(True)
        self.btn_translate.setText("  " + self._tr("translate_now"))
        self.statusBar().showMessage(self._tr("error_tr").format(err=error_msg), 5000)
        if is_manual:
            QMessageBox.warning(self, "Translation Error", error_msg)

    # --- Document / File Translation ---
    def _pick_file_for_translation(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self._tr("pick_file"),
            "",
            "Supported Files (*.txt *.md *.csv);;Text Files (*.txt);;Markdown Files (*.md);;CSV Files (*.csv)",
        )
        if file_path:
            self._chosen_input_file = Path(file_path)
            self.lbl_chosen_file.setText(f"{self._chosen_input_file.name} ({self._chosen_input_file.stat().st_size} bytes)")
            self.btn_start_file_tr.setEnabled(True)

    def _start_file_translation(self) -> None:
        if not hasattr(self, "_chosen_input_file") or not self._chosen_input_file.exists():
            return

        cfg = self.config_manager.config
        model_dir = (
            Path(cfg.custom_model_dir)
            if cfg.custom_model_dir
            else self.model_manager.get_model_directory(cfg.active_model_id)
        )
        if self.model_manager.get_model_status(cfg.active_model_id, model_dir) != ModelStatus.INSTALLED:
            QMessageBox.warning(self, "Model Required", "Model must be installed before translating files.")
            return

        ext = self._chosen_input_file.suffix
        default_out_name = f"{self._chosen_input_file.stem}_translated{ext}"
        out_file, _ = QFileDialog.getSaveFileName(
            self,
            "Save Translated File As",
            str(self._chosen_input_file.parent / default_out_name),
            f"Same Format (*{ext})",
        )
        if not out_file:
            return

        dir_idx = self.combo_file_direction.currentIndex()
        src_l, tgt_l = "auto", "ar"
        if dir_idx == 1:
            src_l, tgt_l = "auto", "en"
        elif dir_idx == 2:
            src_l, tgt_l = "ar", "en"
        elif dir_idx == 3:
            src_l, tgt_l = "en", "ar"

        self.engine.set_model_path(model_dir)
        self.btn_start_file_tr.setEnabled(False)
        self.btn_cancel_file_tr.setEnabled(True)
        self.btn_pick_file.setEnabled(False)
        self.file_preview_edit.clear()

        self.file_worker = FileTranslationWorker(
            engine=self.engine,
            input_file=self._chosen_input_file,
            output_file=Path(out_file),
            source_lang=src_l,
            target_lang=tgt_l,
        )
        self.file_worker.progress_updated.connect(self._on_file_progress)
        self.file_worker.preview_ready.connect(lambda txt: set_text_edit_content(self.file_preview_edit, txt))
        self.file_worker.file_finished.connect(self._on_file_finished)
        self.file_worker.file_failed.connect(self._on_file_failed)
        self.file_worker.start()

    def _on_file_progress(self, current: int, total: int) -> None:
        percent = int(current / total * 100) if total > 0 else 0
        self.file_progress_bar.setValue(percent)
        self.lbl_file_stats.setText(f"Processing chunk {current}/{total} ({percent}%)...")

    def _on_file_finished(self, out_path: str) -> None:
        self.btn_start_file_tr.setEnabled(True)
        self.btn_cancel_file_tr.setEnabled(False)
        self.btn_pick_file.setEnabled(True)
        self.file_progress_bar.setValue(100)
        self.lbl_file_stats.setText(f"Completed: {out_path}")
        QMessageBox.information(self, "Completed", f"File translated successfully and saved to:\n{out_path}")

    def _on_file_failed(self, error: str) -> None:
        self.btn_start_file_tr.setEnabled(True)
        self.btn_cancel_file_tr.setEnabled(False)
        self.btn_pick_file.setEnabled(True)
        self.lbl_file_stats.setText(f"Error: {error}")
        QMessageBox.warning(self, "File Translation Error", error)

    def _cancel_file_translation(self) -> None:
        if self.file_worker:
            self.file_worker.cancel()

    # --- Windows Navigation & Dialogs ---
    def open_model_manager(self) -> None:
        self.model_manager_window = ModelManagerWindow(self.model_manager, self)
        self.model_manager_window.model_configured.connect(self._on_model_configured)
        self.model_manager_window.exec()
        self.refresh_model_status()

    def _on_model_configured(self, model_id: str, model_path: str) -> None:
        self.config_manager.config.active_model_id = model_id
        if model_id == "custom":
            self.config_manager.config.custom_model_dir = model_path
        else:
            self.config_manager.config.custom_model_dir = None
        self.config_manager.save()
        self.refresh_model_status()

    def open_history(self) -> None:
        lang = getattr(self.config_manager.config, "ui_language", "en")
        self.history_window = HistoryWindow(self.history_service, ui_language=lang, parent=self)
        self.history_window.retranslate_requested.connect(self._on_retranslate_from_history)
        self.history_window._load_data()
        self.history_window.exec()

    def _on_retranslate_from_history(self, text: str, src_l: str, tgt_l: str) -> None:
        self.tabs.setCurrentIndex(0)
        set_text_edit_content(self.src_text_edit, text)
        src_map = {"auto": 0, "ar": 1, "en": 2}
        self.combo_source.setCurrentIndex(src_map.get(src_l, 0))
        self.combo_target.setCurrentIndex(0 if tgt_l == "ar" else 1)
        self.translate_current_text()

    def open_settings(self) -> None:
        self.settings_window = SettingsWindow(self.config_manager, self)
        self.settings_window.settings_saved.connect(self._on_settings_saved)
        self.settings_window.exec()

    def _on_settings_saved(self) -> None:
        self._apply_ui_language()
        self._apply_theme()
        self.refresh_model_status()

    def _on_open_from_floating(self, src: str, tr: str, src_l: str, tgt_l: str) -> None:
        self.tabs.setCurrentIndex(0)
        src_is_ar = (src_l == "ar") or is_arabic_script(src) or (get_text_direction(src) == "rtl")
        tgt_is_ar = (tgt_l == "ar") or is_arabic_script(tr) or (get_text_direction(tr) == "rtl")
        set_text_edit_content(self.src_text_edit, src, is_arabic=src_is_ar)
        set_text_edit_content(self.tgt_text_edit, tr, is_arabic=tgt_is_ar)
        self.show()
        self.raise_()
        self.activateWindow()

    def trigger_floating_translation(self, text_to_translate: str) -> None:
        if not text_to_translate.strip():
            return

        cfg = self.config_manager.config
        is_ar_ui = (getattr(cfg, "ui_language", "en") == "ar")
        model_dir = (
            Path(cfg.custom_model_dir)
            if cfg.custom_model_dir
            else self.model_manager.get_model_directory(cfg.active_model_id)
        )
        if self.model_manager.get_model_status(cfg.active_model_id, model_dir) != ModelStatus.INSTALLED:
            missing_msg = (
                "نموذج الترجمة غير مثبت بعد. يرجى فتح التطبيق لتنزيل النموذج بنقرة واحدة."
                if is_ar_ui
                else "Model is not installed. Open the application to download the offline translation model."
            )
            self.floating_window.display_translation(
                text_to_translate,
                missing_msg,
                "auto",
                cfg.target_lang,
            )
            return

        # Detect language of selected text for floating window
        detected = detect_language(text_to_translate)
        is_src_ar = (detected == "ar") or is_arabic_script(text_to_translate)
        src_lang = "ar" if is_src_ar else "en"
        tgt_lang = "en" if is_src_ar else "ar"

        # 1. Provide INSTANT visual feedback: popup window appears immediately in loading state
        self.floating_window.show_loading(
            source_text=text_to_translate,
            source_lang=src_lang,
            target_lang=tgt_lang,
            max_ratio=cfg.floating_max_screen_ratio,
        )

        self.engine.set_model_path(model_dir)

        # 2. Safely wait if previous floating worker is still active
        if self.floating_worker and self.floating_worker.isRunning():
            self.floating_worker.wait(150)

        # 3. Store reference on self and pass parent=self to prevent garbage collection!
        self.floating_worker = TranslationWorker(
            engine=self.engine,
            text=text_to_translate,
            source_lang=src_lang,
            target_lang=tgt_lang,
            parent=self,
        )

        def on_done(res: TranslationResult) -> None:
            self.floating_window.display_translation(
                res.source_text,
                res.translated_text,
                res.source_lang,
                res.target_lang,
                max_ratio=cfg.floating_max_screen_ratio,
            )
            if cfg.history_enabled:
                self.history_service.record_translation(
                    res.source_text,
                    res.translated_text,
                    res.source_lang,
                    res.target_lang,
                    res.model_name,
                )

        def on_fail(err: str) -> None:
            self.floating_window.display_error(
                source_text=text_to_translate,
                error_msg=err,
                max_ratio=cfg.floating_max_screen_ratio,
            )

        self.floating_worker.translation_finished.connect(on_done)
        self.floating_worker.translation_failed.connect(on_fail)
        self.floating_worker.start()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.config_manager.config.minimize_to_tray:
            event.ignore()
            self.hide()
            self.statusBar().showMessage("App is running in the background system tray.", 3000)
        else:
            for w in (self.translation_worker, self.file_worker, getattr(self, "floating_worker", None)):
                if w and w.isRunning():
                    w.wait(500)
            event.accept()
