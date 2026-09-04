import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.models.file_item import FileItem
from app.services.classifier_service import ClassifierService
from app.services.desktop_service import DesktopLocation, get_desktop_locations
from app.services.scanner_service import scan_visible_desktop


class DesktopScannerTests(unittest.TestCase):
    def test_combines_user_public_hidden_shortcut_and_shell_items(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            user = root / "OneDrive" / "Desktop"
            public = root / "Public" / "Desktop"
            user.mkdir(parents=True)
            public.mkdir(parents=True)
            (user / "报告.docx").touch()
            (user / ".hidden-note.txt").touch()
            (user / "desktop.ini").touch()
            (public / "微信.lnk").touch()
            shell_item = FileItem.from_shell_item(
                "回收站", "shell:::{645FF040-5081-101B-9F08-00AA002F954E}"
            )

            items = scan_visible_desktop(
                [
                    DesktopLocation(user, "user", "用户桌面"),
                    DesktopLocation(public, "public", "公共桌面"),
                ],
                [shell_item],
            )

            by_name = {item.name: item for item in items}
            self.assertEqual(
                set(by_name), {"报告.docx", ".hidden-note.txt", "微信.lnk", "回收站"}
            )
            self.assertEqual(by_name["微信.lnk"].source, "public")
            self.assertFalse(by_name["微信.lnk"].can_organize)
            self.assertTrue(by_name["回收站"].is_virtual)
            self.assertFalse(by_name["回收站"].can_organize)
            self.assertEqual(
                ClassifierService().classify_file(by_name["回收站"]), "系统桌面项目"
            )

    def test_environment_overrides_model_onedrive_and_public_redirects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            redirected_user = root / "OneDrive" / "Desktop"
            redirected_public = root / "Shared" / "Desktop"
            redirected_user.mkdir(parents=True)
            redirected_public.mkdir(parents=True)
            with patch.dict(
                os.environ,
                {
                    "CLEANDESK_DESKTOP_DIR": str(redirected_user),
                    "CLEANDESK_PUBLIC_DESKTOP_DIR": str(redirected_public),
                },
            ):
                locations = get_desktop_locations()
            self.assertEqual([location.path for location in locations], [redirected_user, redirected_public])
            self.assertEqual([location.source for location in locations], ["user", "public"])

    @unittest.skipUnless(sys.platform == "win32", "Windows hidden attribute test")
    def test_windows_hidden_attribute_is_recorded_without_omitting_item(self):
        import ctypes

        with tempfile.TemporaryDirectory() as directory:
            hidden = Path(directory) / "hidden.txt"
            hidden.touch()
            self.assertTrue(ctypes.windll.kernel32.SetFileAttributesW(str(hidden), 0x2))
            item = FileItem.from_path(hidden)
            self.assertTrue(item.is_hidden)


if __name__ == "__main__":
    unittest.main()
