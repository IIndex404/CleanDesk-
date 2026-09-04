"""桌面项目分类服务，不移动或重命名真实文件。"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from app.models.file_item import FileItem


CATEGORY_ORDER = (
    "AI 工具", "编程开发", "办公软件", "浏览器", "沟通社交",
    "专业软件", "文件工具", "娱乐游戏", "文件夹", "系统桌面项目", "其他",
)

CATEGORY_ICONS = {
    "AI 工具": "AI", "编程开发": "</>", "办公软件": "OFFICE",
    "浏览器": "WEB", "沟通社交": "CHAT", "专业软件": "PRO",
    "文件工具": "TOOL", "娱乐游戏": "PLAY", "文件夹": "DIR",
    "系统桌面项目": "SYSTEM", "其他": "MORE",
}

FORMAT_LABELS = OrderedDict(
    {
        ".docx": "DOCX 文档", ".doc": "DOC 文档",
        ".xlsx": "XLSX 表格", ".xls": "XLS 表格", ".csv": "CSV 表格",
        ".pptx": "PPTX 演示", ".ppt": "PPT 演示",
        ".pdf": "PDF 文档", ".txt": "TXT 文本", ".rtf": "RTF 文档",
        ".md": "MD 文本", ".odt": "ODT 文档", ".ods": "ODS 表格",
        ".epub": "EPUB 电子书",
        ".png": "PNG 图片", ".jpg": "JPG 图片", ".jpeg": "JPEG 图片",
        ".gif": "GIF 图片", ".bmp": "BMP 图片", ".webp": "WEBP 图片",
        ".svg": "SVG 图片", ".tif": "TIF 图片", ".tiff": "TIFF 图片",
        ".mp3": "MP3 音频", ".wav": "WAV 音频", ".flac": "FLAC 音频",
        ".aac": "AAC 音频", ".mp4": "MP4 视频", ".mkv": "MKV 视频",
        ".avi": "AVI 视频", ".mov": "MOV 视频", ".wmv": "WMV 视频",
        ".zip": "ZIP 压缩包", ".rar": "RAR 压缩包", ".7z": "7Z 压缩包",
        ".tar": "TAR 压缩包", ".gz": "GZ 压缩包", ".bz2": "BZ2 压缩包",
        ".xz": "XZ 压缩包", ".iso": "ISO 镜像",
        ".py": "PY 代码", ".pyw": "PYW 代码", ".ipynb": "IPYNB 笔记本",
        ".js": "JS 代码", ".ts": "TS 代码", ".tsx": "TSX 代码",
        ".jsx": "JSX 代码", ".java": "JAVA 代码", ".c": "C 代码",
        ".cpp": "CPP 代码", ".cs": "CS 代码", ".go": "GO 代码",
        ".rs": "RS 代码", ".php": "PHP 代码", ".rb": "RB 代码",
        ".sql": "SQL 文件", ".html": "HTML 文件", ".css": "CSS 文件",
        ".json": "JSON 文件", ".yaml": "YAML 文件", ".yml": "YML 文件",
        ".toml": "TOML 文件", ".xml": "XML 文件", ".ps1": "PS1 脚本",
        ".bat": "BAT 脚本",
    }
)


def get_category_badge(category: str) -> str:
    """固定用途类别使用缩写，格式类别直接显示扩展名。"""
    if category in CATEGORY_ICONS:
        return CATEGORY_ICONS[category]
    return category.split(maxsplit=1)[0][:6].upper()


class ClassifierService:
    """应用按用途分组，普通文件严格按扩展名分组。"""

    _application_extensions = {".lnk", ".exe", ".url", ".appref-ms"}
    _keyword_rules = OrderedDict(
        {
            "AI 工具": (
                "chatgpt", "codex", "claude", "deepseek", "gemini", "copilot",
                "kimi", "豆包", "通义", "文心", "智谱", "秘塔", "讯飞星火", "workbuddy",
            ),
            "编程开发": (
                "pycharm", "visual studio code", "vscode", "visual studio", "intellij",
                "idea", "jupyter", "anaconda", "docker", "dbeaver", "postman", "git",
                "github", "powershell", "terminal", "终端",
            ),
            "浏览器": (
                "chrome", "edge", "firefox", "brave", "opera", "vivaldi", "浏览器",
                "internet explorer",
            ),
            "沟通社交": (
                "微信", "wechat", "qq", "腾讯会议", "teams", "zoom", "钉钉", "飞书",
                "telegram", "discord", "skype",
            ),
            "办公软件": (
                "word", "excel", "powerpoint", "ppt", "wps", "office", "onenote",
                "outlook", "visio", "access", "endnote", "福昕", "acrobat",
            ),
            "专业软件": (
                "arcgis", "qgis", "photoshop", "illustrator", "premiere", "after effects",
                "autocad", "3ds max", "sketchup", "blender", "matlab", "spss", "stata",
            ),
            "文件工具": (
                "cleandesk", "bandizip", "7-zip", "7zip", "winrar", "迅雷", "网盘", "onedrive",
                "百度云", "夸克", "everything", "total commander", "filezilla",
                "腾讯电脑管家", "geek", "snipaste", "截图", "clash", "control center",
            ),
            "娱乐游戏": (
                "steam", "epic", "game", "游戏", "无畏契约", "燕云", "网易云音乐",
                "spotify", "music", "音乐", "哔哩哔哩", "bilibili",
            ),
        }
    )

    @staticmethod
    def _format_category(extension: str) -> str:
        if extension in FORMAT_LABELS:
            return FORMAT_LABELS[extension]
        return f"{extension.removeprefix('.').upper()} 文件"

    def classify_file(self, item: FileItem) -> str:
        if item.is_virtual:
            return "系统桌面项目"
        path = Path(item.path)
        if item.is_folder or path.is_dir():
            return "文件夹"

        extension = path.suffix.casefold()
        # 普通文件先按精确扩展名拆包，名称中即使含“Word/Excel”也不会混入软件包。
        if extension and extension not in self._application_extensions:
            return self._format_category(extension)

        normalized_name = path.stem.casefold()
        for category, keywords in self._keyword_rules.items():
            if any(keyword.casefold() in normalized_name for keyword in keywords):
                return category
        return "其他"

    def classify_files(self, items: list[FileItem]) -> OrderedDict[str, list[FileItem]]:
        raw: dict[str, list[FileItem]] = {}
        for item in items:
            raw.setdefault(self.classify_file(item), []).append(item)

        ordered: OrderedDict[str, list[FileItem]] = OrderedDict()
        preferred_order = list(CATEGORY_ORDER) + list(FORMAT_LABELS.values())
        for category in preferred_order:
            if category in raw and category not in ordered:
                ordered[category] = raw.pop(category)
        for category in sorted(raw, key=str.casefold):
            ordered[category] = raw[category]
        for entries in ordered.values():
            entries.sort(key=lambda value: value.name.casefold())
        return ordered
