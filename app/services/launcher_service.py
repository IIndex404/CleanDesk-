"""用系统默认程序打开项目；本模块不修改文件系统。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def open_item(path: str | Path) -> None:
    target = str(path)
    if sys.platform == "win32":
        if target.casefold().startswith(("shell:::", "::{")):
            # Shell namespace objects (Recycle Bin, This PC, etc.) are not
            # filesystem paths. Explorer can open them without modifying them.
            subprocess.Popen(["explorer.exe", target])
            return
        os.startfile(target)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target])
