import tempfile
import unittest
from pathlib import Path

import pandas as pd
from check_local import check_local


class ExamScheduleTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.agent_workspace = Path(self.workspace.name) / "agent"
        self.groundtruth_workspace = Path(self.workspace.name) / "groundtruth"
        self.agent_workspace.mkdir()
        self.groundtruth_workspace.mkdir()
        self.ground_row = {
            "Course Code": "NET101",
            "Course Name": "Computer Networks",
            "Proctor Name": "Debra Flores",
            "Proctor Email": "debra@example.com",
            "Open-book/Closed-book": "Closed-book",
            "Final Date (MM/DD/YYYY)": "12/10/2025",
            "Start Time (HH:MM)": "09:00",
            "Duration (minutes)": 120,
            "Location": "Room 101",
            "Information Source(Announcement/Email/Message)": "Email",
            "Course Credit": 4,
        }

    def evaluate(self, **changes):
        agent_row = {**self.ground_row, **changes}
        for workspace, row in (
            (self.agent_workspace, agent_row),
            (self.groundtruth_workspace, self.ground_row),
        ):
            pd.DataFrame([row]).to_excel(
                workspace / "exam_schedule.xlsx", index=False, engine="openpyxl"
            )
        return check_local(str(self.agent_workspace), str(self.groundtruth_workspace))

    def test_email_source_does_not_erase_earlier_mismatches(self):
        for column, value in (
            ("Course Name", "Wrong course"),
            ("Proctor Name", "Wrong proctor"),
            ("Location", "Wrong room"),
        ):
            with self.subTest(column=column):
                passed, error = self.evaluate(**{column: value})
                self.assertFalse(passed)
                self.assertIn("Match rate too low", error)

    def test_accepts_email_and_combined_sources(self):
        for source in ("Email", "Email & Announcement"):
            with self.subTest(source=source):
                self.assertEqual(
                    self.evaluate(
                        **{"Information Source(Announcement/Email/Message)": source}
                    ),
                    (True, None),
                )

    def test_rejects_source_without_email(self):
        passed, _ = self.evaluate(
            **{"Information Source(Announcement/Email/Message)": "Announcement"}
        )
        self.assertFalse(passed)

    def test_rejects_mismatch_after_information_source(self):
        passed, _ = self.evaluate(**{"Course Credit": 3})
        self.assertFalse(passed)

    def test_other_courses_still_require_matching_source(self):
        self.ground_row["Course Code"] = "CS101"
        passed, _ = self.evaluate(
            **{"Information Source(Announcement/Email/Message)": "Email & Announcement"}
        )
        self.assertFalse(passed)


if __name__ == "__main__":
    unittest.main()
