# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

base_path = Path.cwd()

a = Analysis(
    ['src\\gui\\app.py'],
    pathex=[str(base_path)],
    datas=[
        (str(base_path / 'assets' / 'templates'), 'assets/templates'),
        (str(base_path / 'assets' / 'icons'), 'assets/icons'),
        (str(base_path / 'third_party'), 'third_party'),
    ],
    hiddenimports=[
        'pytesseract',
        'pdf2image',
        'PIL.Image',
        'PIL.ImageFile',
        'PIL._tkinter_finder',
        'pystray',
        'pystray._win32',
        'customtkinter',
        'keyring.backends.Windows',
        'email',
        'imaplib',
    ],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='Sorterino',

    debug=False,
    console=False,

    disable_windowed_traceback=True,

    strip=False,
    upx=True,

    icon=str(base_path / 'assets' / 'icons' / 'default_icon_128.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name='Sorterino',
)
