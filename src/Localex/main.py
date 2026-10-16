"""
Main entry point and application orchestrator for Offline Windows Translator.
Handles single-instance locks, Qt loop, hotkey listener, logging, and startup checks.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path

# Prevent Intel MKL memory allocation errors (mkl_malloc: failed to allocate memory)
os.environ.setdefault("CT2_PACKED_GEMM", "0")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from PySide6.QtCore import Qt
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox

from Localex.clipboard import default_clipboard
from Localex.config import ConfigManager
from Localex.history import default_history_service
from Localex.model_manager import ModelManager, ModelStatus
from Localex.paths import default_paths, test_write_permission
from Localex.shortcuts import default_shortcuts
from Localex.speech import default_speech
from Localex.translator import TranslationEngine
from Localex.tray import AppTrayIcon
from Localex.ui.main_window import MainWindow

SINGLE_INSTANCE_SERVER = "OfflineWindowsTranslator_SingleInstance"


def setup_logging(log_file: Path) -> None:
    """Configures rotating file logging without logging private user text."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)


class SingleInstanceGuard:
    """Ensures only a single instance of the application runs at any time."""

    def __init__(self, on_activate_callback) -> None:
        self.server: QLocalServer | None = None
        self.on_activate = on_activate_callback

    def try_lock(self) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(SINGLE_INSTANCE_SERVER)
        if socket.waitForConnected(500):
            # Another instance is already running
            socket.write(b"ACTIVATE")
            socket.waitForBytesWritten(500)
            socket.disconnectFromServer()
            return False

        # Start our local server
        self.server = QLocalServer()
        QLocalServer.removeServer(SINGLE_INSTANCE_SERVER)
        self.server.listen(SINGLE_INSTANCE_SERVER)
        self.server.newConnection.connect(self._handle_connection)
        return True

    def _handle_connection(self) -> None:
        if self.server:
            conn = self.server.nextPendingConnection()
            if conn:
                conn.waitForReadyRead(500)
                msg = conn.readAll().data().decode("utf-8", errors="ignore")
                if "ACTIVATE" in msg:
                    self.on_activate()
                conn.disconnectFromServer()


def main() -> int:
    # High-DPI and Qt attributes
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Localex")
    app.setOrganizationName("Localex")
    app.setQuitOnLastWindowClosed(False)

    # Initialize Logging
    setup_logging(default_paths.log_file_path)
    logging.info("Starting Offline Windows Translator...")

    # Load Config & Path Verification
    config_mgr = ConfigManager()
    cfg = config_mgr.config

    if not default_paths.is_app_dir_writable:
        logging.warning("Application folder is not writable. Checking fallback directory.")

    # Initialize Core Services
    model_mgr = ModelManager(default_paths.models_dir)
    engine = TranslationEngine(
        cpu_threads=cfg.cpu_threads,
        beam_size=cfg.beam_size,
        batch_size=cfg.batch_size,
    )
    history_svc = default_history_service

    # Single-Instance Lock
    main_window: MainWindow | None = None

    def on_second_instance_activated():
        if main_window:
            main_window.show()
            main_window.raise_()
            main_window.activateWindow()

    guard = SingleInstanceGuard(on_second_instance_activated)
    if not guard.try_lock():
        logging.info("Another instance is running. Activating existing instance and exiting.")
        return 0

    # Build Main Window
    main_window = MainWindow(
        config_manager=config_mgr,
        model_manager=model_mgr,
        engine=engine,
        history_service=history_svc,
    )

    # System Tray Icon
    tray_icon: AppTrayIcon | None = None
    if cfg.show_tray_icon:
        tray_icon = AppTrayIcon(app)
        tray_icon.show_main_window_requested.connect(on_second_instance_activated)
        tray_icon.open_models_requested.connect(main_window.open_model_manager)
        tray_icon.open_history_requested.connect(main_window.open_history)
        tray_icon.open_settings_requested.connect(main_window.open_settings)
        tray_icon.stop_tts_requested.connect(default_speech.stop)

        def on_tray_quick_tr():
            text = default_clipboard.get_text()
            if text:
                main_window.trigger_floating_translation(text)
            else:
                on_second_instance_activated()

        tray_icon.trigger_quick_translate_requested.connect(on_tray_quick_tr)

        def on_quit():
            default_shortcuts.unregister_all()
            default_speech.stop()
            app.quit()

        tray_icon.quit_requested.connect(on_quit)
        tray_icon.show()

    # Global Hotkey Callback
    def on_global_hotkey_pressed():
        if not cfg.global_shortcut_enabled:
            return
        logging.info("Global hotkey triggered.")
        # Capture selection via simulated Ctrl+C
        selected = default_clipboard.capture_selected_text(
            delay_ms=cfg.clipboard_capture_delay_ms,
            restore_previous=cfg.clipboard_restore_previous,
        )
        if selected and selected.strip():
            main_window.trigger_floating_translation(selected.strip())
        else:
            # If no text selected, pop open main window or floating window with clipboard text
            clip_txt = default_clipboard.get_text()
            if clip_txt and clip_txt.strip():
                main_window.trigger_floating_translation(clip_txt.strip())
            else:
                on_second_instance_activated()

    # Register Global Shortcut
    if cfg.global_shortcut_enabled and cfg.global_shortcut:
        default_shortcuts.initialize(int(main_window.winId()))
        success, hk_id, err = default_shortcuts.register(
            cfg.global_shortcut, on_global_hotkey_pressed
        )
        if not success:
            logging.warning(f"Could not register global hotkey: {err}")

    # Check start arguments (e.g. --tray)
    start_in_tray = "--tray" in sys.argv
    if not start_in_tray:
        main_window.show()

    # First run onboarding check
    if not cfg.first_run_completed:
        status = model_mgr.get_model_status(cfg.active_model_id)
        if status != ModelStatus.INSTALLED:
            ans = QMessageBox.information(
                main_window,
                "مرحباً بك في المترجم الفوري المستقل",
                "يعمل البرنامج دون اتصال بالإنترنت بنسبة 100% بعد توفير نموذج الترجمة.\n\n"
                "حزمة البرنامج خفيفة ولا تتضمن نماذج الترجمة الكبيرة مسبقاً.\n"
                "هل ترغب في فتح صفحة إدارة النماذج لتنزيل النموذج الأساسي (NLLB-200 INT8) الآن بنقرة واحدة؟",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ans == QMessageBox.Yes:
                main_window.open_model_manager()

        cfg.first_run_completed = True
        config_mgr.save()

    exit_code = app.exec()

    # Cleanup on exit
    default_shortcuts.unregister_all()
    default_speech.stop()
    if main_window:
        for w in (main_window.translation_worker, main_window.file_worker, getattr(main_window, "floating_worker", None)):
            if w and w.isRunning():
                w.wait(500)
    engine.unload()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
