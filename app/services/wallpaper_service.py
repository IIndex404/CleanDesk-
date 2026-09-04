"""读取 Windows 当前桌面壁纸。"""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path


SPI_GETDESKWALLPAPER = 0x0073


def get_current_wallpaper() -> Path | None:
    if sys.platform != "win32":
        return None
    buffer = ctypes.create_unicode_buffer(32768)
    try:
        success = ctypes.windll.user32.SystemParametersInfoW(
            SPI_GETDESKWALLPAPER, len(buffer), buffer, 0
        )
    except (AttributeError, OSError):
        return None
    path = Path(buffer.value) if success and buffer.value else None
    return path if path and path.is_file() else None
