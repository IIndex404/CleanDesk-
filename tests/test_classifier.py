import tempfile
import unittest
from pathlib import Path

from app.models.file_item import FileItem
from app.services.classifier_service import ClassifierService


class ClassifierServiceTests(unittest.TestCase):
    def test_name_and_extension_categories(self):
        cases = {
            "ChatGPT.lnk": "AI 工具",
            "PyCharm.lnk": "编程开发",
            "Firefox.exe": "浏览器",
            "微信.lnk": "沟通社交",
            "论文.docx": "DOCX 文档",
            "数据.xlsx": "XLSX 表格",
            "地图.png": "PNG 图片",
            "资料.zip": "ZIP 压缩包",
            "网易云音乐.lnk": "娱乐游戏",
        }
        classifier = ClassifierService()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, expected in cases.items():
                path = root / name
                path.touch()
                self.assertEqual(classifier.classify_file(FileItem.from_path(path)), expected)

    def test_folder_is_always_a_folder(self):
        classifier = ClassifierService()
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "Python学习资料"
            folder.mkdir()
            self.assertEqual(classifier.classify_file(FileItem.from_path(folder)), "文件夹")

    def test_each_file_format_has_its_own_group(self):
        classifier = ClassifierService()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [root / "甲.docx", root / "乙.doc", root / "数据.xlsx", root / "清单.csv"]
            for path in paths:
                path.touch()
            groups = classifier.classify_files([FileItem.from_path(path) for path in paths])
            self.assertEqual(set(groups), {"DOCX 文档", "DOC 文档", "XLSX 表格", "CSV 表格"})

    def test_cleandesk_launcher_is_a_file_tool(self):
        classifier = ClassifierService()
        with tempfile.TemporaryDirectory() as directory:
            launcher = Path(directory) / "CleanDesk 桌面整理.lnk"
            launcher.touch()
            self.assertEqual(
                classifier.classify_file(FileItem.from_path(launcher)),
                "文件工具",
            )


if __name__ == "__main__":
    unittest.main()
