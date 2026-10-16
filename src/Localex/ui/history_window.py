"""
History Window for inspecting, filtering, searching, exporting, and managing local translations.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from Localex.clipboard import default_clipboard
from Localex.history import HistoryService, default_history_service
from Localex.speech import default_speech
from Localex.ui.theme import STRINGS
from Localex.utils import is_arabic_script, set_text_edit_content

from Localex.ui.icons import get_icon

logger = logging.getLogger(__name__)


class HistoryWindow(QDialog):
    """
    Dialog for searching and managing translation history.
    """
    retranslate_requested = Signal(str, str, str)  # text, src_lang, tgt_lang

    def __init__(
        self,
        history_service: Optional[HistoryService] = None,
        ui_language: str = "en",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.history_service = history_service or default_history_service
        self.ui_language = ui_language
        self._items: list[dict] = []

        self._init_ui()
        self._load_data()

    def _tr(self, key: str) -> str:
        return STRINGS.get(self.ui_language, STRINGS["en"]).get(key, key)

    def _init_ui(self) -> None:
        self.setWindowTitle(self._tr("history_title"))
        self.resize(880, 580)
        self.setWindowIcon(get_icon("history"))
        self.setLayoutDirection(Qt.RightToLeft if self.ui_language == "ar" else Qt.LeftToRight)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Filter bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self._tr("search_placeholder"))
        self.search_input.textChanged.connect(self._on_filter_changed)
        filter_bar.addWidget(self.search_input, stretch=3)

        self.lang_filter = QComboBox()
        self.lang_filter.addItems([
            self._tr("filter_all"),
            self._tr("filter_ar_en"),
            self._tr("filter_en_ar"),
        ])
        self.lang_filter.currentIndexChanged.connect(self._on_filter_changed)
        filter_bar.addWidget(self.lang_filter, stretch=1)

        self.btn_refresh = QPushButton("  " + self._tr("refresh"))
        self.btn_refresh.setIcon(get_icon("retranslate"))
        self.btn_refresh.setIconSize(QSize(14, 14))
        self.btn_refresh.setProperty("class", "secondary")
        self.btn_refresh.clicked.connect(self._load_data)
        filter_bar.addWidget(self.btn_refresh)

        layout.addLayout(filter_bar)

        # Splitter: Table on left/top, Details on right/bottom
        splitter = QSplitter(Qt.Horizontal)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            self._tr("col_datetime"),
            self._tr("col_langs"),
            self._tr("col_source"),
            self._tr("col_target"),
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self.table)

        # Details Panel
        details_panel = QWidget()
        details_layout = QVBoxLayout(details_panel)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(6)

        self.lbl_det_src = QLabel(f"<b>{self._tr('source_label')}</b>")
        details_layout.addWidget(self.lbl_det_src)
        self.detail_src = QTextEdit()
        self.detail_src.setReadOnly(True)
        self.detail_src.setMaximumHeight(160)
        details_layout.addWidget(self.detail_src)

        self.lbl_det_tgt = QLabel(f"<b>{self._tr('target_label')}</b>")
        details_layout.addWidget(self.lbl_det_tgt)
        self.detail_tgt = QTextEdit()
        self.detail_tgt.setReadOnly(True)
        details_layout.addWidget(self.detail_tgt)

        # Details Action buttons
        d_actions = QHBoxLayout()
        self.btn_copy_tgt = QPushButton("  " + self._tr("copy"))
        self.btn_copy_tgt.setIcon(get_icon("copy"))
        self.btn_copy_tgt.setIconSize(QSize(14, 14))
        self.btn_copy_tgt.clicked.connect(self._copy_current_translation)
        d_actions.addWidget(self.btn_copy_tgt)

        self.btn_speak = QPushButton("  " + self._tr("listen"))
        self.btn_speak.setIcon(get_icon("speaker"))
        self.btn_speak.setIconSize(QSize(14, 14))
        self.btn_speak.setProperty("class", "secondary")
        self.btn_speak.clicked.connect(self._speak_current)
        d_actions.addWidget(self.btn_speak)

        self.btn_retranslate = QPushButton("  " + self._tr("retranslate"))
        self.btn_retranslate.setIcon(get_icon("swap"))
        self.btn_retranslate.setIconSize(QSize(14, 14))
        self.btn_retranslate.setProperty("class", "secondary")
        self.btn_retranslate.clicked.connect(self._retranslate_current)
        d_actions.addWidget(self.btn_retranslate)

        self.btn_delete_item = QPushButton("  " + self._tr("btn_delete"))
        self.btn_delete_item.setIcon(get_icon("clear"))
        self.btn_delete_item.setIconSize(QSize(14, 14))
        self.btn_delete_item.setProperty("class", "danger")
        self.btn_delete_item.clicked.connect(self._delete_current_item)
        d_actions.addWidget(self.btn_delete_item)

        details_layout.addLayout(d_actions)
        splitter.addWidget(details_panel)
        splitter.setSizes([500, 350])

        layout.addWidget(splitter)

        # Bottom Bar: Export / Import / Clear All
        bottom = QHBoxLayout()
        self.btn_export_csv = QPushButton("  " + self._tr("btn_export_csv"))
        self.btn_export_csv.setIcon(get_icon("file"))
        self.btn_export_csv.setIconSize(QSize(14, 14))
        self.btn_export_csv.setProperty("class", "secondary")
        self.btn_export_csv.clicked.connect(self._export_csv)
        bottom.addWidget(self.btn_export_csv)

        self.btn_export_txt = QPushButton("  " + self._tr("btn_export_txt"))
        self.btn_export_txt.setIcon(get_icon("file"))
        self.btn_export_txt.setIconSize(QSize(14, 14))
        self.btn_export_txt.setProperty("class", "secondary")
        self.btn_export_txt.clicked.connect(self._export_txt)
        bottom.addWidget(self.btn_export_txt)

        self.btn_import_csv = QPushButton("  " + self._tr("btn_import_csv"))
        self.btn_import_csv.setIcon(get_icon("open"))
        self.btn_import_csv.setIconSize(QSize(14, 14))
        self.btn_import_csv.setProperty("class", "secondary")
        self.btn_import_csv.clicked.connect(self._import_csv)
        bottom.addWidget(self.btn_import_csv)

        bottom.addStretch()

        self.btn_clear_all = QPushButton("  " + self._tr("btn_clear_all"))
        self.btn_clear_all.setIcon(get_icon("clear"))
        self.btn_clear_all.setIconSize(QSize(14, 14))
        self.btn_clear_all.setProperty("class", "danger")
        self.btn_clear_all.clicked.connect(self._clear_all)
        bottom.addWidget(self.btn_clear_all)

        btn_close = QPushButton("  " + self._tr("close_tooltip"))
        btn_close.setIcon(get_icon("close"))
        btn_close.setIconSize(QSize(14, 14))
        btn_close.clicked.connect(self.accept)
        bottom.addWidget(btn_close)

        layout.addLayout(bottom)

    def _load_data(self) -> None:
        query = self.search_input.text().strip()
        lang_idx = self.lang_filter.currentIndex()
        src_l = None
        tgt_l = None
        if lang_idx == 1:
            src_l, tgt_l = "ar", "en"
        elif lang_idx == 2:
            src_l, tgt_l = "en", "ar"

        self._items = self.history_service.get_items(
            query=query,
            source_lang=src_l,
            target_lang=tgt_l,
            limit=500,
        )

        self.table.setRowCount(len(self._items))
        for row_idx, item in enumerate(self._items):
            dt_item = QTableWidgetItem(str(item.get("created_at", "")))
            lang_str = f"{item.get('source_lang', '').upper()} → {item.get('target_lang', '').upper()}"
            lang_item = QTableWidgetItem(lang_str)

            src_item = QTableWidgetItem(item.get("source_text", "").replace("\n", " ")[:60])
            tgt_item = QTableWidgetItem(item.get("translated_text", "").replace("\n", " ")[:60])

            self.table.setItem(row_idx, 0, dt_item)
            self.table.setItem(row_idx, 1, lang_item)
            self.table.setItem(row_idx, 2, src_item)
            self.table.setItem(row_idx, 3, tgt_item)

        if self._items:
            self.table.selectRow(0)

    def _on_filter_changed(self) -> None:
        self._load_data()

    def _on_selection_changed(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self._items):
            item = self._items[row]
            src = item.get("source_text", "")
            tgt = item.get("translated_text", "")
            set_text_edit_content(self.detail_src, src)
            set_text_edit_content(self.detail_tgt, tgt)
        else:
            self.detail_src.clear()
            self.detail_tgt.clear()

    def _copy_current_translation(self) -> None:
        txt = self.detail_tgt.toPlainText().strip()
        if txt:
            default_clipboard.set_text(txt)
            QMessageBox.information(self, "تم النسخ", "تم نسخ الترجمة إلى الحافظة بنجاح.")

    def _speak_current(self) -> None:
        txt = self.detail_tgt.toPlainText().strip()
        if txt:
            default_speech.speak(txt)

    def _retranslate_current(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self._items):
            item = self._items[row]
            self.retranslate_requested.emit(
                item.get("source_text", ""),
                item.get("source_lang", "auto"),
                item.get("target_lang", "ar"),
            )
            self.accept()

    def _delete_current_item(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self._items):
            item = self._items[row]
            confirm = QMessageBox.question(
                self,
                "تأكيد الحذف",
                "هل أنت متأكد من حذف هذا السجل نهائياً؟",
                QMessageBox.Yes | QMessageBox.No,
            )
            if confirm == QMessageBox.Yes:
                self.history_service.delete_item(item["id"])
                self._load_data()

    def _clear_all(self) -> None:
        confirm = QMessageBox.warning(
            self,
            "تأكيد مسح السجل",
            "تحذير: سيتم مسح كامل سجل الترجمات المحفوظة محلياً.\nهل تريد المتابعة؟",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            self.history_service.clear()
            self._load_data()

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "تصدير السجل كملف CSV", "translations_history.csv", "CSV Files (*.csv)")
        if path:
            count = self.history_service.export_csv(path)
            QMessageBox.information(self, "تم التصدير", f"تم تصدير {count} عنصر بنجاح إلى ملف CSV.")

    def _export_txt(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "تصدير السجل كملف TXT", "translations_history.txt", "Text Files (*.txt)")
        if path:
            count = self.history_service.export_txt(path)
            QMessageBox.information(self, "تم التصدير", f"تم تصدير {count} عنصر بنجاح إلى ملف TXT.")

    def _import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "استيراد سجل من ملف CSV", "", "CSV Files (*.csv)")
        if path:
            try:
                count = self.history_service.import_csv(path)
                QMessageBox.information(self, "تم الاستيراد", f"تم استيراد {count} سجل ترجمة بنجاح.")
                self._load_data()
            except Exception as e:
                QMessageBox.critical(self, "فشل الاستيراد", f"حدث خطأ أثناء قراءة الملف: {e}")
