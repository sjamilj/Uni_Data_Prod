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

    def test_prog_mode_part_time_only_html_excluded(self) -> None:
        html = (
            '<html><body><div id="prog-mode">'
            "<h3>Duration</h3><p>1 year part-time</p>"
            "</div></body></html>"
        )
        filt = CourseTypeFilter(
            exclude_course_types=["*part-time*"],
            exclude_url_patterns=[],
            course_type_selectors=[],
        )
        self.assertTrue(filt.should_exclude_html(html))

    def test_prog_mode_full_time_and_part_time_html_kept(self) -> None:
        html = (
            '<html><body><div id="prog-mode"><ul>'
            "<li>1 year full-time</li>"
            "<li>2 years part-time</li>"
            "</ul></div></body></html>"
        )
        filt = CourseTypeFilter(
            exclude_course_types=["*part-time*"],
            exclude_url_patterns=[],
            course_type_selectors=[],
        )
        self.assertFalse(filt.should_exclude_html(html))

    def test_overseas_students_no_html_excluded(self) -> None:
        html = (
            "<html><body>"
            "<h3>Available to overseas students?</h3><p>No</p>"
            "<h3>Can I use Prior Learning?</h3>"
            "<p>For entry: applicants with professional qualifications.</p>"
            "</body></html>"
        )
        filt = CourseTypeFilter(
            exclude_course_types=[],
            exclude_url_patterns=[],
            course_type_selectors=[],
        )
        self.assertTrue(filt.should_exclude_html(html))

    def test_overseas_students_yes_html_kept(self) -> None:
        html = (
            "<html><body>"
            "<h3>Available to overseas students?</h3><p>Yes</p>"
            "</body></html>"
        )
        filt = CourseTypeFilter(
            exclude_course_types=[],
            exclude_url_patterns=[],
            course_type_selectors=[],
        )
        self.assertFalse(filt.should_exclude_html(html))

    def test_prog_mode_sandwich_only_html_excluded(self) -> None:
        html = (
            '<html><body><div id="prog-mode">'
            "<h3>Duration</h3><p>2 years sandwich</p>"
            "</div></body></html>"
        )
        filt = CourseTypeFilter(
            exclude_course_types=["*sandwich*"],
            exclude_url_patterns=[],
            course_type_selectors=[],
        )
        self.assertTrue(filt.should_exclude_html(html))

    def test_industrial_practice_url_excluded(self) -> None:
        filt = CourseTypeFilter(
            exclude_course_types=["*sandwich*"],
            exclude_url_patterns=["*industrial-practice*"],
            course_type_selectors=[],
        )
        self.assertTrue(
            filt.url_is_excluded(
                "https://www.gre.ac.uk/postgraduate-courses/engsci/"
                "civil-engineering-with-industrial-practice-msc"
            )
        )


if __name__ == "__main__":
    unittest.main()
