"""Point frozen Tkinter at the Tcl/Tk runtime bundled by Sorterino."""

import os
import sys
from pathlib import Path


bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
os.environ["TCL_LIBRARY"] = str(bundle_root / "_tcl_data")
os.environ["TK_LIBRARY"] = str(bundle_root / "_tk_data")
