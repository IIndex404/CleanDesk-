from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from app.services.windows_desktop import set_native_desktop_icons_visible
from app.ui.main_window import MainWindow


def main() -> int:
    if "--restore-icons" in sys.argv:
        return 0 if set_native_desktop_icons_visible(True) else 1

    window_mode = "--window" in sys.argv
    desktop_test = "--desktop-test" in sys.argv
    app = QApplication([sys.argv[0]])
    app.setStyle("Fusion")
    app.setApplicationName("CleanDesk")
    app.setQuitOnLastWindowClosed(True)

    window = MainWindow()
    app.aboutToQuit.connect(window.restore_desktop)

    tray = QSystemTrayIcon(app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon), app)
    tray.setToolTip("CleanDesk 桌面分组")
    tray_menu = QMenu()
    refresh_action = QAction("刷新桌面分组", tray_menu)
    refresh_action.triggered.connect(window.workspace_page.refresh)
    exit_action = QAction("退出并恢复原桌面", tray_menu)
    exit_action.triggered.connect(app.quit)
    tray_menu.addAction(refresh_action)
    tray_menu.addSeparator()
    tray_menu.addAction(exit_action)
    tray.setContextMenu(tray_menu)
    tray.show()

    if window_mode:
        window.show()
        QTimer.singleShot(0, lambda: window._restore_normal_window())
    else:
        def activate_desktop() -> None:
            attached = window.activate_desktop_mode()
            if desktop_test:
                print(f"DESKTOP_ATTACH={attached}", flush=True)
                QTimer.singleShot(6000, app.quit)

        QTimer.singleShot(0, activate_desktop)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
