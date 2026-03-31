# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

BASE_DIR = Path(os.getcwd()).resolve()

# -----------------------------
# DATA FILES (SAUBER STRUKTURIERT)
# -----------------------------
datas = [
    (str(BASE_DIR / "assets"), "assets"),
    (str(BASE_DIR / "third_party"), "third_party"),
    (str(BASE_DIR / "rules.json"), "."),
    (str(BASE_DIR / "structure.json"), "."),
    (str(BASE_DIR / "supported_formats.json"), "."),
]

binaries = []

hiddenimports = [
    "infrastructure",
    "infrastructure.config",
    "infrastructure.config.config_loader",
    "infrastructure.config.rules_loader",
    "infrastructure.config.structure_loader",
    "infrastructure.config.formats_loader",
    "infrastructure.config.initialize_workspace",

    "infrastructure.io.folder_document_source",
    "infrastructure.ocr.tesseract_ocr",
    "infrastructure.logging.file_logger",
    "infrastructure.storage.filesystem_storage",

    "usecases.document_pipeline",

    "src.utils.path_helper",
]

# -----------------------------
# CUSTOMTKINTER EINBINDEN
# -----------------------------
ctk_datas, ctk_bins, ctk_hidden = collect_all("customtkinter")

datas += ctk_datas
binaries += ctk_bins
hiddenimports += ctk_hidden

# -----------------------------
# ANALYSIS
# -----------------------------
a = Analysis(
    [str(BASE_DIR / "src" / "gui" / "app.py")],
    pathex=[str(BASE_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

# -----------------------------
# PYZ
# -----------------------------
pyz = PYZ(a.pure)

# -----------------------------
# EXE
# -----------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Sorterino',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(BASE_DIR / "assets" / "icons" / "default_icon_128.ico"),
)

# -----------------------------
# COLLECT (ONEDIR BUILD)
# -----------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Sorterino'
)