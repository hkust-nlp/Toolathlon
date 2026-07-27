import tempfile
import unittest
from pathlib import Path

from check_local import GT_STRUCTURE, scan_directory_structure, should_ignore_path


class FrameworkArtifactIgnoreTests(unittest.TestCase):
    def test_pdf_tool_temp_directory_and_contents_are_ignored(self):
        self.assertTrue(should_ignore_path(".pdf_tools_tempfiles"))
        self.assertTrue(
            should_ignore_path(".pdf_tools_tempfiles/rendered/page-1.png")
        )

    def test_root_overlong_output_directory_and_contents_are_ignored(self):
        self.assertTrue(should_ignore_path(".overlong_tool_outputs"))
        self.assertTrue(
            should_ignore_path(".overlong_tool_outputs/tool-result-1.json")
        )

    def test_similarly_named_or_nested_user_paths_are_not_ignored(self):
        self.assertFalse(should_ignore_path(".overlong_tool_outputs_backup"))
        self.assertFalse(
            should_ignore_path("Work/.overlong_tool_outputs/user-result.json")
        )

    def test_root_framework_artifacts_do_not_change_scanned_gt_structure(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)

            for directory in GT_STRUCTURE["directories"]:
                (root / directory).mkdir(parents=True, exist_ok=True)
            for file_path in GT_STRUCTURE["files"]:
                path = root / file_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()

            artifact = root / ".overlong_tool_outputs" / "tool-result-1.json"
            artifact.parent.mkdir()
            artifact.write_text("{}", encoding="utf-8")

            pdf_artifact = root / ".pdf_tools_tempfiles" / "rendered" / "page-1.png"
            pdf_artifact.parent.mkdir(parents=True)
            pdf_artifact.touch()

            self.assertEqual(scan_directory_structure(workspace), GT_STRUCTURE)


if __name__ == "__main__":
    unittest.main()
