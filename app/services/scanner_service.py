"""Scan the real and virtual sources that make up the visible Windows desktop."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable

from app.models.file_item import FileItem
from app.services.desktop_service import DesktopLocation, get_desktop_locations


_IGNORED_METADATA = {"desktop.ini", "thumbs.db"}

# Windows exposes these as Shell namespace objects, not files.  The visibility
# CLSID can differ from the Explorer launch target (notably Control Panel).
_SYSTEM_SHELL_ITEMS = (
    ("此电脑", "{20D04FE0-3AEA-1069-A2D8-08002B30309D}", None, False),
    ("回收站", "{645FF040-5081-101B-9F08-00AA002F954E}", None, True),
    ("网络", "{F02C1A0D-BE21-4350-88B0-7367FC96EF3C}", None, False),
    (
        "控制面板",
        "{5399E694-6CE5-4D6C-8FCE-1D8870FDCBA0}",
        "{26EE0668-A00A-44D7-9371-BEB064C98683}",
        False,
    ),
    ("用户文件", "{59031A47-3F72-44A7-89C5-5595FE6B30EE}", None, False),
)


def scan_directory(directory: Path, source: str = "user") -> list[FileItem]:
    """Scan one directory level without following folders or changing items."""
    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"目录不存在: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"不是目录: {directory}")

    items: list[FileItem] = []
    try:
        paths = sorted(directory.iterdir(), key=lambda value: value.name.casefold())
    except PermissionError:
        return items

    for item in paths:
        if item.name.casefold() in _IGNORED_METADATA:
            continue
        try:
            items.append(FileItem.from_path(item, source=source))
        except (FileNotFoundError, PermissionError, OSError):
            # Broken shortcuts, transient cloud placeholders and protected files
            # must not prevent the rest of the desktop from appearing.
            continue
    return items


def _read_registry_dword(root, key_path: str, value_name: str) -> int | None:
    try:
        import winreg

        with winreg.OpenKey(root, key_path) as key:
            value, _value_type = winreg.QueryValueEx(key, value_name)
        return int(value)
    except (FileNotFoundError, OSError, TypeError, ValueError):
        return None


def _shell_icon_visible(clsid: str, default_visible: bool) -> bool:
    """Match Explorer's Desktop Icon Settings (0 is visible, 1 is hidden)."""
    if sys.platform != "win32":
        return False

    import winreg

    policy_key = r"Software\Microsoft\Windows\CurrentVersion\Policies\NonEnum"
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        if _read_registry_dword(root, policy_key, clsid) == 1:
            return False

    base = r"Software\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons"
    for menu in ("NewStartPanel", "ClassicStartMenu"):
        hidden = _read_registry_dword(
            winreg.HKEY_CURRENT_USER, f"{base}\\{menu}", clsid
        )
        if hidden is not None:
            return hidden == 0
    return default_visible


def get_shell_desktop_items() -> list[FileItem]:
    """Return enabled system desktop icons as protected virtual items."""
    setting = os.getenv("CLEANDESK_INCLUDE_SHELL_ITEMS", "1").strip().casefold()
    if sys.platform != "win32" or setting in {"0", "false", "no", "off"}:
        return []

    items: list[FileItem] = []
    for name, visibility_clsid, launch_clsid, default_visible in _SYSTEM_SHELL_ITEMS:
        if _shell_icon_visible(visibility_clsid, default_visible):
            target = launch_clsid or visibility_clsid
            items.append(FileItem.from_shell_item(name, f"shell:::{target}"))
    return items


def scan_visible_desktop(
    locations: Iterable[DesktopLocation] | None = None,
    shell_items: Iterable[FileItem] | None = None,
) -> list[FileItem]:
    """Scan user Desktop, Public Desktop and safe Shell namespace entries."""
    resolved_locations = list(locations) if locations is not None else get_desktop_locations()
    resolved_shell_items = (
        list(shell_items) if shell_items is not None else get_shell_desktop_items()
    )

    items: list[FileItem] = []
    seen: set[str] = set()
    for location in resolved_locations:
        for item in scan_directory(location.path, source=location.source):
            key = os.path.normcase(os.path.abspath(item.path))
            if key not in seen:
                seen.add(key)
                items.append(item)

    for item in resolved_shell_items:
        key = item.path.casefold()
        if key not in seen:
            seen.add(key)
            items.append(item)
    return items


def scan_files_only(directory: Path) -> list[FileItem]:
    return [item for item in scan_directory(directory) if item.is_file]


def scan_folders_only(directory: Path) -> list[FileItem]:
    return [item for item in scan_directory(directory) if item.is_folder]


if __name__ == "__main__":
    result = scan_visible_desktop()
    print(f"发现项目数量: {len(result)}")
    for item in result:
        print(f"[{item.source}] {item}")
