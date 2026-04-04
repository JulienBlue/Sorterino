# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

# CONFIG / BASIS
base_path = Path(__file__).resolve().parent

# ANALYSIS / BUILD
a = Analysis(
    ['src\\gui\\app.py'],
    pathex=[],
    binaries=[],
    datas=[
        (str(base_path / 'assets' / 'templates'), 'assets/templates'),
        (str(base_path / 'assets' / 'icons'), 'assets/icons'),
    ],
    hiddenimports=[
        'pytesseract',
        'pdf2image',
        'PIL',
        'pystray',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=True,
    optimize=0,
)

# PYZ / PACKAGE
pyz = PYZ(a.pure)

# EXE / BUILD
exe = EXE(
    pyz,
    a.scripts,
    [('v', None, 'OPTION')],
    exclude_binaries=True,
    name='Sorterino',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(base_path / 'assets' / 'icons' / 'default_icon_128.ico'),
)

# COLLECT / OUTPUT
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Sorterino',
)