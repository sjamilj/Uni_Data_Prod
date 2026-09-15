#!/usr/bin/env python3
"""Tests for entry requirements extraction, UCAS chain, and uni clean validation."""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from export_dev_courses import PortalLookup  # noqa: E402
from llm_extract import (  # noqa: E402
    Stage2Enricher,
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
    resolve_english_course_group,
    select_english_json_program,
)
from uni_pages import split_frontmatter  # noqa: E402
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

    def test_build_course_ielts_requirement_text(self) -> None:
        text = Stage2Enricher.build_course_ielts_requirement_text("6.5", "5.5")
        self.assertIn("IELTS 6.5 overall", text)
        self.assertIn("5.5 in all components", text)

    def test_inject_english_requirements_parsed_markdown(self) -> None:
        from inject_english_requirements_md import (
            ENGLISH_TESTS_MARKER,
            format_english_requirements_parsed_markdown,
            inject_english_requirements_into_markdown,
        )

        english_json = {
            "AcademicRequirementsMetaData": [
                {
                    "subtitle": "English Requirement",
                    "description": [
                        "IELTS Academic and IELTS Indicator 6.0 with 5.5 in all components",
                        "Pearson Academic (including online) 59 overall with 54 in each component",
                    ],
                }
            ],
            "ieltsMinOverall": "6.0",
            "ieltsMinSection": "5.5",
        }
        block = format_english_requirements_parsed_markdown(english_json)
        self.assertIn(ENGLISH_TESTS_MARKER, block)
        self.assertIn("```json", block)
        self.assertIn("Pearson Academic", block)
        fenced = re.search(r"```json\s*\n(.*?)\n```", block, re.S)
        self.assertIsNotNone(fenced)
        payload = json.loads(fenced.group(1))
        self.assertEqual(payload.get("ieltsMinOverall"), "6.0")

        body = (
            "## Entry requirements\n\n"
            "### English language requirements\n\n"
            "This course requires a result from Group A.\n"
        )
        updated, changed = inject_english_requirements_into_markdown(body, english_json)
        self.assertTrue(changed)
        self.assertIn("Group A.", updated)
        self.assertIn("IELTS Academic and IELTS Indicator 6.0", updated)
        updated_again, changed_again = inject_english_requirements_into_markdown(updated, english_json)
        self.assertTrue(changed_again)
        self.assertEqual(updated_again.count(ENGLISH_TESTS_MARKER), 1)

    def test_align_descriptions_to_course_ielts(self) -> None:
        from inject_english_requirements_md import align_descriptions_to_course_ielts

        descriptions = [
            "Postgraduate Group 3: IELTS 6.5 overall with no element below 5.5",
            "Pearson PTE Academic: 62 overall with no element below 59",
        ]
        profile = {"overall": "6.5", "min_section": "6.0", "all_components_min": "6.0"}
        aligned = align_descriptions_to_course_ielts(
            descriptions,
            profile,
            program_label="Group 3",
        )
        self.assertEqual(len(aligned), 2)
        self.assertIn("6.0", aligned[0])
        self.assertNotIn("5.5", aligned[0])
        self.assertIn("Pearson PTE Academic", aligned[1])

    def test_essex_stage1_international_fee_from_markdown(self) -> None:
        md_path = (
            _SHARED.parent
            / "University of Essex/output/clean/courses/foundation/ug00002-2-bsc-accounting-and-finance.md"
        )
        if not md_path.is_file():
            self.skipTest("Essex foundation sample markdown not present")
        _, course_body = split_frontmatter(md_path.read_text(encoding="utf-8"))
        fields = extract_stage1_fields_from_md(course_body)
        self.assertEqual(fields.get("tuitionFee"), "21500")
        self.assertEqual(fields.get("currency"), "GBP")

    def test_essex_stage1_international_fee_lone_gbp_line(self) -> None:
        rel_paths = (
            "University of Essex/output/clean/courses/postgraduate/pg00425-4-mres-accounting.md",
            "University of Essex/output/clean/courses/postgraduate/pg00426-1-msc-accounting-and-finance.md",
        )
        for rel in rel_paths:
            md_path = _SHARED.parent / rel
            with self.subTest(rel=rel):
                if not md_path.is_file():
                    self.skipTest("Essex PG fee sample markdown not present")
                _, course_body = split_frontmatter(md_path.read_text(encoding="utf-8"))
                fields = extract_stage1_fields_from_md(course_body)
                self.assertEqual(fields.get("tuitionFee"), "24675")
                self.assertEqual(fields.get("currency"), "GBP")

    def test_parse_english_from_course_markdown_essex(self) -> None:
        body = Path(_SHARED.parent / "University of Essex/output/clean/courses/undergraduate/ug00001-1-bsc-accounting.md").read_text(encoding="utf-8")
        _, course_body = split_frontmatter(body)
        parsed = Stage2Enricher.parse_english_from_course_markdown(course_body)
        self.assertEqual(parsed.get("ieltsMinOverall"), "6.0")
        self.assertEqual(parsed.get("ieltsMinSection"), "5.5")
        self.assertEqual(parsed.get("pteMinOverall"), "60")
        self.assertEqual(parsed.get("toeflMinOverall"), "82")
        meta = parsed.get("AcademicRequirementsMetaData") or []
        self.assertTrue(meta)
        descriptions = meta[0].get("description") or []
        self.assertTrue(any("Pearson PTE Academic" in str(line) for line in descriptions))

        enriched = Stage2Enricher.enrich_english_parsed(
            {},
            course_body,
            course_name="BSc Accounting",
            course_level="undergraduate",
            course_body=course_body,
            english_lookup_content="should not be used",
        )
        self.assertEqual(enriched.get("ieltsMinOverall"), "6.0")
        self.assertEqual(enriched.get("pteMinOverall"), "60")

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

    def test_select_english_json_program_by_numeric_group(self) -> None:
        programs = [
            {"ProgramName": "Group 1", "TestRequirements": [{"TestName": "IELTS Academic", "ieltsMinOverall": "6.0", "ieltsMinSection": "5.5"}]},
            {"ProgramName": "Group 3", "TestRequirements": [{"TestName": "IELTS Academic", "ieltsMinOverall": "6.5", "ieltsMinSection": "5.5"}]},
        ]
        course_body = "English language test group: Group 3"
        program = select_english_json_program(
            programs,
            course_level="postgraduate",
            course_name="MSc Accounting",
            course_body=course_body,
        )
        self.assertEqual(program["ProgramName"], "Group 3")

    def test_resolve_essex_english_course_group(self) -> None:
        groups = [
            {
                "courseName": "Acting (International)",
                "englishGroup": "Group 1",
                "studyLevel": "postgraduate",
                "department": "EAST 15 ACTING SCHOOL",
            },
            {
                "courseName": "Accounting",
                "englishGroup": "Group 3",
                "studyLevel": "postgraduate",
                "department": "ESSEX BUSINESS SCHOOL (EBS)",
            },
        ]
        body = """# MFA Acting

## Key course information

- **Course:** Acting (International)
- **Based in:** East 15 Acting School
"""
        group = resolve_english_course_group(
            groups,
            course_name="MFA Acting",
            course_body=body,
            course_level="postgraduate",
        )
        self.assertEqual(group, "Group 1")

    def test_resolve_pgr_course_uses_postgraduate_mapping(self) -> None:
        groups = [
            {
                "courseName": "Applied Mathematics",
                "englishGroup": "Group 1",
                "studyLevel": "postgraduate",
                "department": "SCHOOL OF MATHEMATICS, STATISTICS AND ACTUARIAL SCIENCE (SMSAS)",
            },
        ]
        body = """# PhD Applied Mathematics

## Key course information

- **Course:** Applied Mathematics
- **Based in:** Mathematics, Statistics and Actuarial Science (School of)
"""
        group = resolve_english_course_group(
            groups,
            course_name="PhD Applied Mathematics",
            course_body=body,
            course_level="postgraduate_research",
        )
        self.assertEqual(group, "Group 1")

    def test_disambiguate_management_by_ielts(self) -> None:
        from pathlib import Path

        from course_markdown_cleanup import parse_uni_json_payload
        from llm_extract import ExtractionPathConfig, load_uni_section

        repo = Path(__file__).resolve().parents[1]
        groups_md = repo / "University of Essex/output/clean/uni/english-course-groups.md"
        if not groups_md.exists():
            self.skipTest("Essex uni clean files not present")
        output_dir = repo / "University of Essex/output"
        groups = ExtractionPathConfig.load_english_course_groups(output_dir)
        english_programs = parse_uni_json_payload(
            load_uni_section(output_dir, "english-requirements.md"),
            "english-requirements",
        ) or []
        body = (
            repo / "University of Essex/output/clean/courses/postgraduate/pg00670-1-msc-management.md"
        ).read_text(encoding="utf-8")
        _, body = split_frontmatter(body)
        group = resolve_english_course_group(
            groups,
            course_name="MSc Management",
            course_body=body,
            course_level="postgraduate",
            english_programs=english_programs,
        )
        self.assertEqual(group, "Group 4")

    def test_disambiguate_sociology_by_ielts(self) -> None:
        from pathlib import Path

        from course_markdown_cleanup import parse_uni_json_payload
        from llm_extract import ExtractionPathConfig, load_uni_section

        repo = Path(__file__).resolve().parents[1]
        groups_md = repo / "University of Essex/output/clean/uni/english-course-groups.md"
        if not groups_md.exists():
            self.skipTest("Essex uni clean files not present")
        output_dir = repo / "University of Essex/output"
        groups = ExtractionPathConfig.load_english_course_groups(output_dir)
        english_programs = parse_uni_json_payload(
            load_uni_section(output_dir, "english-requirements.md"),
            "english-requirements",
        ) or []
        body = (
            repo / "University of Essex/output/clean/courses/postgraduate/pg00783-1-ma-sociology.md"
        ).read_text(encoding="utf-8")
        _, body = split_frontmatter(body)
        group = resolve_english_course_group(
            groups,
            course_name="MA Sociology",
            course_body=body,
            course_level="postgraduate",
            english_programs=english_programs,
        )
        self.assertEqual(group, "Group 5")

    def test_pick_preferred_group_on_ielts_tie(self) -> None:
        groups = [
            {
                "courseName": "International Hospitality Management",
                "englishGroup": "Group 3",
                "studyLevel": "postgraduate",
                "department": "EDGE HOTEL SCHOOL (EHS)",
            },
            {
                "courseName": "International Hospitality Management",
                "englishGroup": "Group 4",
                "studyLevel": "postgraduate",
                "department": "ESSEX BUSINESS SCHOOL (EBS)",
            },
        ]
        body = """# MSc International Hospitality Management

## Key course information

- **Course:** International Hospitality Management
- **Based in:** Edge Hotel School

### English language requirements

If English is not your first language, we require IELTS 6.5 overall with a minimum component score of 5.5
"""
        english_programs = [
            {
                "ProgramName": "Group 3",
                "TestRequirements": [{"TestName": "IELTS Academic", "ieltsMinOverall": "6.5", "ieltsMinSection": "5.5"}],
                "description": ["IELTS 6.5 overall with no element below 5.5"],
            },
            {
                "ProgramName": "Group 4",
                "TestRequirements": [{"TestName": "IELTS Academic", "ieltsMinOverall": "6.5", "ieltsMinSection": "5.5"}],
                "description": ["IELTS 6.5 overall with Listening 5.5, Reading 5.5, Writing 6.0 and Speaking 5.5"],
            },
        ]
        group = resolve_english_course_group(
            groups,
            course_name="MSc International Hospitality Management",
            course_body=body,
            course_level="postgraduate",
            english_programs=english_programs,
        )
        self.assertEqual(group, "Group 3")

    def test_extract_course_ielts_each_component_pattern(self) -> None:
        body = """### English language requirements

IELTS 6.0 overall with a minimum of 5.5 in each component, or specified score in an equivalent test that we accept.
"""
        profile = Stage2Enricher.extract_course_ielts_profile(body)
        self.assertEqual(profile["overall"], "6.0")
        self.assertEqual(profile["all_components_min"], "5.5")
        self.assertEqual(profile["min_section"], "5.5")

    def test_extract_course_ielts_each_component_without_overall(self) -> None:
        body = """### English language requirements

IELTS 6.5 with a minimum of 5.5 in each component
"""
        profile = Stage2Enricher.extract_course_ielts_profile(body)
        self.assertEqual(profile["overall"], "6.5")
        self.assertEqual(profile["min_section"], "5.5")

    def test_extract_course_ielts_strips_trailing_period(self) -> None:
        body = """### English language requirements

If English is not your first language, we require IELTS 6.5 overall with a minimum component score of 5.5.
"""
        profile = Stage2Enricher.extract_course_ielts_profile(body)
        self.assertEqual(profile["overall"], "6.5")
        self.assertEqual(profile["min_section"], "5.5")

    def test_extract_course_ielts_score_of_pattern(self) -> None:
        body = """### English language requirements

If English is not your first language we require an IELTS score of 6.5 or a TOEFL score of 580/240.
"""
        profile = Stage2Enricher.extract_course_ielts_profile(body)
        self.assertEqual(profile["overall"], "6.5")

    def test_extract_course_ielts_score_of_with_components(self) -> None:
        body = """### English language requirements

If English is not your first language we require an IELTS score of 7.0, with 6.5 in all components.
"""
        profile = Stage2Enricher.extract_course_ielts_profile(body)
        self.assertEqual(profile["overall"], "7.0")
        self.assertEqual(profile["all_components_min"], "6.5")
        self.assertEqual(profile["min_section"], "6.5")

    def test_extract_course_ielts_overall_or_equivalent(self) -> None:
        body = """### English language requirements

IELTS 6.5 overall or equivalent
"""
        profile = Stage2Enricher.extract_course_ielts_profile(body)
        self.assertEqual(profile["overall"], "6.5")

    def test_extract_course_ielts_or_equivalent_shorthand(self) -> None:
        body = """### English language requirements

IELTS 7.0 or equivalent
"""
        profile = Stage2Enricher.extract_course_ielts_profile(body)
        self.assertEqual(profile["overall"], "7.0")

    def test_extract_course_ielts_or_equivalent_all_other_components(self) -> None:
        body = """### English language requirements

IELTS 6.5 overall, or equivalent, with a score of 5.5 in all other components.
"""
        profile = Stage2Enricher.extract_course_ielts_profile(body)
        self.assertEqual(profile["overall"], "6.5")
        self.assertEqual(profile["min_section"], "5.5")

    def test_extract_course_ielts_or_equivalent_minimum_all_other(self) -> None:
        body = """### English language requirements

IELTS 7.0 overall, or equivalent, with a minimum score of 5.5 in all other components.
"""
        profile = Stage2Enricher.extract_course_ielts_profile(body)
        self.assertEqual(profile["overall"], "7.0")
        self.assertEqual(profile["all_components_min"], "5.5")

    def test_extract_course_ielts_level_on_ielts(self) -> None:
        body = """### English language requirements

Demonstrate proficiency in English. If your first language is not English you will need to obtain at least level 7 (with no component below 7) on the IELTS or equivalent (eg TOEFL).
"""
        profile = Stage2Enricher.extract_course_ielts_profile(body)
        self.assertEqual(profile["overall"], "7")
        self.assertEqual(profile["all_components_min"], "7")
        self.assertEqual(profile["min_section"], "7")

    def test_extract_course_ielts_overall_score_with_component_scores(self) -> None:
        body = """### English language requirements

IELTS with an overall score of 7.0, and minimum component scores of 6.5.
"""
        profile = Stage2Enricher.extract_course_ielts_profile(body)
        self.assertEqual(profile["overall"], "7.0")
        self.assertEqual(profile["min_section"], "6.5")

    def test_extract_course_ielts_ielst_typo(self) -> None:
        body = """### English language requirements

If English is not your first language , we require IELST 7.0, or equivalent with a minimum of 5.5 in all other components.
"""
        profile = Stage2Enricher.extract_course_ielts_profile(body)
        self.assertEqual(profile["overall"], "7.0")
        self.assertEqual(profile["min_section"], "5.5")

    def test_conflict_resolution_maps_to_flat_ielts_row(self) -> None:
        from pathlib import Path

        from course_markdown_cleanup import parse_uni_json_payload
        from llm_extract import ExtractionPathConfig, load_uni_section, select_english_json_program

        repo = Path(__file__).resolve().parents[1]
        output_dir = repo / "University of Essex/output"
        english_programs = parse_uni_json_payload(
            load_uni_section(output_dir, "english-requirements.md"),
            "english-requirements",
        ) or []
        body = (
            repo / "University of Essex/output/clean/courses/postgraduate/pg00508-1-ma-conflict-resolution.md"
        ).read_text(encoding="utf-8")
        _, body = split_frontmatter(body)
        groups = ExtractionPathConfig.load_english_course_groups(output_dir)
        group = resolve_english_course_group(
            groups,
            course_name="MA Conflict Resolution",
            course_body=body,
            course_level="postgraduate",
            english_programs=english_programs,
        )
        program = select_english_json_program(
            english_programs,
            course_level="postgraduate",
            course_name="MA Conflict Resolution",
            course_body=body,
        )
        self.assertEqual(group, "Group 3")
        self.assertEqual(program.get("ieltsMinOverall"), "6.5")
        self.assertEqual(program.get("ieltsMinSection"), "5.5")
        self.assertIn("Group 3", " ".join(program.get("description", [])))

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
