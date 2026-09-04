"""Windows 玻璃背景支持。

优先使用 Windows 11 的系统 Acrylic 背景；不支持时回退到 DWM 模糊。
"""

from __future__ import annotations

import ctypes
import sys


class _Margins(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth", ctypes.c_int),
        ("cxRightWidth", ctypes.c_int),
        ("cyTopHeight", ctypes.c_int),
        ("cyBottomHeight", ctypes.c_int),
    ]


class _DwmBlurBehind(ctypes.Structure):
    _fields_ = [
        ("dwFlags", ctypes.c_uint),
        ("fEnable", ctypes.c_bool),
        ("hRgnBlur", ctypes.c_void_p),
        ("fTransitionOnMaximized", ctypes.c_bool),
    ]


def enable_windows_glass(window_id: int) -> bool:
    """为给定原生窗口开启壁纸取色/模糊背景。"""
    if sys.platform != "win32" or not window_id:
        return False

    try:
        dwmapi = ctypes.WinDLL("dwmapi")
        hwnd = ctypes.c_void_p(window_id)

        # 将 DWM 玻璃区域延伸到整个客户区。
        margins = _Margins(-1, -1, -1, -1)
        dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))

        # Windows 11: DWMWA_SYSTEMBACKDROP_TYPE = 38，3 为 Acrylic/Transient。
        backdrop_type = ctypes.c_int(3)
        result = dwmapi.DwmSetWindowAttribute(
            hwnd, 38, ctypes.byref(backdrop_type), ctypes.sizeof(backdrop_type)
        )

        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20。
        dark_mode = ctypes.c_int(1)
        dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode)
        )

        if result == 0:
            return True

        # Windows 10 等环境的回退路径。
        blur = _DwmBlurBehind(1, True, None, True)
        return dwmapi.DwmEnableBlurBehindWindow(hwnd, ctypes.byref(blur)) == 0
    except (AttributeError, OSError, ValueError):
        return False
