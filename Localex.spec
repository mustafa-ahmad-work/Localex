# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

project_root = Path.cwd()
src_dir = project_root / "src"

added_files = [
    (str(project_root / "resources"), "resources"),
]
added_files += collect_data_files("qtawesome")

excluded_modules = [
    "torch",
    "torchvision",
    "torchaudio",
    "tensorflow",
    "tensorboard",
    "scipy",
    "pandas",
    "matplotlib",
    "IPython",
    "jupyter",
    "tkinter",
    "unittest",
    "test",
    "pytest",
    "PySide6.QtWebEngine",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtDesigner",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.Qt3D",
]

hidden_imports_list = [
    "Localex",
    "Localex.main",
    "Localex.translator",
    "Localex.model_manager",
    "Localex.download_manager",
    "Localex.database",
    "Localex.history",
    "Localex.speech",
    "Localex.shortcuts",
    "Localex.clipboard",
    "Localex.paths",
    "Localex.config",
    "Localex.utils",
    "Localex.tray",
    "Localex.workers",
    "Localex.ui.icons",
    "Localex.ui.main_window",
    "Localex.ui.floating_window",
    "Localex.ui.settings_window",
    "Localex.ui.history_window",
    "Localex.ui.model_manager_window",
    "Localex.ui.theme",
    "ctranslate2",
    "sentencepiece",
    "win32com.client",
]
hidden_imports_list += collect_submodules("qtawesome") + collect_submodules("qtpy")

a = Analysis(
    [str(src_dir / "Localex" / "__main__.py")],
    pathex=[str(src_dir)],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports_list,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Localex",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "resources" / "icons" / "app_icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Localex",
)
