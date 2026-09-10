#!/usr/bin/env python3
"""Tests for Keele entry requirement parser."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
_SHARED = _CODE_DIR.parents[1] / "shared"
if str(_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(_CODE_DIR))
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from keele_bangladesh_rules import detect_uk_class, pg_requirement_for_uk_class  # noqa: E402
from parse_keele_requirements import parse_keele_requirements  # noqa: E402


class KeeleEntryParserTests(unittest.TestCase):
    def test_biomedical_grad_dip_successful_completion(self) -> None:
        raw = [
            {
                "country": "Bangladesh",
                "description": [
                    "Successful completion of a degree in a bioscience, medical, or pharmacology related subject"
                ],
            }
        ]
        items = parse_keele_requirements(raw, study_level="postgraduate")
        self.assertEqual(items, [{"degree": "BSc", "grade": "CGPA 2.8"}])

    def test_alim_hsc_foundation(self) -> None:
        raw = [
            {
                "degree": "Foundation",
                "grades": [
                    "Completion of Alim/HSC: (new GPA system) GPA of 2.00 or (Old system) grade C"
                ],
            }
        ]
        items = parse_keele_requirements(raw, study_level="foundation")
        self.assertTrue(any(item["degree"] == "HSC" and "2.00" in item["grade"] for item in items))

    def test_hsc_cgpa_pass_through(self) -> None:
        raw = [{"country": "Bangladesh", "degree": "HSC", "grade": "CGPA of 5.0"}]
        items = parse_keele_requirements(raw, study_level="undergraduate")
        self.assertEqual(items[0]["degree"], "HSC")
        self.assertIn("5.0", items[0]["grade"])

    def test_plain_string_list(self) -> None:
        raw = [
            "2 year undergraduate degree at 60% or above.",
            "Higher Secondary Certificate a CGPA of 5.0.",
        ]
        items = parse_keele_requirements(raw, study_level="foundation")
        self.assertTrue(any(item["degree"] == "HSC" for item in items))

    def test_uk_class_in_qualification(self) -> None:
        raw = [
            {
                "qualification": "2:1 honours degree in psychology",
                "grade": "",
                "degree": "",
            }
        ]
        items = parse_keele_requirements(raw, study_level="postgraduate")
        self.assertEqual(items, [{"degree": "BSc", "grade": "CGPA 3.0"}])

    def test_capitalized_degree_grade(self) -> None:
        raw = [{"Degree": "BSc", "Qualification": "Level 5 degree", "Grade": "50%"}]
        items = parse_keele_requirements(raw, study_level="undergraduate")
        self.assertEqual(items[0]["degree"], "BSc")
        self.assertIn("50", items[0]["grade"])

    def test_detect_uk_class_phrases(self) -> None:
        self.assertEqual(detect_uk_class("good honours degree"), "2:1")
        self.assertEqual(detect_uk_class("Successful completion of a degree"), "2:2")
        self.assertEqual(pg_requirement_for_uk_class("2:1"), ("BSc", "CGPA 3.0"))


if __name__ == "__main__":
    unittest.main()
