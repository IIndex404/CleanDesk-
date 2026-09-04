from datetime import datetime
from dataclasses import dataclass
from pathlib import Path


def _is_hidden(path: Path) -> bool:
    """Return whether a real filesystem item has the Windows hidden attribute."""
    try:
        import ctypes

        attributes = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        return attributes != 0xFFFFFFFF and bool(attributes & 0x2)
    except (AttributeError, OSError):
        return path.name.startswith(".")


@dataclass
class FileItem:
    """
    CleanDesk 文件对象模型

    用于保存扫描后的文件基础信息
    """

    name: str
    path: str
    extension: str
    is_file: bool
    is_folder: bool
    size: int
    modified_time: str
    source: str = "user"
    is_hidden: bool = False
    is_virtual: bool = False
    can_organize: bool = True

    @classmethod
    def from_path(cls, path: Path, source: str = "user"):
        """
        根据真实文件路径创建 FileItem
        """

        stat = path.stat()

        return cls(
            name=path.name,
            path=str(path),
            extension=path.suffix.lower(),
            is_file=path.is_file(),
            is_folder=path.is_dir(),
            size=stat.st_size,
            modified_time=datetime.fromtimestamp(
                stat.st_mtime
            ).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            source=source,
            is_hidden=_is_hidden(path),
            # Public Desktop is shared by all users and can require elevation.
            # CleanDesk is a launcher today, but this flag keeps future organizer
            # code from treating shared entries as ordinary user files.
            can_organize=source == "user",
        )

    @classmethod
    def from_shell_item(cls, name: str, shell_path: str):
        """Create a non-filesystem desktop item that must never be organized."""
        return cls(
            name=name,
            path=shell_path,
            extension="",
            is_file=False,
            is_folder=False,
            size=0,
            modified_time="",
            source="system",
            is_virtual=True,
            can_organize=False,
        )

    def get_size_mb(self):
        """
        文件大小 MB
        """

        return round(
            self.size / 1024 / 1024,
            2
        )

    def __str__(self):
        return (
            f"{self.name} | "
            f"{self.extension} | "
            f"{self.get_size_mb()}MB"
        )
