#!/usr/bin/env python3
"""Tests for entry requirements extraction, UCAS chain, and uni clean validation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from llm_extract import (  # noqa: E402
    canonicalize_requirement_degree,
    derive_uk_equivalent_requirements,
    enrich_stage1_from_markdown,
    extract_entry_lines_from_course_markdown,
    filter_bangladesh_descriptions_for_course,
    merge_requirement_lists,
    parse_bangladesh_json_requirements,
)
from normalize_admission_data import (  # noqa: E402
    alevel_combo_to_hsc_gpa,
    derive_hsc_gpa_from_uk_entry_text,
    process_record,
    ucas_points_to_alevel_combo,
)
from validate_uni_clean import validate_uni_clean  # noqa: E402
from uni_paths import resolve_output_dir  # noqa: E402


BCU_FOUNDATION_MD = Path(
    "Birmingham City University/output/clean/courses/foundation/2027 - 2028/"
    "accounting-and-finance-with-a-foundation-year-bsc-hons-2027-28.md"
)
BCU_CODE = Path("Birmingham City University/code")


class EntryRequirementsTests(unittest.TestCase):
    def test_hsc_alim_maps_to_hsc(self) -> None:
        self.assertEqual(canonicalize_requirement_degree("HSC (Alim)"), "HSC")

    def test_bangladesh_json_requirements_foundation(self) -> None:
        data = {
            "studyLevels": [
                {
                    "studyLevel": "Foundation",
                    "programs": [
                        {
                            "program": "Foundation",
                            "requirements": [
                                {"degree": "HSC (Alim)", "grade": "GPA of 2.00"}
                            ],
                            "description": [
                                "Completion of HSC (Alim): GPA of 2.00 or grade C with no less than 40% in any subject"
                            ],
                        }
                    ],
                }
            ]
        }
        requirements = parse_bangladesh_json_requirements(data, "foundation")
        self.assertEqual(requirements, [{"degree": "HSC", "grade": "GPA 2.00"}])

    def test_filter_bangladesh_keeps_hsc_policy_with_cdd_in_course(self) -> None:
        descriptions = [
            "Completion of HSC (Alim): GPA of 2.00 or grade C with no less than 40% in any subject"
        ]
        course_text = "A Level: 80 UCAS Tariff points / CDD (or equivalent)"
        kept = filter_bangladesh_descriptions_for_course(
            descriptions,
            course_text=course_text,
        )
        self.assertEqual(kept, descriptions)

    def test_extract_entry_lines_from_bcu_foundation_markdown(self) -> None:
        repo_root = _SHARED.parent
        md_path = repo_root / BCU_FOUNDATION_MD
        self.assertTrue(md_path.exists(), f"missing fixture: {md_path}")
        body = md_path.read_text(encoding="utf-8").split("---", 2)[-1]
        lines = extract_entry_lines_from_course_markdown(body)
        joined = "\n".join(lines)
        self.assertIn("80 UCAS Tariff points", joined)
        self.assertIn("CDD", joined)

    def test_enrich_stage1_backfills_entry_requirements(self) -> None:
        repo_root = _SHARED.parent
        md_path = repo_root / BCU_FOUNDATION_MD
        body = md_path.read_text(encoding="utf-8").split("---", 2)[-1]
        stage1 = enrich_stage1_from_markdown(
            {},
            course_body=body,
            course_name="Accounting and Finance with a Foundation Year - BSc (Hons)",
            course_url="https://www.bcu.ac.uk/courses/accounting-and-finance-with-a-foundation-year-bsc-hons-2027-28",
        )
        meta = stage1.get("AcademicRequirementsMetaData", [])
        entry = next(item for item in meta if item.get("subtitle") == "Entry Requirements")
        joined = "\n".join(entry.get("description", []))
        self.assertIn("CDD", joined)
        self.assertIn("80 UCAS Tariff points", joined)

    def test_ucas_points_to_cdd(self) -> None:
        self.assertEqual(ucas_points_to_alevel_combo(80), "CDD")

    def test_cdd_maps_to_hsc_gpa_3_5(self) -> None:
        self.assertEqual(alevel_combo_to_hsc_gpa("CDD"), 3.5)

    def test_derive_uk_equivalent_requirements(self) -> None:
        repo_root = _SHARED.parent
        body = (repo_root / BCU_FOUNDATION_MD).read_text(encoding="utf-8").split("---", 2)[-1]
        derived = derive_uk_equivalent_requirements(body, "foundation")
        self.assertEqual(derived, [{"degree": "HSC", "grade": "GPA 3.5"}])

    def test_merge_requirement_lists_allows_duplicate_hsc_grades(self) -> None:
        merged = merge_requirement_lists(
            [{"degree": "HSC", "grade": "GPA 2.00"}],
            [{"degree": "HSC", "grade": "GPA 3.5"}],
            course_level="foundation",
        )
        self.assertEqual(len(merged), 2)

    def test_process_record_uses_higher_hsc_gpa(self) -> None:
        result = process_record(
            {
                "courseName": "Test",
                "courseUrl": "https://example.com",
                "requirements": [
                    {"degree": "HSC", "grade": "GPA 2.00"},
                    {"degree": "HSC", "grade": "GPA 3.5"},
                ],
            }
        )
        self.assertEqual(result["minDegreeName"], "HSC")
        self.assertEqual(result["minGpa"], "3.5")
        self.assertEqual(result["higherGpa"], "")

    def test_derive_hsc_gpa_from_ucas_text(self) -> None:
        self.assertEqual(
            derive_hsc_gpa_from_uk_entry_text("80 UCAS Tariff points / CDD"),
            "GPA 3.5",
        )

    def test_validate_bcu_uni_clean_passes(self) -> None:
        repo_root = _SHARED.parent
        output_dir = resolve_output_dir(repo_root / BCU_CODE)
        report = validate_uni_clean(output_dir, university_name="Birmingham City University")
        self.assertEqual(report.error_count, 0, format_report_issues(report))


def format_report_issues(report) -> str:
    return "\n".join(issue.format_line() for issue in report.issues)


if __name__ == "__main__":
    unittest.main()
