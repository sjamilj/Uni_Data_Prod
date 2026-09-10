#!/usr/bin/env python3
"""Tests for intake-year URL deduplication."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from study_level import dedupe_course_records_by_latest_intake  # noqa: E402


class IntakeDedupeTests(unittest.TestCase):
    def test_keeps_latest_intake_per_course_identity(self) -> None:
        records = [
            {
                "course_url": "https://www.bcu.ac.uk/courses/accounting-and-finance-with-a-foundation-year-bsc-hons-2026-27",
                "study_level": "foundation",
            },
            {
                "course_url": "https://www.bcu.ac.uk/courses/accounting-and-finance-with-a-foundation-year-bsc-hons-2027-28",
                "study_level": "foundation",
            },
            {
                "course_url": "https://www.bcu.ac.uk/courses/architectural-technology-foundation-bsc-hons-2027-28",
                "study_level": "foundation",
            },
        ]
        kept, skipped = dedupe_course_records_by_latest_intake(records)
        self.assertEqual(len(kept), 2)
        self.assertEqual(len(skipped), 1)
        self.assertIn("2027-28", kept[0]["course_url"])
        self.assertTrue(any("2027-28" in row["course_url"] for row in kept))
        self.assertTrue(any("2026-27" in url for url in skipped))

    def test_does_not_merge_different_study_levels(self) -> None:
        records = [
            {
                "course_url": "https://example.ac.uk/courses/foo-bsc-hons-2026-27",
                "study_level": "foundation",
            },
            {
                "course_url": "https://example.ac.uk/courses/foo-bsc-hons-2027-28",
                "study_level": "undergraduate",
            },
        ]
        kept, skipped = dedupe_course_records_by_latest_intake(records)
        self.assertEqual(len(kept), 2)
        self.assertEqual(skipped, [])


if __name__ == "__main__":
    unittest.main()
