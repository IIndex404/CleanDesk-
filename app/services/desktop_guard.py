"""CleanDesk 异常退出保护进程：等待主进程结束后恢复桌面图标。"""

from __future__ import annotations

import ctypes
import sys


SYNCHRONIZE = 0x00100000
INFINITE = 0xFFFFFFFF


def run_guard(process_id: int) -> int:
    """Wait for one CleanDesk process and restore Explorer desktop icons."""
    if sys.platform != "win32":
        return 0
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [ctypes.c_uint, ctypes.c_bool, ctypes.c_uint]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        kernel32.WaitForSingleObject.restype = ctypes.c_uint
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = ctypes.c_bool
        handle = kernel32.OpenProcess(SYNCHRONIZE, False, process_id)
        if handle:
            kernel32.WaitForSingleObject(handle, INFINITE)
            kernel32.CloseHandle(handle)
        from app.services.windows_desktop import set_native_desktop_icons_visible

        set_native_desktop_icons_visible(True)
        return 0
    except Exception:
        # 守护进程不能影响主程序；Explorer 重启也会恢复桌面控件。
        return 1


def main() -> int:
    if len(sys.argv) != 2:
        return 2
    try:
        process_id = int(sys.argv[1])
    except ValueError:
        return 2
    return run_guard(process_id)


if __name__ == "__main__":
    raise SystemExit(main())
