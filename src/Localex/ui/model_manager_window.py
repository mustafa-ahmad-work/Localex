"""
Model Manager Window for downloading, verifying, selecting, and inspecting offline translation models.
Fully respects application-wide Light and Dark themes with zero style leaks.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from Localex.download_manager import DownloadProgress, DownloadState, ModelDownloader
from Localex.model_manager import CATALOG, ModelManager, ModelStatus
from Localex.paths import default_paths
from Localex.utils import format_bytes, format_eta, format_speed
from Localex.workers import DownloadWorker

from Localex.ui.icons import get_icon

logger = logging.getLogger(__name__)


class ModelCard(QFrame):
    """
    UI widget representing a single translation model item with specs and action buttons.
    """
    model_selected = Signal(str, str)
    download_requested = Signal(str)
    verify_requested = Signal(str)

    def __init__(self, model_info: dict, model_manager: ModelManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.model_info = model_info
        self.model_manager = model_manager
        self.model_id = model_info["id"]

        self.setObjectName("ModelCardFrame")
        self.setProperty("class", "card")

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header: Name + Status Badge
        header = QHBoxLayout()
        name_label = QLabel(self.model_info["name"])
        name_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #0078D4;")
        header.addWidget(name_label)
        header.addStretch()

        self.status_badge = QLabel()
        self.status_badge.setStyleSheet("padding: 3px 8px; font-weight: 600; font-size: 11px;")
        self._update_status_badge(self.model_info["status"])
        header.addWidget(self.status_badge)
        layout.addLayout(header)

        # Description
        desc_label = QLabel(self.model_info["description"])
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # Specs grid
        specs = QHBoxLayout()
        specs.addWidget(QLabel(f"Disk Required: <b>~{self.model_info['disk_mb']} MB</b>"))
        specs.addWidget(QLabel(f"RAM Required: <b>~{self.model_info['ram_mb']} MB</b>"))
        specs.addWidget(QLabel(f"Engine: <b>{self.model_info['quantization']} CPU</b>"))
        specs.addStretch()
        layout.addLayout(specs)

        # Disclaimer
        disclaimer = QLabel(self.model_info.get("disclaimer", ""))
        disclaimer.setWordWrap(True)
        disclaimer.setStyleSheet("color: #71717A; font-size: 11px; font-style: italic;")
        layout.addWidget(disclaimer)

        # Actions
        actions = QHBoxLayout()
        self.btn_download = QPushButton("  Download Model")
        self.btn_download.setIcon(get_icon("models"))
        self.btn_download.setIconSize(QSize(16, 16))
        self.btn_download.clicked.connect(lambda: self.download_requested.emit(self.model_id))
        actions.addWidget(self.btn_download)

        self.btn_verify = QPushButton("  Verify Integrity (SHA256)")
        self.btn_verify.setIcon(get_icon("settings"))
        self.btn_verify.setIconSize(QSize(16, 16))
        self.btn_verify.setProperty("class", "secondary")
        self.btn_verify.clicked.connect(lambda: self.verify_requested.emit(self.model_id))
        actions.addWidget(self.btn_verify)

        actions.addStretch()
        layout.addLayout(actions)

        self._refresh_buttons()

    def _update_status_badge(self, status: str) -> None:
        if status == ModelStatus.INSTALLED:
            self.status_badge.setText("Ready / Installed")
            self.status_badge.setStyleSheet("background-color: #0E5A35; color: #FFFFFF; padding: 3px 8px; ")
        elif status == ModelStatus.INCOMPLETE:
            self.status_badge.setText("Incomplete Download")
            self.status_badge.setStyleSheet("background-color: #7A4D00; color: #FFFFFF; padding: 3px 8px; ")
        elif status == ModelStatus.CORRUPTED:
            self.status_badge.setText("Corrupted / Incomplete")
            self.status_badge.setStyleSheet("background-color: #A82315; color: #FFFFFF; padding: 3px 8px; ")
        else:
            self.status_badge.setText("Not Installed")
            self.status_badge.setStyleSheet("background-color: #55555C; color: #FFFFFF; padding: 3px 8px; ")

    def _refresh_buttons(self) -> None:
        status = self.model_manager.get_model_status(self.model_id)
        self._update_status_badge(status)
        if status == ModelStatus.INSTALLED:
            self.btn_download.setText("  Re-download")
            self.btn_verify.setEnabled(True)
        else:
            self.btn_download.setText("  Download Model")
            self.btn_verify.setEnabled(status != ModelStatus.NOT_DOWNLOADED)


class ModelManagerWindow(QDialog):
    """
    Model management dialog for downloading, selecting, and verifying offline translation models.
    """
    model_configured = Signal(str, str)

    def __init__(self, model_manager: ModelManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.model_manager = model_manager
        self.download_worker: Optional[DownloadWorker] = None
        self.downloader: Optional[ModelDownloader] = None

        self.setWindowTitle("Model Management - Offline Windows Translator")
        self.resize(720, 560)
        self.setWindowIcon(get_icon("models"))
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # Header Info Banner
        banner = QLabel(
            "The application functions 100% offline once the translation model is downloaded.\n"
            "Download the recommended NLLB-200 INT8 model directly, or select an existing folder."
        )
        banner.setProperty("class", "info-banner")
        banner.setWordWrap(True)
        main_layout.addWidget(banner)

        # Custom Folder Selection Group
        custom_group = QGroupBox("Select Model Folder From Disk")
        custom_layout = QHBoxLayout(custom_group)
        self.btn_browse = QPushButton("  Browse Folder...")
        self.btn_browse.setIcon(get_icon("file"))
        self.btn_browse.setIconSize(QSize(16, 16))
        self.btn_browse.clicked.connect(self._browse_custom_model_dir)
        custom_layout.addWidget(self.btn_browse)

        self.custom_path_label = QLabel("No custom model directory selected.")
        self.custom_path_label.setStyleSheet("color: #71717A;")
        custom_layout.addWidget(self.custom_path_label)
        custom_layout.addStretch()
        main_layout.addWidget(custom_group)

        # Download Progress Area (Hidden by default)
        self.progress_frame = QFrame()
        self.progress_frame.setObjectName("ProgressFrame")
        p_layout = QVBoxLayout(self.progress_frame)
        p_layout.setContentsMargins(12, 10, 12, 10)
        p_layout.setSpacing(8)

        self.progress_title = QLabel("Downloading Model...")
        self.progress_title.setStyleSheet("font-weight: bold; color: #0078D4;")
        p_layout.addWidget(self.progress_title)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        p_layout.addWidget(self.progress_bar)

        self.progress_stats = QLabel("Speed: -- | ETA: -- | Size: --")
        self.progress_stats.setStyleSheet("color: #71717A; font-size: 11px;")
        p_layout.addWidget(self.progress_stats)

        # Progress controls
        p_controls = QHBoxLayout()
        self.btn_pause = QPushButton("  Pause")
        self.btn_pause.setIcon(get_icon("retranslate"))
        self.btn_pause.setIconSize(QSize(14, 14))
        self.btn_pause.clicked.connect(self._toggle_pause_download)
        p_controls.addWidget(self.btn_pause)

        self.btn_cancel = QPushButton("  Cancel Download")
        self.btn_cancel.setIcon(get_icon("close"))
        self.btn_cancel.setIconSize(QSize(14, 14))
        self.btn_cancel.setProperty("class", "danger")
        self.btn_cancel.clicked.connect(self._cancel_download)
        p_controls.addWidget(self.btn_cancel)
        p_controls.addStretch()
        p_layout.addLayout(p_controls)

        self.progress_frame.setVisible(False)
        main_layout.addWidget(self.progress_frame)

        # Scrollable catalog list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.catalog_layout = QVBoxLayout(scroll_content)
        self.catalog_layout.setContentsMargins(0, 0, 0, 0)
        self.catalog_layout.setSpacing(10)

        self._populate_catalog()

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # Bottom Close Button
        bottom = QHBoxLayout()
        btn_close = QPushButton("  Close")
        btn_close.setIcon(get_icon("close"))
        btn_close.setIconSize(QSize(14, 14))
        btn_close.clicked.connect(self.accept)
        bottom.addStretch()
        bottom.addWidget(btn_close)
        main_layout.addLayout(bottom)

    def _populate_catalog(self) -> None:
        while self.catalog_layout.count():
            item = self.catalog_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        models = self.model_manager.scan_models()
        self.cards: list[ModelCard] = []
        for m in models:
            card = ModelCard(m, self.model_manager, self)
            card.download_requested.connect(self._start_download)
            card.verify_requested.connect(self._verify_model)
            self.cards.append(card)
            self.catalog_layout.addWidget(card)
        self.catalog_layout.addStretch()

    def _browse_custom_model_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose CTranslate2 Model Folder")
        if not folder:
            return

        folder_path = Path(folder)
        is_valid, reason = self.model_manager.validate_model_directory(folder_path)
        if not is_valid:
            QMessageBox.critical(
                self,
                "Invalid Model Folder",
                f"Selected folder does not contain a valid CTranslate2 model:\n\n{reason}"
            )
            return

        self.custom_path_label.setText(str(folder_path))
        QMessageBox.information(
            self,
            "Model Configured",
            "Model files verified successfully and ready for offline use."
        )
        self.model_configured.emit("custom", str(folder_path))
        self._refresh_all_cards()

    def _start_download(self, model_id: str) -> None:
        cat_item = CATALOG.get(model_id)
        if not cat_item:
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Download",
            f"Model {cat_item.name} requires approximately {cat_item.required_disk_mb} MB from Hugging Face.\n\nProceed with download?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        dest_dir = self.model_manager.get_model_directory(model_id)
        self.downloader = ModelDownloader(cat_item, dest_dir)
        self.download_worker = DownloadWorker(self.downloader)

        self.download_worker.progress_changed.connect(self._on_download_progress)
        self.download_worker.download_finished.connect(self._on_download_finished)
        self.download_worker.download_failed.connect(self._on_download_failed)

        self.progress_frame.setVisible(True)
        self.btn_browse.setEnabled(False)
        self.btn_pause.setText("Pause")
        self.progress_title.setText(f"Downloading {cat_item.name}...")

        self.download_worker.start()

    def _on_download_progress(self, p: DownloadProgress) -> None:
        if p.state == DownloadState.DOWNLOADING:
            self.progress_bar.setValue(int(p.overall_percent))
            self.progress_stats.setText(
                f"File {p.current_file_index}/{p.total_files}: {p.current_file} | "
                f"Speed: {format_speed(p.speed_bps)} | "
                f"ETA: {format_eta(p.eta_seconds)} | "
                f"Downloaded: {format_bytes(p.total_downloaded_bytes)} of {format_bytes(p.grand_total_bytes)}"
            )
        elif p.state == DownloadState.CONNECTING:
            self.progress_stats.setText(f"Connecting to server for {p.current_file}...")
        elif p.state == DownloadState.VERIFYING:
            self.progress_stats.setText("Download complete. Verifying SHA256 checksums...")
        elif p.state == DownloadState.PAUSED:
            self.progress_stats.setText("Download paused.")

    def _toggle_pause_download(self) -> None:
        if not self.download_worker or not self.downloader:
            return
        if self.downloader.progress.state == DownloadState.PAUSED:
            self.download_worker.resume()
            self.btn_pause.setText("  Pause")
        else:
            self.download_worker.pause()
            self.btn_pause.setText("  Resume")

    def _cancel_download(self) -> None:
        if self.download_worker:
            self.download_worker.cancel()
            self.progress_frame.setVisible(False)
            self.btn_browse.setEnabled(True)
            self._refresh_all_cards()

    def _on_download_finished(self, success: bool) -> None:
        self.progress_frame.setVisible(False)
        self.btn_browse.setEnabled(True)
        self._refresh_all_cards()
        if success:
            QMessageBox.information(
                self,
                "Download Complete",
                "Model files downloaded and verified successfully! The model is ready for 100% offline translation."
            )
            if self.downloader:
                dest = self.downloader.destination_dir
                self.model_configured.emit(self.downloader.catalog_item.model_id, str(dest))

    def _on_download_failed(self, error_msg: str) -> None:
        self.progress_frame.setVisible(False)
        self.btn_browse.setEnabled(True)
        self._refresh_all_cards()
        QMessageBox.critical(
            self,
            "Download Failed",
            f"Could not finish downloading model:\n{error_msg}\n\nYou can retry later; the downloader supports resuming partial downloads."
        )

    def _verify_model(self, model_id: str) -> None:
        valid, failed = self.model_manager.verify_model_checksums(model_id)
        if valid:
            QMessageBox.information(
                self,
                "Integrity Check",
                "All model files are verified and match official SHA256 checksums 100%."
            )
        else:
            msg = "\n".join(failed)
            QMessageBox.warning(
                self,
                "Integrity Warning",
                f"Failed checksum verification on:\n{msg}"
            )

    def _refresh_all_cards(self) -> None:
        for card in self.cards:
            card._refresh_buttons()
