"""CleanDesk 异常退出保护进程：等待主进程结束后恢复桌面图标。"""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path


SYNCHRONIZE = 0x00100000
INFINITE = 0xFFFFFFFF


def main() -> int:
    if sys.platform != "win32" or len(sys.argv) != 2:
        return 0
    try:
        process_id = int(sys.argv[1])
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
        project_root = Path(__file__).resolve().parents[2]
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        from app.services.windows_desktop import set_native_desktop_icons_visible

        set_native_desktop_icons_visible(True)
        return 0
    except Exception:
        # 守护进程不能影响主程序；Explorer 重启也会恢复桌面控件。
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
