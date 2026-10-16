"""
Settings Window for configuring languages, hotkeys, themes, speech synthesis, storage, and engine parameters.
"""

from __future__ import annotations

import logging
import winreg
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon


from Localex.config import ConfigManager
from Localex.paths import default_paths, test_write_permission
from Localex.shortcuts import default_shortcuts, parse_hotkey_string
from Localex.speech import default_speech
from Localex.ui.theme import STRINGS

from Localex.ui.icons import get_icon

logger = logging.getLogger(__name__)


WINDOWS_RUN_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "OfflineWindowsTranslator"


def set_run_at_startup(enable: bool, exe_path: str) -> bool:
    """Manages Windows startup registry entry for optional auto-launch."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, WINDOWS_RUN_REG_KEY, 0, winreg.KEY_ALL_ACCESS)
        if enable:
            winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, f'"{exe_path}" --tray')
        else:
            try:
                winreg.DeleteValue(key, APP_REG_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        logger.error(f"Failed to update startup registry key: {e}")
        return False


class SettingsWindow(QDialog):
    """
    Application Settings configuration dialog.
    """
    settings_saved = Signal()

    def __init__(self, config_manager: ConfigManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.config_manager = config_manager
        self.ui_language = getattr(self.config_manager.config, "ui_language", "en")
        self.setWindowTitle(self._tr("settings_title"))
        self.resize(680, 530)
        self.setWindowIcon(get_icon("settings"))
        self.setLayoutDirection(Qt.RightToLeft if self.ui_language == "ar" else Qt.LeftToRight)

        self._init_ui()
        self._load_from_config()

    def _tr(self, key: str) -> str:
        lang = getattr(self.config_manager.config, "ui_language", "en")
        return STRINGS.get(lang, STRINGS["en"]).get(key, key)

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        self.tabs = QTabWidget()

        # Tab 1: General & Appearance
        tab_general = QWidget()
        l_gen = QVBoxLayout(tab_general)

        g_lang = QGroupBox(self._tr("group_defaults"))
        f_lang = QFormLayout(g_lang)
        self.combo_src = QComboBox()
        self.combo_src.addItems([self._tr("auto_detect"), self._tr("arabic"), self._tr("english")])
        f_lang.addRow(self._tr("lbl_default_source"), self.combo_src)

        self.combo_tgt = QComboBox()
        self.combo_tgt.addItems([self._tr("arabic"), self._tr("english")])
        f_lang.addRow(self._tr("lbl_default_target"), self.combo_tgt)

        self.chk_auto_detect = QCheckBox(self._tr("chk_auto_detect"))
        f_lang.addRow("", self.chk_auto_detect)
        l_gen.addWidget(g_lang)

        g_ui = QGroupBox(self._tr("group_appearance"))
        f_ui = QFormLayout(g_ui)
        self.combo_theme = QComboBox()
        self.combo_theme.addItems([self._tr("theme_dark"), self._tr("theme_light")])
        f_ui.addRow(self._tr("lbl_theme"), self.combo_theme)

        self.spin_zoom = QSpinBox()
        self.spin_zoom.setRange(-4, 10)
        self.spin_zoom.setValue(0)
        self.spin_zoom.setSuffix(" pt")
        f_ui.addRow(self._tr("lbl_font_zoom"), self.spin_zoom)
        l_gen.addWidget(g_ui)
        l_gen.addStretch()
        self.tabs.addTab(tab_general, get_icon("settings"), self._tr("tab_general"))

        # Tab 2: Hotkey & Floating Window
        tab_hotkey = QWidget()
        l_hotkey = QVBoxLayout(tab_hotkey)

        g_hk = QGroupBox(self._tr("group_hotkey"))
        f_hk = QFormLayout(g_hk)

        self.chk_hk_enabled = QCheckBox(self._tr("chk_hotkey"))
        f_hk.addRow("", self.chk_hk_enabled)

        self.txt_hotkey = QLineEdit()
        self.txt_hotkey.setPlaceholderText("Ctrl+Alt+T")
        f_hk.addRow(self._tr("lbl_hotkey_key"), self.txt_hotkey)

        self.chk_restore_clip = QCheckBox(self._tr("chk_restore_clip"))
        f_hk.addRow("", self.chk_restore_clip)

        self.spin_clip_delay = QSpinBox()
        self.spin_clip_delay.setRange(50, 600)
        self.spin_clip_delay.setSuffix(" ms")
        self.spin_clip_delay.setValue(150)
        f_hk.addRow(self._tr("lbl_clip_delay"), self.spin_clip_delay)
        l_hotkey.addWidget(g_hk)

        g_float = QGroupBox(self._tr("group_floating"))
        f_float = QFormLayout(g_float)

        self.combo_float_pos = QComboBox()
        self.combo_float_pos.addItems([self._tr("float_pos_cursor"), self._tr("float_pos_center")])
        f_float.addRow(self._tr("lbl_float_pos"), self.combo_float_pos)

        self.slider_max_ratio = QSlider(Qt.Horizontal)
        self.slider_max_ratio.setRange(20, 50)
        self.slider_max_ratio.setValue(33)
        self.lbl_max_ratio = QLabel(self._tr("percent_screen").format(val=33))
        self.slider_max_ratio.valueChanged.connect(
            lambda v: self.lbl_max_ratio.setText(self._tr("percent_screen").format(val=v))
        )
        ratio_box = QHBoxLayout()
        ratio_box.addWidget(self.slider_max_ratio)
        ratio_box.addWidget(self.lbl_max_ratio)
        f_float.addRow(self._tr("lbl_max_size"), ratio_box)

        self.chk_float_pin = QCheckBox(self._tr("chk_float_pin"))
        f_float.addRow("", self.chk_float_pin)
        l_hotkey.addWidget(g_float)
        l_hotkey.addStretch()
        self.tabs.addTab(tab_hotkey, get_icon("pin"), self._tr("tab_hotkey"))

        # Tab 3: Text-To-Speech (TTS)
        tab_tts = QWidget()
        l_tts = QVBoxLayout(tab_tts)

        g_voice = QGroupBox(self._tr("group_voice"))
        f_voice = QFormLayout(g_voice)

        self.combo_voice = QComboBox()
        self._populate_voices()
        f_voice.addRow(self._tr("lbl_voice"), self.combo_voice)

        self.slider_speed = QSlider(Qt.Horizontal)
        self.slider_speed.setRange(-10, 10)
        self.slider_speed.setValue(0)
        self.lbl_speed = QLabel("0")
        self.slider_speed.valueChanged.connect(lambda v: self.lbl_speed.setText(str(v)))
        sp_box = QHBoxLayout()
        sp_box.addWidget(self.slider_speed)
        sp_box.addWidget(self.lbl_speed)
        f_voice.addRow(self._tr("lbl_speech_rate"), sp_box)

        self.slider_volume = QSlider(Qt.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(100)
        self.lbl_volume = QLabel("100%")
        self.slider_volume.valueChanged.connect(lambda v: self.lbl_volume.setText(f"{v}%"))
        vol_box = QHBoxLayout()
        vol_box.addWidget(self.slider_volume)
        vol_box.addWidget(self.lbl_volume)
        f_voice.addRow(self._tr("lbl_speech_volume"), vol_box)

        btn_test_speech = QPushButton("  " + self._tr("btn_test_voice"))
        btn_test_speech.setIcon(get_icon("speaker"))
        btn_test_speech.setIconSize(QSize(14, 14))
        btn_test_speech.setProperty("class", "secondary")
        btn_test_speech.clicked.connect(self._test_voice)
        f_voice.addRow("", btn_test_speech)

        tts_notice = QLabel(self._tr("tts_notice"))
        tts_notice.setStyleSheet("color: #888888; font-size: 11px; font-style: italic;")
        tts_notice.setWordWrap(True)
        f_voice.addRow("", tts_notice)

        l_tts.addWidget(g_voice)
        l_tts.addStretch()
        self.tabs.addTab(tab_tts, get_icon("speaker"), self._tr("tab_tts"))

        # Tab 4: Engine & Performance
        tab_engine = QWidget()
        l_eng = QVBoxLayout(tab_engine)

        g_perf = QGroupBox(self._tr("group_engine"))
        f_perf = QFormLayout(g_perf)

        self.spin_threads = QSpinBox()
        self.spin_threads.setRange(1, 32)
        self.spin_threads.setValue(4)
        f_perf.addRow(self._tr("lbl_cpu_threads"), self.spin_threads)

        self.combo_beam = QComboBox()
        self.combo_beam.addItem("1 (Greedy)", 1)
        self.combo_beam.addItem("2 (Balanced)", 2)
        self.combo_beam.addItem("4 (Accurate)", 4)
        f_perf.addRow(self._tr("lbl_beam_size"), self.combo_beam)

        self.spin_batch = QSpinBox()
        self.spin_batch.setRange(4, 64)
        self.spin_batch.setValue(16)
        f_perf.addRow("Batch Size:", self.spin_batch)

        l_eng.addWidget(g_perf)

        g_hist = QGroupBox(self._tr("history_title"))
        f_hist = QFormLayout(g_hist)
        self.chk_save_hist = QCheckBox(self._tr("chk_history_enabled"))
        f_hist.addRow("", self.chk_save_hist)

        self.spin_retention = QSpinBox()
        self.spin_retention.setRange(0, 365)
        self.spin_retention.setValue(0)
        self.spin_retention.setSpecialValueText("Never Delete")
        self.spin_retention.setSuffix(" days")
        f_hist.addRow("Retention:", self.spin_retention)
        l_eng.addWidget(g_hist)
        l_eng.addStretch()
        self.tabs.addTab(tab_engine, get_icon("translate"), self._tr("tab_engine"))

        # Tab 5: Storage & Portability
        tab_storage = QWidget()
        l_store = QVBoxLayout(tab_storage)

        g_path = QGroupBox(self._tr("group_storage"))
        f_path = QFormLayout(g_path)

        self.lbl_current_path = QLabel()
        self.lbl_current_path.setStyleSheet("font-family: Consolas; font-size: 12px; color: #0078D4;")
        f_path.addRow(self._tr("lbl_current_path"), self.lbl_current_path)

        self.lbl_perm_status = QLabel()
        f_path.addRow(self._tr("lbl_portable_status"), self.lbl_perm_status)

        btn_change_dir = QPushButton("  " + self._tr("btn_change_storage"))
        btn_change_dir.setIcon(get_icon("file"))
        btn_change_dir.setIconSize(QSize(14, 14))
        btn_change_dir.setProperty("class", "secondary")
        btn_change_dir.clicked.connect(self._choose_custom_data_dir)
        f_path.addRow("", btn_change_dir)

        p_info = QLabel(
            "Offline portable mode runs directly from the application folder.\n"
            "All settings, history database, and downloaded models are stored locally."
        )
        p_info.setWordWrap(True)
        p_info.setStyleSheet("color: #888888; font-size: 11px;")
        f_path.addRow("", p_info)

        l_store.addWidget(g_path)

        g_sys = QGroupBox("Windows Integration")
        f_sys = QFormLayout(g_sys)

        self.chk_startup = QCheckBox("Start with Windows")
        f_sys.addRow("", self.chk_startup)

        self.chk_tray = QCheckBox("Show System Tray Icon")
        f_sys.addRow("", self.chk_tray)

        self.chk_min_tray = QCheckBox("Minimize to Tray on Close")
        f_sys.addRow("", self.chk_min_tray)
        l_store.addWidget(g_sys)
        l_store.addStretch()
        self.tabs.addTab(tab_storage, get_icon("file"), self._tr("tab_storage"))

        main_layout.addWidget(self.tabs)

        # Bottom Buttons
        bottom = QHBoxLayout()
        btn_restore_def = QPushButton("  " + self._tr("btn_reset_storage"))
        btn_restore_def.setIcon(get_icon("clear"))
        btn_restore_def.setIconSize(QSize(14, 14))
        btn_restore_def.setProperty("class", "secondary")
        btn_restore_def.clicked.connect(self._restore_defaults)
        bottom.addWidget(btn_restore_def)
        bottom.addStretch()

        btn_save = QPushButton("  " + self._tr("btn_save"))
        btn_save.setIcon(get_icon("translate"))
        btn_save.setIconSize(QSize(14, 14))
        btn_save.setProperty("class", "primary")
        btn_save.clicked.connect(self._save_settings)
        bottom.addWidget(btn_save)

        btn_cancel = QPushButton("  " + self._tr("btn_cancel"))
        btn_cancel.setIcon(get_icon("close"))
        btn_cancel.setIconSize(QSize(14, 14))
        btn_cancel.clicked.connect(self.reject)
        bottom.addWidget(btn_cancel)

        main_layout.addLayout(bottom)

    def _populate_voices(self) -> None:
        self.combo_voice.clear()
        voices = default_speech.get_voices()
        for v in voices:
            self.combo_voice.addItem(v["name"], v["id"])
        if not voices:
            self.combo_voice.addItem("Default Windows Voice", "")

    def _test_voice(self) -> None:
        v_id = self.combo_voice.currentData()
        rate = self.slider_speed.value()
        vol = self.slider_volume.value()
        default_speech.speak("Hello, this is an offline voice test.", voice_id=v_id, rate=rate, volume=vol)

    def _choose_custom_data_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, self._tr("btn_change_storage"))
        if folder:
            p = Path(folder)
            if not test_write_permission(p):
                QMessageBox.critical(self, "Permission Error", "Directory is not writable.")
                return
            default_paths.set_custom_data_dir(p)
            self._update_storage_labels()

    def _update_storage_labels(self) -> None:
        self.lbl_current_path.setText(str(default_paths.base_data_dir))
        writable = test_write_permission(default_paths.base_data_dir)
        if writable:
            self.lbl_perm_status.setText(self._tr("status_writable"))
            self.lbl_perm_status.setStyleSheet("color: #107C41; font-weight: bold;")
        else:
            self.lbl_perm_status.setText(self._tr("status_readonly"))
            self.lbl_perm_status.setStyleSheet("color: #D13438; font-weight: bold;")

    def _load_from_config(self) -> None:
        cfg = self.config_manager.config

        # General
        src_map = {"auto": 0, "ar": 1, "en": 2}
        self.combo_src.setCurrentIndex(src_map.get(cfg.source_lang, 0))
        self.combo_tgt.setCurrentIndex(0 if cfg.target_lang == "ar" else 1)
        self.chk_auto_detect.setChecked(cfg.auto_detect)
        self.combo_theme.setCurrentIndex(0 if cfg.theme == "dark" else 1)
        self.spin_zoom.setValue(cfg.font_size_delta)

        # Hotkey
        self.chk_hk_enabled.setChecked(cfg.global_shortcut_enabled)
        self.txt_hotkey.setText(cfg.global_shortcut)
        self.chk_restore_clip.setChecked(cfg.clipboard_restore_previous)
        self.spin_clip_delay.setValue(cfg.clipboard_capture_delay_ms)
        self.combo_float_pos.setCurrentIndex(0 if cfg.floating_position == "cursor" else 1)
        ratio_int = int(cfg.floating_max_screen_ratio * 100)
        self.slider_max_ratio.setValue(ratio_int)
        self.chk_float_pin.setChecked(cfg.floating_pinned)

        # Speech
        if cfg.tts_voice_id:
            idx = self.combo_voice.findData(cfg.tts_voice_id)
            if idx >= 0:
                self.combo_voice.setCurrentIndex(idx)
        self.slider_speed.setValue(cfg.tts_rate)
        self.slider_volume.setValue(cfg.tts_volume)

        # Engine
        self.spin_threads.setValue(cfg.cpu_threads)
        idx = self.combo_beam.findData(cfg.beam_size)
        if idx >= 0:
            self.combo_beam.setCurrentIndex(idx)
        self.spin_batch.setValue(cfg.batch_size)
        self.chk_save_hist.setChecked(cfg.history_enabled)
        self.spin_retention.setValue(cfg.history_retention_days)

        # System & Startup
        self.chk_startup.setChecked(cfg.start_with_windows)
        self.chk_tray.setChecked(cfg.show_tray_icon)
        self.chk_min_tray.setChecked(cfg.minimize_to_tray)

        self._update_storage_labels()

    def _save_settings(self) -> None:
        # Validate Hotkey
        hk_str = self.txt_hotkey.text().strip()
        mods, vk = parse_hotkey_string(hk_str)
        if vk == 0:
            QMessageBox.critical(self, "خطأ في الاختصار", "صيغة مفتاح الاختصار العام غير صحيحة.")
            return

        cfg = self.config_manager.config
        cfg.source_lang = ["auto", "ar", "en"][self.combo_src.currentIndex()]
        cfg.target_lang = "ar" if self.combo_tgt.currentIndex() == 0 else "en"
        cfg.auto_detect = self.chk_auto_detect.isChecked()
        cfg.theme = "dark" if self.combo_theme.currentIndex() == 0 else "light"
        cfg.font_size_delta = self.spin_zoom.value()

        cfg.global_shortcut_enabled = self.chk_hk_enabled.isChecked()
        cfg.global_shortcut = hk_str
        cfg.clipboard_restore_previous = self.chk_restore_clip.isChecked()
        cfg.clipboard_capture_delay_ms = self.spin_clip_delay.value()
        cfg.floating_position = "cursor" if self.combo_float_pos.currentIndex() == 0 else "center"
        cfg.floating_max_screen_ratio = self.slider_max_ratio.value() / 100.0
        cfg.floating_pinned = self.chk_float_pin.isChecked()

        cfg.tts_voice_id = self.combo_voice.currentData()
        cfg.tts_rate = self.slider_speed.value()
        cfg.tts_volume = self.slider_volume.value()

        cfg.cpu_threads = self.spin_threads.value()
        cfg.beam_size = self.combo_beam.currentData()
        cfg.batch_size = self.spin_batch.value()
        cfg.history_enabled = self.chk_save_hist.isChecked()
        cfg.history_retention_days = self.spin_retention.value()

        cfg.start_with_windows = self.chk_startup.isChecked()
        cfg.show_tray_icon = self.chk_tray.isChecked()
        cfg.minimize_to_tray = self.chk_min_tray.isChecked()

        # Update Windows startup if toggled
        import sys
        exe_path = sys.executable if getattr(sys, "frozen", False) else str(default_paths.app_dir / "start.bat")
        set_run_at_startup(cfg.start_with_windows, exe_path)

        self.config_manager.save()
        self.settings_saved.emit()
        self.accept()

    def _restore_defaults(self) -> None:
        confirm = QMessageBox.question(
            self,
            "استعادة الافتراضيات",
            "هل تريد استعادة كافة الإعدادات إلى قيمها الافتراضية؟",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            from Localex.config import AppConfig
            self.config_manager.config = AppConfig()
            self._load_from_config()
