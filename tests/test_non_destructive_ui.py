import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.workspace_page import CategoryCard, DesktopItemButton, WorkspacePage
from app.ui.music_visualizer import MusicVisualizer


class NonDestructiveUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_refresh_does_not_change_desktop_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            desktop = root / "Desktop"
            public_desktop = root / "PublicDesktop"
            desktop.mkdir()
            public_desktop.mkdir()
            for name in ("Codex.lnk", "PyCharm.lnk", "报告.docx", "Firefox.exe"):
                (desktop / name).touch()
            (desktop / "资料文件夹").mkdir()
            (public_desktop / "微信.lnk").touch()
            before_user = sorted(path.name for path in desktop.iterdir())
            before_public = sorted(path.name for path in public_desktop.iterdir())
            with patch.dict(
                os.environ,
                {
                    "CLEANDESK_DESKTOP_DIR": str(desktop),
                    "CLEANDESK_PUBLIC_DESKTOP_DIR": str(public_desktop),
                    "CLEANDESK_INCLUDE_SHELL_ITEMS": "0",
                },
            ):
                page = WorkspacePage()
                page.refresh()
                self.app.processEvents()
                after_user = sorted(path.name for path in desktop.iterdir())
                after_public = sorted(path.name for path in public_desktop.iterdir())
                self.assertEqual(before_user, after_user)
                self.assertEqual(before_public, after_public)
                self.assertGreaterEqual(len(page.findChildren(CategoryCard)), 5)
                visualizer = page.findChild(MusicVisualizer)
                self.assertIsNotNone(visualizer)
                self.assertTrue(visualizer.animation_timer.isActive())
                self.assertEqual(
                    len(page.findChildren(DesktopItemButton)),
                    len(before_user) + len(before_public),
                )


if __name__ == "__main__":
    unittest.main()
