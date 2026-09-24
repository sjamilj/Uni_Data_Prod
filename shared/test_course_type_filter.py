#!/usr/bin/env python3
"""Tests for course type / study mode exclusion."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_type_filter import CourseTypeFilter, CourseTypeExtractor  # noqa: E402

_PART_TIME_KEY_INFO_MD = """\
# Example postgraduate course

## Key course information

Study options

Part-time
"""

_FULL_TIME_STUDY_MODE_MD = "- **Study mode:** Full-time\n"


class CourseTypeFilterTests(unittest.TestCase):
    def test_part_time_study_options_excluded(self) -> None:
        self.assertEqual(
            CourseTypeExtractor.study_options_from_markdown(_PART_TIME_KEY_INFO_MD),
            "Part-time",
        )
        filt = CourseTypeFilter(
            exclude_course_types=["*part-time*"],
            exclude_url_patterns=[],
            course_type_selectors=[],
        )
        self.assertTrue(filt.should_exclude_markdown(_PART_TIME_KEY_INFO_MD))

    def test_part_time_duration_only_excluded(self) -> None:
        md = "**Duration:** 24 months part-time\n"
        filt = CourseTypeFilter(
            exclude_course_types=["*part-time*"],
            exclude_url_patterns=[],
            course_type_selectors=[],
        )
        self.assertTrue(filt.should_exclude_markdown(md))

    def test_full_time_not_excluded(self) -> None:
        filt = CourseTypeFilter(
            exclude_course_types=["*part-time*"],
            exclude_url_patterns=[],
            course_type_selectors=[],
        )
        self.assertFalse(filt.should_exclude_markdown(_FULL_TIME_STUDY_MODE_MD))


if __name__ == "__main__":
    unittest.main()
