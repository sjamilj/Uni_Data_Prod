#!/usr/bin/env python3
"""Tests for missing_field_stats."""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from missing_field_stats import MissingFieldStats, REPORT_TXT_NAME  # noqa: E402


class MissingFieldStatsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.uni_name = "Test University - TU"
        self.uni_dir = self.root / self.uni_name
        self.output_dir = self.uni_dir / "output"
        self.output_dir.mkdir(parents=True)
        self.stats = MissingFieldStats(self.root)

        reviewed = self.output_dir / f"dev_courses_{self.uni_name}_reviewed.csv"
        with reviewed.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "courseName",
                    "courseUrlExternal",
                    "degreeName",
                    "tuitionFee",
                    "errorReason",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "courseName": "Economics BSc",
                    "courseUrlExternal": "https://example.ac.uk/study/courses/economics-bsc",
                    "degreeName": "BSc",
                    "tuitionFee": "18000",
                    "errorReason": "",
                }
            )
            writer.writerow(
                {
                    "courseName": "Accounting Foundation",
                    "courseUrlExternal": "https://example.ac.uk/study/courses/accounting-foundation",
                    "degreeName": "",
                    "tuitionFee": "",
                    "errorReason": "MISSING_REQUIRED_FIELD: missing required field(s): degreeName",
                }
            )

        level_csv = self.output_dir / "undergraduate_course_urls.csv"
        with level_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["course_url", "study_level", "source_scope"])
            writer.writeheader()
            writer.writerow(
                {
                    "course_url": "https://example.ac.uk/study/courses/economics-bsc",
                    "study_level": "undergraduate",
                    "source_scope": "UNDERGRADUATE",
                }
            )

        foundation_csv = self.output_dir / "foundation_course_urls.csv"
        with foundation_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["course_url", "study_level", "source_scope"])
            writer.writeheader()
            writer.writerow(
                {
                    "course_url": "https://example.ac.uk/study/courses/accounting-foundation",
                    "study_level": "foundation",
                    "source_scope": "FOUNDATION",
                }
            )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_generate_writes_report_txt(self) -> None:
        result = self.stats.generate(self.uni_name)
        self.assertTrue(result.report_txt.is_file())
        self.assertEqual(result.report_txt.name, REPORT_TXT_NAME)
        self.assertEqual(result.total_courses, 2)

        text = result.report_txt.read_text(encoding="utf-8")
        self.assertIn("missing field statistics", text)
        self.assertIn("Total courses: 2", text)
        self.assertIn("Foundation", text)
        self.assertIn("degreeName", text)
        self.assertNotIn("report_type", text)

    def test_dry_run_does_not_write_report(self) -> None:
        report_path = self.output_dir / REPORT_TXT_NAME
        result = self.stats.generate(self.uni_name, dry_run=True)
        self.assertFalse(report_path.exists())
        self.assertEqual(result.total_courses, 2)


if __name__ == "__main__":
    unittest.main()
