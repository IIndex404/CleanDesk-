from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.windows_desktop import WindowsDesktopController, _guard_command


class PackagingTests(unittest.TestCase):
    def test_guard_start_failure_restores_icons(self):
        controller = WindowsDesktopController()
        controller.attached = True
        with (
            patch("app.services.windows_desktop.set_native_desktop_icons_visible", return_value=True) as visibility,
            patch.object(controller, "_start_guard", side_effect=OSError("cannot launch")),
        ):
            self.assertFalse(controller.take_over_icons())
        self.assertEqual([call.args[0] for call in visibility.call_args_list], [False, True])
        self.assertFalse(controller.native_icons_hidden)

    def test_guard_gets_independent_onefile_environment(self):
        with patch("app.services.windows_desktop.subprocess.Popen") as popen:
            controller = WindowsDesktopController()
            controller._start_guard()
            self.assertEqual(
                popen.call_args.kwargs["env"]["PYINSTALLER_RESET_ENVIRONMENT"], "1"
            )
            controller._start_guard()
            popen.assert_called_once()

    def test_source_guard_uses_python_script(self):
        with patch.object(sys, "frozen", False, create=True):
            command, working_directory = _guard_command(1234)

        self.assertEqual(command[0], sys.executable)
        self.assertTrue(command[1].endswith("desktop_guard.py"))
        self.assertEqual(command[2], "1234")
        self.assertEqual(Path(working_directory), Path(command[1]).parents[2])

    def test_frozen_guard_relaunches_packaged_executable(self):
        packaged_executable = r"C:\Apps\CleanDesk\CleanDesk.exe"
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "executable", packaged_executable),
        ):
            command, working_directory = _guard_command(4321)

        self.assertEqual(
            command,
            [packaged_executable, "--desktop-guard", "4321"],
        )
        self.assertEqual(working_directory, r"C:\Apps\CleanDesk")


if __name__ == "__main__":
    unittest.main()
