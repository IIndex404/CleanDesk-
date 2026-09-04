"""CleanDesk 的非破坏性桌面接管界面。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEvent, QFileInfo, QFileSystemWatcher, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPaintEvent, QPainter, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QApplication, QFileIconProvider, QFrame, QGridLayout, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QScrollArea, QSizePolicy, QStyle, QToolButton, QVBoxLayout, QWidget,
)

from app.models.file_item import FileItem
from app.services.classifier_service import ClassifierService, get_category_badge
from app.services.desktop_service import get_desktop_locations
from app.services.launcher_service import open_item
from app.services.scanner_service import scan_visible_desktop
from app.services.wallpaper_service import get_current_wallpaper
from app.ui.flow_layout import FlowLayout
from app.ui.music_visualizer import MusicVisualizer


CARD_STYLE = """
QFrame#categoryCard {
    background-color: rgba(255, 255, 255, 32);
    border: 1px solid rgba(255, 255, 255, 62);
    border-radius: 22px;
}
QLabel#categoryBadge {
    color: #ffffff; background-color: rgba(8, 12, 24, 180);
    border: 1px solid rgba(255, 255, 255, 30); border-radius: 11px;
    padding: 1px 7px; font-size: 10px; font-weight: 700;
}
QLabel#categoryName { color: #f7f8ff; font-size: 14px; font-weight: 700; }
QLabel#categoryCount { color: rgba(235, 239, 255, 150); font-size: 12px; }
QToolButton {
    color: #ffffff; background-color: rgba(12, 18, 32, 42);
    border: 1px solid transparent; border-radius: 14px;
    padding: 3px 3px; font-size: 12px; font-weight: 600;
}
QToolButton:hover {
    background-color: rgba(255, 255, 255, 38);
    border: 1px solid rgba(255, 255, 255, 60);
}
QToolButton:pressed { background-color: rgba(122, 135, 255, 80); }
"""


class DesktopItemButton(QToolButton):
    def __init__(self, item: FileItem, icon_provider: QFileIconProvider, parent=None):
        super().__init__(parent)
        self.item = item
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        if item.is_virtual:
            standard_icons = {
                "此电脑": QStyle.StandardPixmap.SP_ComputerIcon,
                "回收站": QStyle.StandardPixmap.SP_TrashIcon,
                "网络": QStyle.StandardPixmap.SP_DriveNetIcon,
                "用户文件": QStyle.StandardPixmap.SP_DirHomeIcon,
            }
            icon_kind = standard_icons.get(item.name, QStyle.StandardPixmap.SP_DirIcon)
            self.setIcon(QApplication.style().standardIcon(icon_kind))
        else:
            self.setIcon(icon_provider.icon(QFileInfo(item.path)))
        self.setIconSize(QSize(40, 40))
        self.setFixedSize(64, 72)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        source_labels = {"user": "用户桌面", "public": "公共桌面", "system": "系统项目"}
        source_label = source_labels.get(item.source, item.source)
        safety_label = "\n受保护：不参与整理" if not item.can_organize else ""
        hidden_label = "\n隐藏项目" if item.is_hidden else ""
        self.setToolTip(
            f"{item.name}\n来源：{source_label}\n{item.path}{safety_label}{hidden_label}"
        )
        font = self.font()
        font.setPixelSize(12)
        font.setWeight(QFont.Weight.DemiBold)
        self.setFont(font)
        metrics = QFontMetrics(self.font())
        self.setText(self._readable_label(Path(item.name).stem, metrics, 58))

    @staticmethod
    def _readable_label(text: str, metrics: QFontMetrics, width: int) -> str:
        """尽量用两行显示名称，第二行才做省略。"""
        clean = " ".join(text.split())
        if metrics.horizontalAdvance(clean) <= width:
            return clean

        split_at = 1
        for index in range(1, len(clean) + 1):
            if metrics.horizontalAdvance(clean[:index]) > width:
                break
            split_at = index
        prefix = clean[:split_at]
        space_at = prefix.rfind(" ")
        if space_at >= max(2, split_at // 2):
            split_at = space_at
        first = clean[:split_at].rstrip()
        remainder = clean[split_at:].lstrip()
        second = metrics.elidedText(remainder, Qt.TextElideMode.ElideRight, width)
        return f"{first}\n{second}" if second else first


class CategoryCard(QFrame):
    """一个类别对应一块磨砂矩形卡片。"""

    def __init__(self, category: str, items: list[FileItem], open_callback, parent=None):
        super().__init__(parent)
        self.setObjectName("categoryCard")
        self.setStyleSheet(CARD_STYLE)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(9, 3, 9, 4)
        root.setSpacing(1)

        header = QHBoxLayout()
        header.setSpacing(9)
        badge = QLabel(get_category_badge(category))
        badge.setObjectName("categoryBadge")
        badge.setFixedHeight(20)
        badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        name = QLabel(category)
        name.setObjectName("categoryName")
        count = QLabel(f"{len(items)} 项")
        count.setObjectName("categoryCount")
        header.addWidget(badge)
        header.addWidget(name)
        header.addStretch(1)
        header.addWidget(count)
        root.addLayout(header)

        item_grid = QGridLayout()
        item_grid.setContentsMargins(0, 0, 0, 0)
        item_grid.setHorizontalSpacing(3)
        item_grid.setVerticalSpacing(2)
        icon_provider = QFileIconProvider()
        icon_columns = min(8, max(1, len(items)))
        for index, item in enumerate(items):
            button = DesktopItemButton(item, icon_provider, self)
            button.clicked.connect(lambda checked=False, path=item.path: open_callback(path))
            item_grid.addWidget(
                button, index // icon_columns, index % icon_columns, Qt.AlignmentFlag.AlignLeft
            )
        root.addLayout(item_grid)
        content_width = icon_columns * 64 + max(0, icon_columns - 1) * 3 + 18
        self.setFixedWidth(max(176, content_width))


class WorkspacePage(QWidget):
    """只读扫描真实桌面，在桌面接管层中分组并作为启动器使用。"""

    def __init__(self):
        super().__init__()
        self.desktop_locations = get_desktop_locations()
        self.desktop_path = self.desktop_locations[0].path
        self.classifier = ClassifierService()
        self.desktop_mode_active = False
        self.wallpaper_pixmap = QPixmap()
        self._load_wallpaper()
        self._build_ui()
        self._watch_desktop()
        self.refresh()

    def _build_ui(self) -> None:
        self.setObjectName("workspace")
        self.setStyleSheet(
            """
            QWidget#workspace {
                background: transparent;
            }
            QLabel#mainTitle { color:#ffffff; font-size:24px; font-weight:800; }
            QLabel#subtitle { color:rgba(232,236,255,170); font-size:13px; }
            QLabel#status { color:rgba(232,236,255,145); font-size:12px; }
            QFrame#clockPanel {
                background-color:rgba(255,255,255,24);
                border:1px solid rgba(255,255,255,58);
                border-radius:24px;
            }
            QLabel#clockTime {
                color:#ffffff; font-size:52px; font-weight:700;
            }
            QLabel#clockDate {
                color:rgba(240,243,255,190); font-size:14px; font-weight:600;
            }
            QPushButton#refreshButton {
                color:#ffffff; background-color:rgba(255,255,255,30);
                border:1px solid rgba(255,255,255,58); border-radius:13px;
                padding:9px 16px; font-weight:700;
            }
            QPushButton#refreshButton:hover { background-color:rgba(255,255,255,50); }
            QScrollArea { border:none; background:transparent; }
            QScrollArea > QWidget > QWidget { background:transparent; }
            QScrollBar:vertical { background:transparent; width:10px; margin:2px; }
            QScrollBar::handle:vertical {
                background:rgba(255,255,255,55); border-radius:5px; min-height:32px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0px; }
            """
        )

        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(24, 18, 24, 12)
        page_layout.setSpacing(11)

        header = QHBoxLayout()
        heading = QVBoxLayout()
        title = QLabel("CleanDesk")
        title.setObjectName("mainTitle")
        subtitle = QLabel(f"桌面接管分组  ·  {self.desktop_path}")
        subtitle.setObjectName("subtitle")
        heading.addWidget(title)
        heading.addWidget(subtitle)
        header.addLayout(heading)
        header.addStretch(1)
        refresh_button = QPushButton("刷新桌面")
        refresh_button.setObjectName("refreshButton")
        refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_button.clicked.connect(self.refresh)
        header.addWidget(refresh_button)
        exit_button = QPushButton("退出")
        exit_button.setObjectName("refreshButton")
        exit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        exit_button.clicked.connect(QApplication.instance().quit)
        header.addWidget(exit_button)
        page_layout.addLayout(header)

        hero_row = QHBoxLayout()
        hero_row.setContentsMargins(0, 0, 0, 0)
        hero_row.setSpacing(12)

        self.clock_panel = QFrame()
        self.clock_panel.setObjectName("clockPanel")
        self.clock_panel.setFixedSize(310, 118)
        clock_layout = QVBoxLayout(self.clock_panel)
        clock_layout.setContentsMargins(20, 9, 20, 10)
        clock_layout.setSpacing(0)
        self.clock_time_label = QLabel()
        self.clock_time_label.setObjectName("clockTime")
        self.clock_date_label = QLabel()
        self.clock_date_label.setObjectName("clockDate")
        clock_layout.addWidget(self.clock_time_label)
        clock_layout.addWidget(self.clock_date_label)
        hero_row.addWidget(self.clock_panel, 0, Qt.AlignmentFlag.AlignLeft)
        hero_row.addStretch(1)
        self.music_visualizer = MusicVisualizer(self)
        hero_row.addWidget(self.music_visualizer, 8, Qt.AlignmentFlag.AlignVCenter)
        hero_row.addStretch(1)
        page_layout.addLayout(hero_row)

        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start()
        self._update_clock()
        page_layout.addStretch(1)

        self.lower_container = QWidget()
        self.lower_container.setStyleSheet("background: transparent;")
        lower_layout = QHBoxLayout(self.lower_container)
        lower_layout.setContentsMargins(0, 0, 0, 0)
        lower_layout.setSpacing(0)

        self.scrolls: list[QScrollArea] = []
        self.cards_hosts: list[QWidget] = []
        self.cards_layouts: list[FlowLayout] = []
        for panel_index in range(2):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            cards_host = QWidget()
            cards_host.setStyleSheet("background: transparent;")
            cards_layout = FlowLayout(cards_host, margin=0, spacing=3)
            scroll.setWidget(cards_host)
            self.scrolls.append(scroll)
            self.cards_hosts.append(cards_host)
            self.cards_layouts.append(cards_layout)
            lower_layout.addWidget(scroll, 46)
            if panel_index == 0:
                lower_layout.addStretch(8)

        page_layout.addWidget(self.lower_container, 0)

        self.status_label = QLabel()
        self.status_label.setObjectName("status")
        page_layout.addWidget(self.status_label)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.lower_container.setFixedHeight(max(466, int(self.height() * 0.692)))
        QTimer.singleShot(0, self._sync_cards_height)
        previous_width = getattr(self, "_last_layout_width", 0)
        self._last_layout_width = self.width()
        if previous_width and abs(previous_width - self.width()) > 60 and hasattr(self, "refresh_timer"):
            self.refresh_timer.start()

    def _sync_cards_height(self) -> None:
        for scroll, cards_host, cards_layout in zip(
            self.scrolls, self.cards_hosts, self.cards_layouts
        ):
            viewport_width = max(1, scroll.viewport().width() - 4)
            needed_height = cards_layout.heightForWidth(viewport_width)
            cards_host.setMinimumHeight(max(needed_height, scroll.viewport().height()))

    def _load_wallpaper(self) -> None:
        wallpaper = get_current_wallpaper()
        self.wallpaper_pixmap = QPixmap(str(wallpaper)) if wallpaper else QPixmap()

    def _update_clock(self) -> None:
        now = datetime.now()
        weekdays = "一二三四五六日"
        self.clock_time_label.setText(now.strftime("%H:%M"))
        self.clock_date_label.setText(
            f"{now:%Y年%m月%d日}  星期{weekdays[now.weekday()]}"
        )

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        if not self.wallpaper_pixmap.isNull():
            scaled = self.wallpaper_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (scaled.width() - self.width()) // 2
            y = (scaled.height() - self.height()) // 2
            painter.drawPixmap(self.rect(), scaled, scaled.rect().adjusted(x, y, -x, -y))
        else:
            painter.fillRect(self.rect(), QColor("#171b2e"))
        painter.fillRect(self.rect(), QColor(8, 12, 26, 105))

    def _watch_desktop(self) -> None:
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.setInterval(450)
        self.refresh_timer.timeout.connect(self.refresh)
        self.desktop_watcher = QFileSystemWatcher(self)
        self.desktop_watcher.directoryChanged.connect(lambda _path: self.refresh_timer.start())
        self._sync_desktop_watcher()

    def _sync_desktop_watcher(self) -> None:
        desired = {str(location.path) for location in self.desktop_locations}
        current = set(self.desktop_watcher.directories())
        if current - desired:
            self.desktop_watcher.removePaths(sorted(current - desired))
        if desired - current:
            self.desktop_watcher.addPaths(sorted(desired - current))

    def set_desktop_mode_status(self, active: bool) -> None:
        self.desktop_mode_active = active
        self._update_status()

    def _update_status(self, item_count: int | None = None, group_count: int | None = None) -> None:
        if item_count is None:
            item_count = getattr(self, "last_item_count", 0)
        if group_count is None:
            group_count = getattr(self, "last_group_count", 0)
        mode_text = (
            "桌面接管已开启 · 原生图标已安全隐藏"
            if self.desktop_mode_active
            else "窗口预览模式 · 不会移动文件"
        )
        source_text = (
            f" · 公共桌面 {getattr(self, 'last_public_count', 0)} 项"
            f" · 系统保护项 {getattr(self, 'last_system_count', 0)} 项"
        )
        self.status_label.setText(
            f"{mode_text} · {item_count} 个项目 · {group_count} 个分类{source_text} · "
            f"{datetime.now().strftime('%H:%M:%S')}"
        )

    def _clear_cards(self) -> None:
        for cards_layout in self.cards_layouts:
            while cards_layout.count():
                item = cards_layout.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    @staticmethod
    def _packed_height(card_sizes: list[tuple[int, int]], indices: list[int], width: int) -> int:
        x = 0
        total_height = 0
        row_height = 0
        spacing = 3
        for index in indices:
            card_width, card_height = card_sizes[index]
            required_width = card_width if x == 0 else spacing + card_width
            if x and x + required_width > width:
                total_height += row_height + spacing
                x = 0
                row_height = 0
                required_width = card_width
            x += required_width
            row_height = max(row_height, card_height)
        return total_height + row_height

    def _best_panel_assignment(
        self, card_sizes: list[tuple[int, int]], categories: list[str]
    ) -> list[int]:
        count = len(card_sizes)
        if count < 2:
            return [0] * count
        # 两侧视口会因滚动条和取整出现少量宽度差，按较窄侧计算可避免
        # 刚好贴边的大卡片在真实桌面中额外换行。
        panel_width = max(
            300,
            min(scroll.viewport().width() for scroll in self.scrolls) - 6,
        )
        best_assignment = [index % 2 for index in range(count)]
        best_score: tuple[int, int] | None = None
        # 当前桌面分类数量较少，完整枚举可稳定得到两侧最低、最均衡的组合。
        for mask in range(1, (1 << count) - 1):
            valid = True
            for index, category in enumerate(categories):
                if category == "办公软件" and not mask & (1 << index):
                    valid = False
                    break
                if category == "文件夹" and mask & (1 << index):
                    valid = False
                    break
            if not valid:
                continue
            left = [index for index in range(count) if mask & (1 << index)]
            right = [index for index in range(count) if not mask & (1 << index)]
            left_height = self._packed_height(card_sizes, left, panel_width)
            right_height = self._packed_height(card_sizes, right, panel_width)
            score = (max(left_height, right_height), abs(left_height - right_height))
            if best_score is None or score < best_score:
                best_score = score
                best_assignment = [0 if mask & (1 << index) else 1 for index in range(count)]
        return best_assignment

    def refresh(self) -> None:
        try:
            self._load_wallpaper()
            self.update()
            # Refresh the resolved locations in case OneDrive or policy changed
            # while the app was running. Shell items are protected model entries.
            self.desktop_locations = get_desktop_locations()
            self._sync_desktop_watcher()
            items = scan_visible_desktop(self.desktop_locations)
            groups = self.classifier.classify_files(items)
            self._clear_cards()
            visible_groups = [(name, entries) for name, entries in groups.items() if entries]
            cards: list[CategoryCard] = []
            for category, entries in visible_groups:
                card = CategoryCard(category, entries, self._open_item)
                card.ensurePolished()
                cards.append(card)
            card_sizes = [(card.sizeHint().width(), card.sizeHint().height()) for card in cards]
            assignments = self._best_panel_assignment(
                card_sizes, [category for category, _entries in visible_groups]
            )
            panel_cards: list[list[tuple[str, CategoryCard]]] = [[], []]
            for (category, _entries), card, panel_index in zip(
                visible_groups, cards, assignments
            ):
                panel_cards[panel_index].append((category, card))
            for panel_index, entries in enumerate(panel_cards):
                # 文件夹保持为右侧最后一行；“娱乐游戏”和“其他”可在它上方共用一行。
                entries.sort(key=lambda value: value[0] == "文件夹")
                for _category, card in entries:
                    card.setParent(self.cards_hosts[panel_index])
                    self.cards_layouts[panel_index].addWidget(card)
            QTimer.singleShot(0, self._sync_cards_height)
            self.last_item_count = len(items)
            self.last_group_count = len(visible_groups)
            self.last_system_count = sum(item.is_virtual for item in items)
            self.last_public_count = sum(item.source == "public" for item in items)
            self._update_status(self.last_item_count, self.last_group_count)
        except Exception as exc:
            QMessageBox.warning(self, "读取桌面失败", str(exc))

    def _open_item(self, path: str) -> None:
        try:
            open_item(path)
        except Exception as exc:
            QMessageBox.warning(self, "无法打开", f"{path}\n\n{exc}")
