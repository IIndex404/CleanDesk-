"""将 CleanDesk 安全地嵌入 Windows 桌面层。"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path

from ctypes import wintypes


WM_SPAWN_WORKER = 0x052C
SMTO_NORMAL = 0x0000
SW_HIDE = 0
SW_SHOW = 5
GWL_STYLE = -16
WS_CHILD = 0x40000000
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
HWND_TOP = 0


if sys.platform == "win32":
    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    _user32.FindWindowW.restype = wintypes.HWND
    _user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
    _user32.FindWindowExW.restype = wintypes.HWND
    _user32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
    _user32.EnumWindows.restype = wintypes.BOOL
    _user32.SendMessageTimeoutW.argtypes = [
        wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
        wintypes.UINT, wintypes.UINT, ctypes.POINTER(wintypes.DWORD),
    ]
    _user32.SendMessageTimeoutW.restype = wintypes.LPARAM
    _user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    _user32.GetWindowLongW.restype = ctypes.c_long
    _user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
    _user32.SetWindowLongW.restype = ctypes.c_long
    _user32.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
    _user32.SetParent.restype = wintypes.HWND
    _user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    _user32.GetClientRect.restype = wintypes.BOOL
    _user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    _user32.ShowWindow.restype = wintypes.BOOL
    _user32.UpdateWindow.argtypes = [wintypes.HWND]
    _user32.UpdateWindow.restype = wintypes.BOOL
    _user32.SetWindowPos.argtypes = [
        wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, wintypes.UINT,
    ]
    _user32.SetWindowPos.restype = wintypes.BOOL
else:
    _user32 = None


def _find_shell_windows() -> tuple[int, int, int]:
    """返回 (Progman/WorkerW父窗口, SHELLDLL_DefView, SysListView32)。"""
    if _user32 is None:
        return 0, 0, 0

    progman = _user32.FindWindowW("Progman", None)
    if progman:
        result = wintypes.DWORD()
        _user32.SendMessageTimeoutW(
            progman, WM_SPAWN_WORKER, 0, 0, SMTO_NORMAL, 1000, ctypes.byref(result)
        )

    defview = 0
    icon_host = 0

    enum_proc_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @enum_proc_type
    def enum_windows(hwnd, _lparam):
        nonlocal defview, icon_host
        shell_view = _user32.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
        if shell_view:
            defview = shell_view
            # 该窗口承载桌面图标层。CleanDesk 作为它的子窗口，
            # 位于壁纸之上、普通应用窗口之下。
            icon_host = int(hwnd)
            return False
        return True

    _user32.EnumWindows(enum_windows, 0)
    # 直接挂到 SHELLDLL_DefView：CleanDesk 与原生 FolderView 位于同一层。
    # 隐藏 FolderView 后，CleanDesk 成为该桌面层唯一可见的交互内容。
    parent = defview or icon_host or progman
    list_view = _user32.FindWindowExW(defview, 0, "SysListView32", "FolderView") if defview else 0
    return int(parent or 0), int(defview or 0), int(list_view or 0)


def set_native_desktop_icons_visible(visible: bool) -> bool:
    """显示或隐藏 Explorer 的桌面图标控件。操作可逆。"""
    if _user32 is None:
        return False
    _parent, defview, list_view = _find_shell_windows()
    target = list_view or defview
    if not target:
        return False
    _user32.ShowWindow(target, SW_SHOW if visible else SW_HIDE)
    _user32.UpdateWindow(target)
    return True


class WindowsDesktopController:
    def __init__(self):
        self.window_id = 0
        self.parent_window = 0
        self.attached = False
        self.native_icons_hidden = False
        self._original_style = 0
        self._guard_process: subprocess.Popen | None = None

    def attach(self, window_id: int) -> bool:
        """把 Qt 窗口变成壁纸层的子窗口。"""
        if _user32 is None or not window_id:
            return False
        parent, _defview, _list_view = _find_shell_windows()
        if not parent:
            return False

        hwnd = wintypes.HWND(window_id)
        self.window_id = window_id
        self.parent_window = parent
        self._original_style = ctypes.c_ulong(_user32.GetWindowLongW(hwnd, GWL_STYLE)).value
        child_style = (self._original_style & ~WS_POPUP) | WS_CHILD | WS_VISIBLE
        _user32.SetWindowLongW(hwnd, GWL_STYLE, ctypes.c_long(child_style).value)
        ctypes.set_last_error(0)
        previous_parent = _user32.SetParent(hwnd, wintypes.HWND(parent))
        if not previous_parent and ctypes.get_last_error():
            return False

        rect = wintypes.RECT()
        if not _user32.GetClientRect(wintypes.HWND(parent), ctypes.byref(rect)):
            return False
        width = max(1, rect.right - rect.left)
        height = max(1, rect.bottom - rect.top)
        _user32.SetWindowPos(
            hwnd, wintypes.HWND(HWND_TOP), 0, 0, width, height,
            SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )
        self.attached = True
        return True

    def take_over_icons(self) -> bool:
        if not self.attached:
            return False
        hidden = set_native_desktop_icons_visible(False)
        self.native_icons_hidden = hidden
        if hidden:
            self._start_guard()
        return hidden

    def restore(self) -> None:
        if self.native_icons_hidden:
            set_native_desktop_icons_visible(True)
            self.native_icons_hidden = False

    def _start_guard(self) -> None:
        """独立守护：主程序异常退出时也恢复 Explorer 桌面图标。"""
        if sys.platform != "win32" or self._guard_process is not None:
            return
        guard_script = Path(__file__).with_name("desktop_guard.py")
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self._guard_process = subprocess.Popen(
            [sys.executable, str(guard_script), str(os.getpid())],
            cwd=str(guard_script.parents[2]),
            creationflags=creation_flags,
        )
