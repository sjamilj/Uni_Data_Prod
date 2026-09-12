#!/usr/bin/env python3
"""Tests for course title inference from cleaned markdown."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from llm_extract import ExtractionPathConfig  # noqa: E402


class InferCourseNameTests(unittest.TestCase):
    def test_skips_cookie_banner_heading(self) -> None:
        body = (
            "# Your choice regarding cookies on this site\n\n"
            "## Key information\n\nStart Dates\n"
        )
        url = (
            "https://courses.hud.ac.uk/2027-28/undergraduate/"
            "automotive-and-motorsport-engineering-with-foundation-year-beng-hons"
        )
        self.assertEqual(
            ExtractionPathConfig.infer_course_name(body, url),
            "Automotive And Motorsport Engineering With Foundation Year Beng Hons",
        )

    def test_uses_real_course_heading_when_present(self) -> None:
        body = "# Health Foundation Pathway leading to a BSc(Hons) Degree\n\n## Key information\n"
        url = (
            "https://courses.hud.ac.uk/2027-28/undergraduate/"
            "health-foundation-pathway-leading-to-a-bsc-hons-degree"
        )
        self.assertEqual(
            ExtractionPathConfig.infer_course_name(body, url),
            "Health Foundation Pathway leading to a BSc(Hons) Degree",
        )

    def test_skips_cookie_heading_and_uses_later_heading(self) -> None:
        body = (
            "# Your choice regarding cookies on this site\n\n"
            "# Accounting and Finance BSc(Hons)\n"
        )
        url = "https://courses.hud.ac.uk/2027-28/undergraduate/accounting-and-finance-bsc-hons"
        self.assertEqual(
            ExtractionPathConfig.infer_course_name(body, url),
            "Accounting and Finance BSc(Hons)",
        )


if __name__ == "__main__":
    unittest.main()
