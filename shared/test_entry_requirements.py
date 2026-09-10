#!/usr/bin/env python3
"""Tests for entry requirements extraction, UCAS chain, and uni clean validation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from export_dev_courses import PortalLookup  # noqa: E402
from llm_extract import (  # noqa: E402
    build_output_json,
    canonicalize_requirement_degree,
    derive_uk_equivalent_requirements,
    enrich_stage1_from_markdown,
    extract_bangladesh_section_text,
    extract_entry_lines_from_course_markdown,
    extract_stage1_fields_from_md,
    filter_bangladesh_descriptions_for_course,
    infer_degree_name_from_md,
    merge_requirement_lists,
    parse_bangladesh_json_requirements,
    select_english_json_program,
)
from normalize_admission_data import (  # noqa: E402
    _extract_gbp_fee_from_metadata,
    alevel_combo_to_hsc_gpa,
    derive_hsc_gpa_from_uk_entry_text,
    process_record,
    sanitize_international_tuition_fee,
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

    def test_aru_stage1_parser_extracts_intake_and_tuition(self) -> None:
        md_path = Path(
            "Anglia Ruskin University - ARU/output/clean/courses/foundation/"
            "study-undergraduate-accounting-and-finance.md"
        )
        if not md_path.exists():
            self.skipTest("ARU sample markdown not in workspace")
        body = md_path.read_text(encoding="utf-8")
        hints = extract_stage1_fields_from_md(body)
        self.assertEqual(hints["tuitionFee"], "17500")
        self.assertEqual(hints["intakeInfo"], "January 2027, September 2026")
        self.assertEqual(hints["courseDuration"], "4 years with foundation")
        self.assertEqual(hints["degreeName"], "BSc")

    def test_aru_research_overview_start_label_parses_intake(self) -> None:
        md_path = Path(
            "Anglia Ruskin University - ARU/output/clean/courses/postgraduate_research/"
            "study-postgraduate-animal-and-environmental-sciences.md"
        )
        if not md_path.exists():
            self.skipTest("ARU research sample markdown not in workspace")
        body = md_path.read_text(encoding="utf-8")
        hints = extract_stage1_fields_from_md(body)
        self.assertEqual(hints["intakeInfo"], "January 2027, April, September 2026")

    def test_aru_research_completion_dates_parse_duration(self) -> None:
        md_path = Path(
            "Anglia Ruskin University - ARU/output/clean/courses/postgraduate_research/"
            "study-postgraduate-animal-and-environmental-sciences.md"
        )
        if not md_path.exists():
            self.skipTest("ARU research sample markdown not in workspace")
        body = md_path.read_text(encoding="utf-8")
        hints = extract_stage1_fields_from_md(body)
        self.assertEqual(hints["courseDuration"], "2-4 years")

    def test_aru_professional_doctorate_type_line_parses_duration(self) -> None:
        md_path = Path(
            "Anglia Ruskin University - ARU/output/clean/courses/postgraduate_research/"
            "study-postgraduate-professional-doctorate-in-health-and-social-care.md"
        )
        if not md_path.exists():
            self.skipTest("ARU professional doctorate sample markdown not in workspace")
        body = md_path.read_text(encoding="utf-8")
        hints = extract_stage1_fields_from_md(body)
        self.assertEqual(hints["courseDuration"], "6 years part-time")

    def test_aru_infer_degree_name_from_course_overview_line(self) -> None:
        md_path = Path(
            "Anglia Ruskin University - ARU/output/clean/courses/foundation/"
            "study-undergraduate-accounting-and-finance.md"
        )
        if not md_path.exists():
            self.skipTest("ARU sample markdown not in workspace")
        body = md_path.read_text(encoding="utf-8")
        self.assertEqual(infer_degree_name_from_md(body), "BSc")

    def test_enrich_stage1_sets_degree_name_from_markdown(self) -> None:
        md_path = Path(
            "Anglia Ruskin University - ARU/output/clean/courses/foundation/"
            "study-undergraduate-accounting-and-finance.md"
        )
        if not md_path.exists():
            self.skipTest("ARU sample markdown not in workspace")
        body = md_path.read_text(encoding="utf-8")
        enriched = enrich_stage1_from_markdown(
            {},
            course_body=body,
            course_name="Accounting and Finance",
            course_url="https://www.aru.ac.uk/study/undergraduate/accounting-and-finance",
        )
        self.assertEqual(enriched["degreeName"], "BSc")

    def test_portal_degree_name_only_when_row_empty(self) -> None:
        lookup = PortalLookup()
        lookup.by_url["/study/undergraduate/accounting-and-finance"] = {
            "programmeName": "Accounting and Finance",
            "degreeName": "FDA",
        }
        row = {
            "courseName": "Accounting and Finance",
            "courseUrlExternal": "https://www.aru.ac.uk/study/undergraduate/accounting-and-finance",
            "degreeName": "",
        }
        lookup.apply_to_row(row)
        self.assertEqual(row["degreeName"], "FDA")

        row_with_degree = {
            "courseName": "Accounting and Finance",
            "courseUrlExternal": "https://www.aru.ac.uk/study/undergraduate/accounting-and-finance",
            "degreeName": "BSc",
        }
        lookup.apply_to_row(row_with_degree)
        self.assertEqual(row_with_degree["degreeName"], "BSc")

    def test_build_output_json_includes_degree_name(self) -> None:
        output = build_output_json(
            {"degreeName": "BSc", "intakeInfo": "September 2026"},
            {},
            university_name="Test Uni",
            course_name="Accounting and Finance",
            course_url="https://example.ac.uk/course",
            degree_name="BSc",
        )
        self.assertEqual(output["degreeName"], "BSc")

    def test_process_record_passes_degree_name(self) -> None:
        result = process_record(
            {
                "courseName": "Accounting and Finance",
                "courseUrl": "https://example.ac.uk/course",
                "degreeName": "BSc",
                "requirements": [{"degree": "HSC", "grade": "3.0"}],
            }
        )
        self.assertEqual(result["degreeName"], "BSc")

    def test_aru_parser_extracts_fee_before_international_students(self) -> None:
        body = (
            "£18,400 International students starting 2026/27 (full-time, per year)\n"
        )
        hints = extract_stage1_fields_from_md(body)
        self.assertEqual(hints["tuitionFee"], "18400")
        self.assertEqual(hints["currency"], "GBP")

    def test_aston_partially_funded_phd_parses_duration_and_fee_difference(self) -> None:
        body = (
            "Programme length: 3 years\n"
            "Currently, the difference between 'Home' and the 'Overseas' tuition fees is £17,712 for 2026/7.\n"
        )
        hints = extract_stage1_fields_from_md(body)
        self.assertEqual(hints["courseDuration"], "3 years")
        self.assertEqual(hints["tuitionFee"], "17712")
        self.assertEqual(hints["currency"], "GBP")

    def test_enrich_stage1_promotes_nested_international_fees_metadata(self) -> None:
        md_path = Path(
            "Anglia Ruskin University - ARU/output/clean/courses/undergraduate/"
            "study-undergraduate-applied-sport-science-and-coaching-top-up.md"
        )
        if not md_path.exists():
            self.skipTest("ARU top-up sample markdown not in workspace")
        body = md_path.read_text(encoding="utf-8")
        stage1 = {
            "tuitionFee": 0,
            "currency": "",
            "feesMetaData": {
                "UK students starting 2026/27 (full-time, per year)": {
                    "fee": 9790,
                    "currency": "GBP",
                },
                "International students starting 2026/27 (full-time, per year)": {
                    "fee": 18400,
                    "currency": "GBP",
                },
            },
        }
        enriched = enrich_stage1_from_markdown(
            stage1,
            course_body=body,
            course_name="Applied Sport Science and Coaching (Top Up)",
            course_url="https://www.aru.ac.uk/study/undergraduate/applied-sport-science-and-coaching-top-up",
        )
        self.assertEqual(enriched["tuitionFee"], "18400")
        self.assertEqual(enriched["currency"], "GBP")
        self.assertEqual(enriched["intakeInfo"], "September 2026")

    def test_enrich_stage1_promotes_fees_metadata_object(self) -> None:
        md_path = Path(
            "Anglia Ruskin University - ARU/output/clean/courses/foundation/"
            "study-undergraduate-accounting-and-finance.md"
        )
        if not md_path.exists():
            self.skipTest("ARU sample markdown not in workspace")
        body = md_path.read_text(encoding="utf-8")
        stage1 = {
            "feesMetaData": {
                "tuitionFee": 17500,
                "currency": "GBP",
                "placementYearFee": 1700,
            }
        }
        enriched = enrich_stage1_from_markdown(
            stage1,
            course_body=body,
            course_name="Accounting and Finance",
            course_url="https://www.aru.ac.uk/study/undergraduate/accounting-and-finance",
        )
        self.assertEqual(enriched["tuitionFee"], "17500")
        self.assertEqual(enriched["intakeInfo"], "January 2027, September 2026")
        self.assertTrue(enriched["feesMetaData"])
        self.assertIn("17,500", str(enriched["feesMetaData"]))

    def test_extract_gbp_fee_ignores_placement_year_amount(self) -> None:
        meta_text = (
            "International tuition fee: £18,000 (full-time, per year)\n"
            "During placement year: £2,500"
        )
        fee, currency = _extract_gbp_fee_from_metadata(meta_text)
        self.assertEqual(fee, "18000")
        self.assertEqual(currency, "GBP")

    def test_sanitize_keeps_parser_tuition_when_metadata_is_deposit_only(self) -> None:
        record = {
            "tuitionFee": "18000",
            "currency": "GBP",
            "feesMetaData": [
                {
                    "subtitle": "Initial Deposit",
                    "description": ["You'll pay a £4,000 deposit before CAS."],
                }
            ],
        }
        sanitize_international_tuition_fee(record, fee_from_candidates=False)
        self.assertEqual(record["tuitionFee"], "18000")
        self.assertEqual(record["currency"], "GBP")

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

    def test_extract_bangladesh_country_block_from_course(self) -> None:
        body = "## Entry requirements\n#### Bangladesh\n60% in a 4-year degree\n"
        text = extract_bangladesh_section_text(body, "postgraduate")
        self.assertIn("60% in a 4-year degree", text)

    def test_select_english_json_program_by_group(self) -> None:
        programs = [
            {"ProgramName": "Group A", "TestRequirements": [{"TestName": "IELTS Academic", "ieltsMinOverall": "6.0", "ieltsMinSection": "5.5"}]},
            {"ProgramName": "Group B", "TestRequirements": [{"TestName": "IELTS Academic", "ieltsMinOverall": "6.5", "ieltsMinSection": "5.5"}]},
        ]
        course_body = "This course requires a test from Group B."
        program = select_english_json_program(
            programs,
            course_level="postgraduate",
            course_name="Law and Society",
            course_body=course_body,
        )
        self.assertEqual(program["ProgramName"], "Group B")
        self.assertEqual(program["TestRequirements"][0]["ieltsMinOverall"], "6.5")

    def test_keele_stage1_fields_from_key_information(self) -> None:
        body = """## Key information
### Year of entry

- 2027 - for 2027 entry see here  - for 2026 entry see here

### Duration of study

- 3 years or 4 years with international, placement or entrepreneurship year

## Fees and funding

- International: Band 1, £18,200 for the 2026/27 academic year
"""
        hints = extract_stage1_fields_from_md(body)
        self.assertEqual(hints["intakeInfo"], "January 2027, September 2026")
        self.assertEqual(hints["courseDuration"], "3 years")
        self.assertEqual(hints["tuitionFee"], "18200")
        self.assertEqual(hints["currency"], "GBP")

    def test_keele_stage1_fields_pg_month_of_entry(self) -> None:
        body = """## Key information
### Month of entry

- September

### Fees for 2026/27 academic year

- UK - Full time £10,400 per year.  International - £18,200 per year.
"""
        hints = extract_stage1_fields_from_md(body)
        self.assertEqual(hints["intakeInfo"], "September 2026")
        self.assertEqual(hints["tuitionFee"], "18200")


def format_report_issues(report) -> str:
    return "\n".join(issue.format_line() for issue in report.issues)


if __name__ == "__main__":
    unittest.main()
