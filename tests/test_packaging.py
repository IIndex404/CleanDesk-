from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.windows_desktop import _guard_command


class PackagingTests(unittest.TestCase):
    def test_source_guard_uses_python_script(self):
        with patch.object(sys, "frozen", False, create=True):
            command, working_directory = _guard_command(1234)

        self.assertEqual(command[0], sys.executable)
        self.assertTrue(command[1].endswith("desktop_guard.py"))
        self.assertEqual(command[2], "1234")
        self.assertEqual(Path(working_directory).name, "CleanDesk")

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
