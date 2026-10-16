"""
Smart Floating Translation Window.
Positions near mouse cursor, auto-resizes to content up to 1/3 screen area,
clamps to screen bounds, uses real graphical icons, and supports RTL/LTR layouts.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtGui import QCursor, QFont, QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from Localex.clipboard import default_clipboard
from Localex.paths import default_paths
from Localex.speech import default_speech
from Localex.ui.icons import get_icon
from Localex.ui.theme import STRINGS
from Localex.utils import (
    get_text_direction,
    is_arabic_script,
    set_label_direction,
    set_text_edit_content,
)

logger = logging.getLogger(__name__)


class FloatingTranslationWindow(QWidget):
    """
    Floating translation popup window appearing near cursor.
    """
    open_in_main_requested = Signal(str, str, str, str)
    closed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent, Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self._is_pinned = True
        self._drag_position = QPoint()
        self._src_text = ""
        self._tr_text = ""
        self._src_lang = "en"
        self._tgt_lang = "ar"
        self._ui_lang = "en"

        self._init_ui()

    def _init_ui(self) -> None:
        self.setObjectName("FloatingWindow")
        self.setMinimumSize(320, 180)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(1, 1, 1, 1)
        main_layout.setSpacing(0)

        # Outer bordered frame
        self.frame = QFrame(self)
        self.frame.setObjectName("FloatingFrame")
        self.frame.setStyleSheet("""
            QFrame#FloatingFrame {
                border: 2px solid #0078D4;
                
            }
        """)
        frame_layout = QVBoxLayout(self.frame)
        frame_layout.setContentsMargins(10, 8, 10, 8)
        frame_layout.setSpacing(6)

        # Header Bar (Draggable)
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        self.title_label = QLabel("Quick Translation")
        self.title_label.setStyleSheet("color: #0078D4; font-weight: bold; font-size: 13px;")

        self.lang_badge = QLabel("EN → AR")
        self.lang_badge.setStyleSheet("""
            border: 1px solid #0078D4;
            
            padding: 1px 6px;
            font-size: 11px;
            font-weight: 600;
        """)

        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.lang_badge)
        header_layout.addStretch()

        # Action Buttons in header with real icons
        self.btn_pin = QPushButton()
        self.btn_pin.setIcon(get_icon("pin"))
        self.btn_pin.setIconSize(QSize(16, 16))
        self.btn_pin.setFixedSize(26, 26)
        self.btn_pin.setToolTip("Pin on top")
        self.btn_pin.clicked.connect(self._toggle_pin)

        self.btn_speak = QPushButton()
        self.btn_speak.setIcon(get_icon("speaker"))
        self.btn_speak.setIconSize(QSize(16, 16))
        self.btn_speak.setFixedSize(26, 26)
        self.btn_speak.setToolTip("Listen")
        self.btn_speak.clicked.connect(self._speak_text)

        self.btn_copy = QPushButton()
        self.btn_copy.setIcon(get_icon("copy"))
        self.btn_copy.setIconSize(QSize(16, 16))
        self.btn_copy.setFixedSize(26, 26)
        self.btn_copy.setToolTip("Copy")
        self.btn_copy.clicked.connect(self._copy_translation)

        self.btn_open_main = QPushButton()
        self.btn_open_main.setIcon(get_icon("open"))
        self.btn_open_main.setIconSize(QSize(16, 16))
        self.btn_open_main.setFixedSize(26, 26)
        self.btn_open_main.setToolTip("Open in Main Window")
        self.btn_open_main.clicked.connect(self._on_open_in_main)

        self.btn_close = QPushButton()
        self.btn_close.setIcon(get_icon("close"))
        self.btn_close.setIconSize(QSize(16, 16))
        self.btn_close.setFixedSize(26, 26)
        self.btn_close.setToolTip("Close")
        self.btn_close.clicked.connect(self.hide)

        for b in (self.btn_pin, self.btn_speak, self.btn_copy, self.btn_open_main, self.btn_close):
            b.setProperty("class", "icon-btn")
            header_layout.addWidget(b)

        frame_layout.addWidget(header)

        # Source text preview container with listen button
        src_box = QWidget()
        src_box_layout = QHBoxLayout(src_box)
        src_box_layout.setContentsMargins(0, 0, 0, 0)
        src_box_layout.setSpacing(4)

        self.src_preview = QLabel()
        self.src_preview.setStyleSheet("color: #888888; font-size: 11px; padding: 2px;")
        self.src_preview.setWordWrap(True)
        self.src_preview.setMaximumHeight(50)
        src_box_layout.addWidget(self.src_preview, stretch=1)

        self.btn_speak_src = QPushButton()
        self.btn_speak_src.setIcon(get_icon("speaker"))
        self.btn_speak_src.setIconSize(QSize(14, 14))
        self.btn_speak_src.setFixedSize(24, 24)
        self.btn_speak_src.setProperty("class", "icon-btn")
        self.btn_speak_src.setToolTip("Listen to original text")
        self.btn_speak_src.clicked.connect(self._speak_source_text)
        src_box_layout.addWidget(self.btn_speak_src, alignment=Qt.AlignTop)

        frame_layout.addWidget(src_box)

        # Translation text box
        self.tr_text_edit = QTextEdit()
        self.tr_text_edit.setReadOnly(True)
        self.tr_text_edit.setAcceptRichText(False)
        frame_layout.addWidget(self.tr_text_edit)


        # Bottom bar with size grip
        bottom_bar = QWidget()
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #888888; font-size: 10px;")
        bottom_layout.addWidget(self.status_label)
        bottom_layout.addStretch()

        size_grip = QSizeGrip(self)
        bottom_layout.addWidget(size_grip)
        frame_layout.addWidget(bottom_bar)

        main_layout.addWidget(self.frame)

    def apply_language(self, lang: str) -> None:
        self._ui_lang = lang
        is_ar = (lang == "ar")
        self.setLayoutDirection(Qt.RightToLeft if is_ar else Qt.LeftToRight)
        dic = STRINGS.get(lang, STRINGS["en"])
        self.title_label.setText(dic.get("floating_title", "Quick Translation"))
        self.btn_pin.setToolTip(dic.get("pin_tooltip", "Pin"))
        self.btn_speak.setToolTip(dic.get("listen_translation", "Listen to translation"))
        self.btn_speak_src.setToolTip(dic.get("listen_source", "Listen to source text"))
        self.btn_copy.setToolTip(dic.get("copy_tooltip", "Copy"))
        self.btn_open_main.setToolTip(dic.get("open_tooltip", "Open"))
        self.btn_close.setToolTip(dic.get("close_tooltip", "Close"))

    def apply_theme(self, theme_name: str) -> None:
        self.btn_pin.setIcon(get_icon("pin", theme=theme_name))
        self.btn_speak.setIcon(get_icon("speaker", theme=theme_name))
        self.btn_speak_src.setIcon(get_icon("speaker", theme=theme_name))
        self.btn_copy.setIcon(get_icon("copy", theme=theme_name))
        self.btn_open_main.setIcon(get_icon("open", theme=theme_name))
        self.btn_close.setIcon(get_icon("close", theme=theme_name))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self._drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def _toggle_pin(self) -> None:
        self._is_pinned = not self._is_pinned
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self._is_pinned)
        self.btn_pin.setStyleSheet("background-color: #333333;" if self._is_pinned else "")
        self.show()

    def _copy_translation(self) -> None:
        txt = self.tr_text_edit.toPlainText().strip()
        if txt:
            default_clipboard.set_text(txt)
            self.status_label.setText("Copied!" if self._ui_lang == "en" else "تم النسخ!")

    def _speak_source_text(self) -> None:
        txt = self._src_text.strip()
        if txt:
            default_speech.speak(txt)

    def _speak_text(self) -> None:
        txt = self.tr_text_edit.toPlainText().strip()
        if txt:
            default_speech.speak(txt)

    def _on_open_in_main(self) -> None:
        self.open_in_main_requested.emit(
            self._src_text, self._tr_text, self._src_lang, self._tgt_lang
        )
        self.hide()

    def show_loading(
        self,
        source_text: str,
        source_lang: str = "auto",
        target_lang: str = "ar",
        max_ratio: float = 0.33,
    ) -> None:
        self._src_text = source_text
        self._tr_text = ""
        self._src_lang = source_lang
        self._tgt_lang = target_lang

        self.lang_badge.setText(f"{source_lang.upper()} → {target_lang.upper()}")

        snippet = (source_text[:120] + "...") if len(source_text) > 120 else source_text
        set_label_direction(self.src_preview, snippet, is_arabic=is_arabic_script(snippet))

        loading_msg = "جاري الترجمة..." if (target_lang == "ar") else "Translating..."
        is_tgt_ar = (target_lang == "ar")
        set_text_edit_content(self.tr_text_edit, loading_msg, is_arabic=is_tgt_ar)

        chars_word = "chars" if self._ui_lang == "en" else "حرف"
        status_txt = f"{len(source_text)} {chars_word}  |  جاري المعالجة..." if self._ui_lang == "ar" else f"{len(source_text)} {chars_word}  |  Processing..."
        self.status_label.setText(status_txt)

        self._position_and_size(source_text, loading_msg, max_ratio)
        self.show()
        self.raise_()
        self.activateWindow()

    def display_error(self, source_text: str, error_msg: str, max_ratio: float = 0.33) -> None:
        self._src_text = source_text
        snippet = (source_text[:120] + "...") if len(source_text) > 120 else source_text
        set_label_direction(self.src_preview, snippet, is_arabic=is_arabic_script(snippet))
        set_text_edit_content(self.tr_text_edit, f"Error: {error_msg}", is_arabic=False)
        self.status_label.setText("خطأ في الترجمة" if self._ui_lang == "ar" else "Translation Error")
        self._position_and_size(source_text, error_msg, max_ratio)
        self.show()
        self.raise_()
        self.activateWindow()

    def display_translation(
        self,
        source_text: str,
        translated_text: str,
        source_lang: str,
        target_lang: str,
        max_ratio: float = 0.33,
    ) -> None:
        self._src_text = source_text
        self._tr_text = translated_text
        self._src_lang = source_lang
        self._tgt_lang = target_lang

        self.lang_badge.setText(f"{source_lang.upper()} → {target_lang.upper()}")

        snippet = (source_text[:120] + "...") if len(source_text) > 120 else source_text
        set_label_direction(self.src_preview, snippet, is_arabic=is_arabic_script(snippet))

        is_tr_ar = (
            (target_lang == "ar")
            or is_arabic_script(translated_text)
            or (get_text_direction(translated_text) == "rtl")
        )
        set_text_edit_content(self.tr_text_edit, translated_text, is_arabic=is_tr_ar)

        chars_word = "chars" if self._ui_lang == "en" else "حرف"
        self.status_label.setText(f"{len(source_text)} {chars_word}")

        self._position_and_size(source_text, translated_text, max_ratio)
        self.show()
        self.raise_()
        self.activateWindow()

    def _position_and_size(self, source_text: str, translated_text: str, max_ratio: float) -> None:
        cursor_pos = QCursor.pos()
        screen = QGuiApplication.screenAt(cursor_pos) or QGuiApplication.primaryScreen()
        if not screen:
            self.resize(380, 240)
            self.show()
            return

        geom = screen.availableGeometry()
        max_w = int(geom.width() * max_ratio)
        max_h = int(geom.height() * max_ratio)

        content_len = max(len(source_text), len(translated_text))
        if content_len < 80:
            target_w, target_h = 360, 190
        elif content_len < 250:
            target_w, target_h = 420, 260
        elif content_len < 600:
            target_w, target_h = min(500, max_w), min(340, max_h)
        else:
            target_w, target_h = max_w, max_h

        self.resize(target_w, target_h)

        target_x = cursor_pos.x() + 15
        target_y = cursor_pos.y() + 15

        if target_x + target_w > geom.right():
            target_x = max(geom.left(), cursor_pos.x() - target_w - 15)

        if target_y + target_h > geom.bottom():
            target_y = max(geom.top(), cursor_pos.y() - target_h - 15)

        self.move(target_x, target_y)
