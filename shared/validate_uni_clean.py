#!/usr/bin/env python3
"""Validate output/clean/uni/*.md against pipeline parsers before LLM extraction."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from course_markdown_cleanup import parse_uni_json_payload
from llm_extract import (
    BANGLADESH_JSON_LEVEL_ALIASES,
    ENGLISH_JSON_LEVEL_ALIASES,
    FOUNDATION_ENTRY_DEGREES,
    PG_ENTRY_DEGREES,
    UG_ENTRY_DEGREES,
    canonicalize_requirement_degree,
    extract_grade_from_requirement_text,
    load_uni_section,
    scholarship_study_level_matches,
)
from uni_pages import UNI_MD_BY_ROLE
from uni_paths import resolve_code_dir, resolve_output_dir

LEVEL_DEGREE_ALLOWLIST = {
    "foundation": FOUNDATION_ENTRY_DEGREES,
    "undergraduate": UG_ENTRY_DEGREES,
    "postgraduate": PG_ENTRY_DEGREES,
}

PIPELINE_LEVELS = ("foundation", "undergraduate", "postgraduate")


@dataclass
class ValidationIssue:
    level: str
    code: str
    file: str
    message: str

    def format_line(self) -> str:
        return f"{self.level} [{self.code}] {self.file}\n  {self.message}"


@dataclass
class ValidationReport:
    university: str
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.level == "ERROR")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.level == "WARN")

    def add(self, level: str, code: str, file: str, message: str) -> None:
        self.issues.append(ValidationIssue(level=level, code=code, file=file, message=message))


def _pipeline_level_for_study_level(study_level: str) -> str | None:
    normalized = study_level.strip().lower()
    for pipeline_level, aliases in BANGLADESH_JSON_LEVEL_ALIASES.items():
        if normalized in aliases:
            return pipeline_level
    return None


def _allowed_degrees_for_study_level(study_level: str) -> set[str]:
    pipeline_level = _pipeline_level_for_study_level(study_level)
    if not pipeline_level:
        return set()
    return LEVEL_DEGREE_ALLOWLIST[pipeline_level]


def validate_bangladesh_entry(content: str, filename: str, report: ValidationReport) -> None:
    data = parse_uni_json_payload(content, "bangladesh-entry")
    if not isinstance(data, dict):
        report.add("ERROR", "json_parse_failed", filename, "Could not parse bangladesh-entry JSON payload")
        return

    study_levels = data.get("studyLevels")
    if not isinstance(study_levels, list) or not study_levels:
        report.add("ERROR", "missing_study_levels", filename, "studyLevels must be a non-empty array")
        return

    seen_pipeline_levels: set[str] = set()
    for level_index, level in enumerate(study_levels):
        if not isinstance(level, dict):
            report.add(
                "ERROR",
                "invalid_study_level",
                filename,
                f"studyLevels[{level_index}] must be an object",
            )
            continue

        study_level = str(level.get("studyLevel", "") or "").strip()
        if not study_level:
            report.add(
                "ERROR",
                "missing_study_level_name",
                filename,
                f"studyLevels[{level_index}] is missing studyLevel",
            )
            continue

        pipeline_level = _pipeline_level_for_study_level(study_level)
        if not pipeline_level:
            report.add(
                "ERROR",
                "unknown_study_level",
                filename,
                f'studyLevel "{study_level}" does not match foundation/undergraduate/postgraduate aliases',
            )
            continue
        seen_pipeline_levels.add(pipeline_level)

        allowed_degrees = _allowed_degrees_for_study_level(study_level)
        programs = level.get("programs", [])
        if not isinstance(programs, list) or not programs:
            report.add(
                "WARN",
                "missing_programs",
                filename,
                f"{study_level} has no programs[] entries",
            )
            continue

        for program_index, program in enumerate(programs):
            if not isinstance(program, dict):
                continue
            requirements = program.get("requirements", [])
            if not isinstance(requirements, list) or not requirements:
                report.add(
                    "WARN",
                    "missing_requirements",
                    filename,
                    f"{study_level} programs[{program_index}] has no requirements[]",
                )

            descriptions = program.get("description", [])
            if not descriptions:
                report.add(
                    "WARN",
                    "missing_description",
                    filename,
                    f"{study_level} programs[{program_index}] has empty description[]",
                )

            for req_index, requirement in enumerate(requirements or []):
                if not isinstance(requirement, dict):
                    continue
                raw_degree = str(requirement.get("degree", "") or "").strip()
                raw_grade = str(requirement.get("grade", "") or "").strip()
                if not raw_degree:
                    report.add(
                        "ERROR",
                        "missing_degree",
                        filename,
                        f"{study_level} requirements[{req_index}] is missing degree",
                    )
                    continue
                if not raw_grade:
                    report.add(
                        "ERROR",
                        "missing_grade",
                        filename,
                        f"{study_level} requirements[{req_index}] is missing grade",
                    )
                    continue

                canonical = canonicalize_requirement_degree(raw_degree)
                if canonical not in allowed_degrees:
                    report.add(
                        "ERROR",
                        "degree_unmapped",
                        filename,
                        (
                            f'{study_level} requirements[{req_index}].degree "{raw_degree}" '
                            f'canonicalizes to "{canonical}" which is not in {sorted(allowed_degrees)}'
                        ),
                    )

                extracted_grade = extract_grade_from_requirement_text(raw_grade)
                if not extracted_grade:
                    report.add(
                        "ERROR",
                        "grade_unextractable",
                        filename,
                        f'{study_level} requirements[{req_index}].grade "{raw_grade}" could not be parsed',
                    )

    for pipeline_level in PIPELINE_LEVELS:
        if pipeline_level not in seen_pipeline_levels:
            report.add(
                "WARN",
                "missing_pipeline_level",
                filename,
                f"No studyLevel block found for pipeline level '{pipeline_level}'",
            )


def validate_english_requirements(content: str, filename: str, report: ValidationReport) -> None:
    data = parse_uni_json_payload(content, "english-requirements")
    if not isinstance(data, list) or not data:
        report.add("ERROR", "json_parse_failed", filename, "Could not parse english-requirements JSON array")
        return

    rows_without_level = 0
    for index, row in enumerate(data):
        if not isinstance(row, dict):
            report.add("ERROR", "invalid_row", filename, f"english row[{index}] must be an object")
            continue
        test_level = str(row.get("TestStudyLevel", "") or "").strip()
        if not test_level:
            rows_without_level += 1
            continue
        aliases = set()
        for level_aliases in ENGLISH_JSON_LEVEL_ALIASES.values():
            aliases.update(level_aliases)
        if test_level.strip().lower() not in aliases:
            report.add(
                "WARN",
                "unknown_english_study_level",
                filename,
                f'english row[{index}] TestStudyLevel "{test_level}" is not a known alias',
            )

    if rows_without_level:
        report.add(
            "WARN",
            "english_no_study_level",
            filename,
            f"{rows_without_level} row(s) missing TestStudyLevel — pipeline uses heuristics / Stage 1 fallback",
        )


def validate_scholarships(content: str, filename: str, report: ValidationReport) -> None:
    data = parse_uni_json_payload(content, "scholarships")
    if not isinstance(data, list) or not data:
        report.add("ERROR", "json_parse_failed", filename, "Could not parse scholarships JSON array")
        return

    for index, item in enumerate(data):
        if not isinstance(item, dict):
            report.add("ERROR", "invalid_row", filename, f"scholarship[{index}] must be an object")
            continue
        study_level = str(item.get("scholarshipStudyLevel", "") or "").strip()
        if not study_level:
            report.add(
                "WARN",
                "missing_scholarship_study_level",
                filename,
                f'scholarship[{index}] "{item.get("scholarshipName", "")}" missing scholarshipStudyLevel',
            )
            continue
        if not any(
            scholarship_study_level_matches(study_level, pipeline_level)
            for pipeline_level in PIPELINE_LEVELS
        ):
            report.add(
                "WARN",
                "scholarship_level_unmatched",
                filename,
                f'scholarshipStudyLevel "{study_level}" does not match any pipeline course level',
            )


def validate_deposit(content: str, filename: str, report: ValidationReport) -> None:
    data = parse_uni_json_payload(content, "deposit")
    if not isinstance(data, dict):
        report.add("ERROR", "json_parse_failed", filename, "Could not parse deposit JSON object")
        return
    if not str(data.get("initialDeposit", "") or "").strip() and not data.get("feesMetaData"):
        report.add(
            "WARN",
            "missing_deposit_fields",
            filename,
            "deposit JSON should include initialDeposit and/or feesMetaData",
        )


def validate_uni_clean(output_dir: Path, *, university_name: str = "") -> ValidationReport:
    university = university_name or output_dir.parent.name
    report = ValidationReport(university=university)
    uni_dir = output_dir / "clean" / "uni"

    validators = {
        "entry": validate_bangladesh_entry,
        "english": validate_english_requirements,
        "scholarship": validate_scholarships,
        "deposit": validate_deposit,
    }
    html_stems = {
        "entry": "bangladesh-entry",
        "english": "english-requirements",
        "scholarship": "scholarships",
        "deposit": "deposit",
    }

    for role, filename in UNI_MD_BY_ROLE.items():
        path = uni_dir / filename
        if not path.exists():
            report.add("ERROR", "missing_file", filename, f"Required file not found: {path}")
            continue
        content = load_uni_section(output_dir, filename)
        if not content.strip():
            report.add("ERROR", "empty_file", filename, "File is empty")
            continue
        validators[role](content, filename, report)

    return report


def format_report(report: ValidationReport) -> str:
    counts: dict[str, dict[str, int]] = {}
    for issue in report.issues:
        bucket = counts.setdefault(issue.file, {"ERROR": 0, "WARN": 0})
        bucket[issue.level] += 1

    lines = [f"=== Uni clean validation: {report.university} ==="]
    for filename in UNI_MD_BY_ROLE.values():
        bucket = counts.get(filename, {"ERROR": 0, "WARN": 0})
        lines.append(
            f"{filename:<24} {bucket['ERROR']} error(s), {bucket['WARN']} warning(s)"
        )
    lines.append("")
    for issue in report.issues:
        lines.append(issue.format_line())
    if report.error_count:
        lines.append("")
        lines.append(f"Validation failed ({report.error_count} error(s)). LLM extraction aborted.")
    else:
        lines.append("")
        lines.append("Validation passed.")
    return "\n".join(lines)


def ensure_uni_clean_valid(
    output_dir: Path,
    *,
    university_name: str = "",
    skip: bool = False,
) -> ValidationReport:
    report = validate_uni_clean(output_dir, university_name=university_name)
    if skip:
        return report
    print(format_report(report), flush=True)
    if report.error_count:
        raise SystemExit(1)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate output/clean/uni markdown before LLM extraction.")
    parser.add_argument("university_dir", nargs="?", default=".", help="University code/ folder")
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    args = parser.parse_args()

    code_dir = resolve_code_dir(Path(args.university_dir))
    output_dir = resolve_output_dir(code_dir)
    report = validate_uni_clean(output_dir)

    if args.json:
        payload = {
            "university": report.university,
            "error_count": report.error_count,
            "warning_count": report.warning_count,
            "issues": [
                {
                    "level": issue.level,
                    "code": issue.code,
                    "file": issue.file,
                    "message": issue.message,
                }
                for issue in report.issues
            ],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(format_report(report))

    return 1 if report.error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
