"""Resolve every real filesystem location merged into the Windows desktop."""

from __future__ import annotations

import ctypes
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from ctypes import wintypes


FOLDERID_DESKTOP = "B4BFCC3A-DB2C-424C-B029-7FE99A87C641"
FOLDERID_PUBLIC_DESKTOP = "C4AA340D-F20F-4863-AFEF-F87EF2E6BA25"


@dataclass(frozen=True)
class DesktopLocation:
    path: Path
    source: str
    label: str


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    @classmethod
    def from_string(cls, value: str) -> "_GUID":
        return cls.from_buffer_copy(uuid.UUID(value).bytes_le)


def _known_folder_path(folder_id: str) -> Path | None:
    """Read a Known Folder path, including OneDrive/group-policy redirects."""
    if sys.platform != "win32":
        return None

    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    ole32 = ctypes.WinDLL("ole32", use_last_error=True)
    shell32.SHGetKnownFolderPath.argtypes = [
        ctypes.POINTER(_GUID), wintypes.DWORD, wintypes.HANDLE,
        ctypes.POINTER(ctypes.c_wchar_p),
    ]
    shell32.SHGetKnownFolderPath.restype = ctypes.c_long
    ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]

    guid = _GUID.from_string(folder_id)
    result_path = ctypes.c_wchar_p()
    result = shell32.SHGetKnownFolderPath(
        ctypes.byref(guid), 0, None, ctypes.byref(result_path)
    )
    if result != 0 or not result_path.value:
        return None
    try:
        return Path(result_path.value)
    finally:
        ole32.CoTaskMemFree(result_path)


def _expanded_override(variable: str) -> Path | None:
    value = os.getenv(variable)
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return Path(os.path.expandvars(value)).expanduser().resolve()


def _first_existing(candidates: list[Path | None]) -> Path | None:
    seen: set[str] = set()
    for candidate in candidates:
        if candidate is None:
            continue
        key = os.path.normcase(os.path.abspath(str(candidate)))
        if key in seen:
            continue
        seen.add(key)
        if candidate.is_dir():
            return candidate
    return None


def get_windows_desktop_path() -> Path:
    """Return the current user's real Desktop, respecting OneDrive redirect."""
    override = _expanded_override("CLEANDESK_DESKTOP_DIR")
    if override is not None:
        if not override.is_dir():
            raise FileNotFoundError(f"桌面路径不存在: {override}")
        return override

    one_drive = os.getenv("OneDrive") or os.getenv("OneDriveConsumer")
    desktop_path = _first_existing(
        [
            _known_folder_path(FOLDERID_DESKTOP),
            Path(one_drive) / "Desktop" if one_drive else None,
            Path.home() / "Desktop",
        ]
    )
    if desktop_path is None:
        raise FileNotFoundError("无法找到 Windows 当前用户桌面路径")
    return desktop_path


def get_public_desktop_path() -> Path | None:
    """Return the shared Public Desktop, or None if unavailable."""
    override_value = os.getenv("CLEANDESK_PUBLIC_DESKTOP_DIR")
    if override_value is not None:
        if not override_value.strip():
            return None
        override = _expanded_override("CLEANDESK_PUBLIC_DESKTOP_DIR")
        if override is None or not override.is_dir():
            raise FileNotFoundError(f"公共桌面路径不存在: {override}")
        return override

    public_root = os.getenv("PUBLIC")
    return _first_existing(
        [
            _known_folder_path(FOLDERID_PUBLIC_DESKTOP),
            Path(public_root) / "Desktop" if public_root else None,
        ]
    )


def get_desktop_locations() -> list[DesktopLocation]:
    """Return distinct real folders whose contents Explorer merges on Desktop."""
    locations = [DesktopLocation(get_windows_desktop_path(), "user", "用户桌面")]
    public_path = get_public_desktop_path()
    if public_path is not None:
        locations.append(DesktopLocation(public_path, "public", "公共桌面"))

    unique: list[DesktopLocation] = []
    seen: set[str] = set()
    for location in locations:
        key = os.path.normcase(os.path.abspath(str(location.path)))
        if key not in seen:
            seen.add(key)
            unique.append(location)
    return unique


if __name__ == "__main__":
    for desktop in get_desktop_locations():
        print(f"{desktop.label}: {desktop.path}")
