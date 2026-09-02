# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path
import sys

base_path = Path.cwd()
# The project can also be built from a virtual environment whose Tcl/Tk
# runtime belongs to its base interpreter. Tell PyInstaller the resolved
# locations explicitly so the packaged GUI is not silently built without Tk.
tcl_library = Path(sys.base_prefix) / 'tcl' / 'tcl8.6'
tk_library = Path(sys.base_prefix) / 'tcl' / 'tk8.6'
os.environ['TCL_LIBRARY'] = str(tcl_library)
os.environ['TK_LIBRARY'] = str(tk_library)

a = Analysis(
    ['src\\gui\\app.py'],
    pathex=[str(base_path)],
    binaries=[
        (str(Path(sys.base_prefix) / 'DLLs' / '_tkinter.pyd'), '.'),
        (str(Path(sys.base_prefix) / 'DLLs' / 'tcl86t.dll'), '.'),
        (str(Path(sys.base_prefix) / 'DLLs' / 'tk86t.dll'), '.'),
    ],
    datas=[
        (str(Path(sys.base_prefix) / 'Lib' / 'tkinter'), 'tkinter'),
        (str(tcl_library), '_tcl_data'),
        (str(tk_library), '_tk_data'),
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
        'pillow_heif',
        'olefile',
        'pystray',
        'pystray._win32',
        'customtkinter',
        'tkinter',
        'tkinter.constants',
        'tkinter.filedialog',
        'tkinter.font',
        'tkinter.messagebox',
        'tkinter.ttk',
        'keyring.backends.Windows',
        'msal',
        'email',
        'imaplib',
    ],
    runtime_hooks=[str(base_path / 'tools' / 'pyi_rth_sorterino_tk.py')],
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
