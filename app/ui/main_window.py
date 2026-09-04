from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMainWindow

from app.services.windows_desktop import WindowsDesktopController
from app.services.windows_glass import enable_windows_glass
from app.ui.workspace_page import WorkspacePage


class MainWindow(QMainWindow):
    """CleanDesk 主界面；默认可切换为真正的 Windows 桌面层。"""

    def __init__(self):
        super().__init__()
        self.desktop_controller = WindowsDesktopController()
        self.is_desktop_mode = False
        self.setWindowTitle("CleanDesk · 桌面分组")
        self.setMinimumSize(940, 620)
        self.resize(1220, 780)
        self.setStyleSheet("QMainWindow { background: #101321; }")
        self.workspace_page = WorkspacePage()
        self.setCentralWidget(self.workspace_page)

    def activate_desktop_mode(self) -> bool:
        """去掉窗口边框、嵌入壁纸层并安全接管桌面图标。"""
        if os.getenv("QT_QPA_PLATFORM") == "offscreen":
            return False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())
        self.show()
        QApplication.processEvents()
        # 先让整屏尺寸和两侧视口稳定，再按真实桌面宽度重新分配卡片。
        self.workspace_page.refresh()
        QApplication.processEvents()

        if not self.desktop_controller.attach(int(self.winId())):
            self._restore_normal_window()
            return False

        self.is_desktop_mode = True
        if not self.desktop_controller.take_over_icons():
            self.desktop_controller.restore()
            self._restore_normal_window()
            return False
        self.workspace_page.set_desktop_mode_status(True)
        return True

    def _restore_normal_window(self) -> None:
        self.is_desktop_mode = False
        self.setWindowFlags(Qt.WindowType.Window)
        self.resize(1220, 780)
        self.show()
        enable_windows_glass(int(self.winId()))
        self.workspace_page.set_desktop_mode_status(False)

    def restore_desktop(self) -> None:
        self.desktop_controller.restore()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.restore_desktop()
        super().closeEvent(event)
