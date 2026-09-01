#!/usr/bin/env python3
"""Validate output/dev_courses_{UNIVERSITY_NAME}.csv after export (course-import rules + QA)."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from course_markdown_cleanup import parse_uni_json_payload
from export_dev_courses import DEV_COURSE_CSV_COLUMNS, load_env_config, write_dev_courses_csv
from programme_name_dictionary import (
    ProgrammeNameDictionary,
    infer_programme_names_with_llm,
    load_programme_name_dictionary,
)
from llm_extract import (
    DEGREE_ALIASES,
    infer_course_level,
    load_uni_section,
    read_course_index_csv,
    scholarship_study_level_matches,
)
from study_level import LEVEL_MATCH_ORDER, load_url_levels
from uni_paths import resolve_code_dir, resolve_output_dir

REQUIRED_NONEMPTY = (
    "uniName",
    "programmeName",
    "degreeName",
    "courseName",
    "minDegreeName",
    "minGpa",
    "intakeInfo",
)

OPTIONAL_NUMBERS = (
    "minGpa",
    "higherGpa",
    "tuitionFee",
    "initialDeposit",
    "applicationFee",
    "scholarshipAmount",
    "ieltsMinOverall",
    "ieltsMinSection",
    "toeflMinOverall",
    "toeflMinSection",
    "pteMinOverall",
    "pteMinSection",
)

JSON_COLUMNS = (
    "AcademicRequirementsMetaData",
    "feesMetaData",
    "scholarshipMetaData",
)

KNOWN_DEGREES = frozenset(DEGREE_ALIASES.values()) | {
    "HSC",
    "SSC",
    "HND",
    "MSci",
    "BArch",
    "MArch",
    "BMus",
    "AdvPgDip",
    "PGCert",
    "PgCert",
    "FdSc",
    "Fd",
    "FDA",
    "CertHE",
    "BM BS",
}

MONTH_ABBREV = {
    "jan": "jan",
    "january": "jan",
    "feb": "feb",
    "february": "feb",
    "mar": "mar",
    "march": "mar",
    "apr": "apr",
    "april": "apr",
    "may": "may",
    "jun": "jun",
    "june": "jun",
    "jul": "jul",
    "july": "jul",
    "aug": "aug",
    "august": "aug",
    "sep": "sep",
    "sept": "sep",
    "september": "sep",
    "oct": "oct",
    "october": "oct",
    "nov": "nov",
    "november": "nov",
    "dec": "dec",
    "december": "dec",
}

INTAKE_TOKEN_RE = re.compile(
    r"^(?P<month>[A-Za-z]{3,9})[-\s](?P<year>\d{2}|\d{4})$"
)

UG_LIKE = frozenset({"foundation", "undergraduate"})
PG_LIKE = frozenset({"postgraduate", "postgraduate_research"})


class CourseLevelResolver:
    def __init__(self, output_dir: Path) -> None:
        self._by_path_levels: dict[str, set[str]] = {}
        url_levels = load_url_levels(output_dir)
        for record in url_levels.records():
            key = DevCoursesValidator.url_path_key(record.get("course_url", ""))
            level = (record.get("study_level") or "").strip()
            if key and level:
                self._by_path_levels.setdefault(key, set()).add(level)

        self._index_levels: dict[str, str] = {}
        try:
            for row in read_course_index_csv(output_dir):
                key = DevCoursesValidator.url_path_key(row.get("courseUrlExternal", ""))
                level = (row.get("study_level") or "").strip()
                if key and level:
                    self._index_levels[key] = level
        except FileNotFoundError:
            pass

    def resolve(self, url: str, course_name: str) -> str:
        key = DevCoursesValidator.url_path_key(url)
        if key and key in self._by_path_levels:
            return DevCoursesValidator.pick_primary_level(list(self._by_path_levels[key]))
        if key and key in self._index_levels:
            return self._index_levels[key]
        return infer_course_level(course_name, url)


@dataclass
class DevCoursesValidationResult:
    csv_path: Path
    reviewed_path: Path
    row_count: int
    error_rows: int
    inferred_rows: int = 0
    llm_inferred_rows: int = 0
    empty_counts: dict[str, int] = field(default_factory=dict)
    file_error: str = ""

    @property
    def ok(self) -> bool:
        return not self.file_error and self.error_rows == 0


class DevCoursesValidator:
    """Validate dev_courses CSV exports against course-import rules and QA checks."""

    REQUIRED_NONEMPTY = REQUIRED_NONEMPTY
    OPTIONAL_NUMBERS = OPTIONAL_NUMBERS
    JSON_COLUMNS = JSON_COLUMNS
    KNOWN_DEGREES = KNOWN_DEGREES
    MONTH_ABBREV = MONTH_ABBREV
    INTAKE_TOKEN_RE = INTAKE_TOKEN_RE
    UG_LIKE = UG_LIKE
    PG_LIKE = PG_LIKE

    @staticmethod
    def url_path_key(url: str) -> str:
        return urlparse((url or "").strip()).path.rstrip("/").lower()

    @staticmethod
    def cell(row: dict[str, str], key: str) -> str:
        return (row.get(key) or "").strip()

    @staticmethod
    def format_import_error(code: str, message: str) -> str:
        return f"{code}: {message}"

    @classmethod
    def infer_programme_name(
        cls,
        row: dict[str, str],
        dictionary: ProgrammeNameDictionary,
    ) -> str:
        """Fill empty programmeName from the dictionary. Returns the comment, or ''."""
        if cls.cell(row, "programmeName") or not cls.cell(row, "courseName"):
            return ""
        programme = dictionary.lookup(cls.cell(row, "courseName"))
        if not programme:
            return ""
        row["programmeName"] = programme
        return cls.format_import_error(
            "COMMENT",
            f"programmeName inferred from dictionary ({programme})",
        )

    @classmethod
    def infer_programme_name_from_llm(
        cls,
        row: dict[str, str],
        picks: dict[str, str],
    ) -> str:
        """Fill empty programmeName from an LLM closed-list pick. Returns the comment, or ''."""
        if cls.cell(row, "programmeName"):
            return ""
        programme = picks.get(cls.cell(row, "courseName"), "")
        if not programme:
            return ""
        row["programmeName"] = programme
        return cls.format_import_error(
            "COMMENT",
            f"programmeName inferred from dictionary by LLM ({programme})",
        )

    @staticmethod
    def parse_optional_decimal(raw: str) -> bool:
        text = (raw or "").strip()
        if not text:
            return True
        cleaned = text.replace(",", "")
        try:
            return __import__("math").isfinite(float(cleaned))
        except ValueError:
            return False

    @classmethod
    def parse_intake_tokens(cls, raw: str) -> list[str]:
        parsed: list[str] = []
        for part in re.split(r"\s*,\s*", (raw or "").strip()):
            if not part:
                continue
            match = cls.INTAKE_TOKEN_RE.match(part)
            if not match:
                continue
            month = cls.MONTH_ABBREV.get(match.group("month").lower())
            if not month:
                continue
            year = match.group("year")
            if len(year) == 2:
                year = str(2000 + int(year))
            parsed.append(f"{month} {year}")
        return parsed

    @staticmethod
    def parse_metadata_items(raw: str) -> list[dict] | None:
        text = (raw or "").strip()
        if not text:
            return []
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, list):
            return None
        items: list[dict] = []
        for item in data:
            if not isinstance(item, dict):
                return None
            desc = item.get("description")
            if desc is None:
                desc = []
            if not isinstance(desc, list) or not all(isinstance(part, str) for part in desc):
                return None
            items.append(item)
        return items

    @staticmethod
    def metadata_has_block(items: list[dict], *needles: str) -> bool:
        for item in items:
            subtitle = str(item.get("subtitle") or "").strip().casefold()
            if not any(needle in subtitle for needle in needles):
                continue
            desc = item.get("description") or []
            if any(str(part).strip() for part in desc):
                return True
        return False

    @staticmethod
    def flatten_metadata_text(items: list[dict]) -> str:
        parts: list[str] = []
        for item in items:
            parts.append(str(item.get("subtitle") or ""))
            for line in item.get("description") or []:
                parts.append(str(line))
        return "\n".join(parts)

    @classmethod
    def known_degree(cls, name: str) -> bool:
        text = (name or "").strip()
        if not text:
            return True
        if text in cls.KNOWN_DEGREES:
            return True
        folded = text.casefold()
        if folded in DEGREE_ALIASES:
            return True
        for alias, canonical in DEGREE_ALIASES.items():
            if alias == folded or canonical.casefold() == folded:
                return True
        return False

    @staticmethod
    def pick_primary_level(levels: list[str]) -> str:
        found = {level.strip() for level in levels if level.strip()}
        for level in LEVEL_MATCH_ORDER:
            if level in found:
                return level
        if "other" in found:
            return "other"
        return next(iter(found), "")

    @staticmethod
    def load_scholarship_catalog(output_dir: Path) -> list[dict]:
        content = load_uni_section(output_dir, "scholarships.md")
        data = parse_uni_json_payload(content, "scholarships")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []

    @staticmethod
    def scholarship_declared_level(name: str, catalog: list[dict]) -> str:
        want = (name or "").strip().casefold()
        if not want:
            return ""
        for item in catalog:
            item_name = str(item.get("scholarshipName") or "").strip().casefold()
            if item_name == want:
                return str(item.get("scholarshipStudyLevel") or "").strip()
        return ""

    @staticmethod
    def scholarship_match_level(course_level: str) -> str:
        if course_level == "postgraduate_research":
            return "postgraduate"
        return course_level

    @classmethod
    def scholarship_level_mismatch(
        cls,
        *,
        course_level: str,
        scholarship_name: str,
        scholarship_meta: list[dict],
        catalog: list[dict],
    ) -> str:
        if not scholarship_name:
            return ""
        match_level = cls.scholarship_match_level(course_level)
        haystack = f"{scholarship_name}\n{cls.flatten_metadata_text(scholarship_meta)}".casefold()
        declared = cls.scholarship_declared_level(scholarship_name, catalog)
        if declared and not scholarship_study_level_matches(declared, match_level):
            if match_level in cls.UG_LIKE and "postgraduate" in declared.casefold():
                return (
                    "scholarship study level does not match course "
                    "(undergraduate/foundation got postgraduate scholarship)"
                )
            if match_level in cls.PG_LIKE or course_level in cls.PG_LIKE:
                if "undergraduate" in declared.casefold() and "postgraduate" not in declared.casefold():
                    return (
                        "scholarship study level does not match course "
                        "(postgraduate got undergraduate scholarship)"
                    )

        has_pg = bool(re.search(r"\bpostgraduate\b|\bmasters?\b", haystack))
        has_ug = bool(re.search(r"\bundergraduate\b", haystack))
        if match_level in cls.UG_LIKE and has_pg:
            return (
                "scholarship study level does not match course "
                "(undergraduate/foundation got postgraduate scholarship)"
            )
        if (match_level in cls.PG_LIKE or course_level in cls.PG_LIKE) and has_ug and not has_pg:
            return (
                "scholarship study level does not match course "
                "(postgraduate got undergraduate scholarship)"
            )
        return ""

    @classmethod
    def validate_row(
        cls,
        row: dict[str, str],
        *,
        level_resolver: CourseLevelResolver,
        scholarship_catalog: list[dict],
    ) -> list[str]:
        errors: list[str] = []
        missing = [key for key in cls.REQUIRED_NONEMPTY if not cls.cell(row, key)]
        if missing:
            errors.append(
                cls.format_import_error(
                    "MISSING_REQUIRED_FIELD",
                    f"missing required field(s): {', '.join(missing)}",
                )
            )

        higher_name = cls.cell(row, "higherDegreeName")
        higher_gpa = cls.cell(row, "higherGpa")
        if higher_gpa and not higher_name:
            errors.append(
                cls.format_import_error(
                    "MISSING_REQUIRED_FIELD",
                    "higherDegreeName is required when higherGpa is set",
                )
            )
        if higher_name and not higher_gpa:
            errors.append(
                cls.format_import_error(
                    "MISSING_REQUIRED_FIELD",
                    "higherGpa is required when higherDegreeName is set",
                )
            )

        for key in cls.OPTIONAL_NUMBERS:
            value = cls.cell(row, key)
            if not value:
                continue
            if key == "higherGpa" and higher_name and not cls.parse_optional_decimal(value):
                errors.append(
                    cls.format_import_error(
                        "INVALID_FORMAT",
                        "higherGpa must be a number when higherDegreeName is set",
                    )
                )
            elif key == "minGpa" and not cls.parse_optional_decimal(value):
                errors.append(cls.format_import_error("INVALID_FORMAT", "minGpa must be a number"))
            elif key != "minGpa" and key != "higherGpa" and not cls.parse_optional_decimal(value):
                errors.append(
                    cls.format_import_error("INVALID_FORMAT", f"{key} must be a number when set")
                )

        duration = cls.cell(row, "courseDuration")
        if duration and not re.search(r"\d", duration):
            errors.append(
                cls.format_import_error(
                    "INVALID_FORMAT",
                    "courseDuration must contain a number (months)",
                )
            )

        intake = cls.cell(row, "intakeInfo")
        if intake and not cls.parse_intake_tokens(intake):
            errors.append(
                cls.format_import_error(
                    "INVALID_FORMAT",
                    "intakeInfo must be parseable (e.g. Sep-26, Dec-26 or Sep 2026)",
                )
            )

        parsed_meta: dict[str, list[dict] | None] = {}
        for key in cls.JSON_COLUMNS:
            raw = cls.cell(row, key)
            if not raw:
                parsed_meta[key] = []
                continue
            items = cls.parse_metadata_items(raw)
            parsed_meta[key] = items
            if items is None:
                errors.append(
                    cls.format_import_error("INVALID_JSON", f"{key} must be MetaDataItem[]")
                )

        for key in ("degreeName", "minDegreeName", "higherDegreeName"):
            value = cls.cell(row, key)
            if value and not cls.known_degree(value):
                errors.append(
                    cls.format_import_error(
                        "UNKNOWN_DEGREE",
                        f'Unknown degree "{value}" for insert - add "{value}" to course-degree-level-order.ts',
                    )
                )

        academic = parsed_meta.get("AcademicRequirementsMetaData")
        if academic is not None:
            if not cls.metadata_has_block(academic, "entry"):
                errors.append(
                    cls.format_import_error(
                        "INVALID_JSON",
                        "AcademicRequirementsMetaData missing Entry Requirements block",
                    )
                )
            if not cls.metadata_has_block(academic, "english"):
                errors.append(
                    cls.format_import_error(
                        "INVALID_JSON",
                        "AcademicRequirementsMetaData missing English Requirement block",
                    )
                )

        scholarship_name = cls.cell(row, "scholarshipName")
        scholarship_meta = parsed_meta.get("scholarshipMetaData") or []
        if scholarship_name and scholarship_meta is not None:
            course_level = level_resolver.resolve(
                cls.cell(row, "courseUrlExternal"),
                cls.cell(row, "courseName"),
            )
            mismatch = cls.scholarship_level_mismatch(
                course_level=course_level,
                scholarship_name=scholarship_name,
                scholarship_meta=scholarship_meta,
                catalog=scholarship_catalog,
            )
            if mismatch:
                errors.append(cls.format_import_error("INVALID_FORMAT", mismatch))

        return errors

    @classmethod
    def empty_column_counts(cls, rows: list[dict[str, str]], headers: list[str]) -> dict[str, int]:
        counts = {col: 0 for col in headers}
        for row in rows:
            for col in headers:
                if not cls.cell(row, col):
                    counts[col] += 1
        return counts

    @staticmethod
    def write_reviewed_csv(
        reviewed_path: Path,
        headers: list[str],
        rows: list[dict[str, str]],
    ) -> None:
        """Write every row (passing and failing) with an errorReason column."""
        fieldnames = list(headers) + ["errorReason"]
        with reviewed_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({col: row.get(col, "") for col in fieldnames})

    @staticmethod
    def print_validation_report(result: DevCoursesValidationResult) -> None:
        print(f"Validated {result.csv_path} ({result.row_count} row(s))")
        print("Empty columns:")
        for col, count in result.empty_counts.items():
            print(f"  {col}: {count} / {result.row_count}")
        if result.inferred_rows:
            print(
                f"programmeName inferred from dictionary: "
                f"{result.inferred_rows} row(s)"
            )
        if result.llm_inferred_rows:
            print(
                f"programmeName inferred from dictionary by LLM: "
                f"{result.llm_inferred_rows} row(s)"
            )
        if result.file_error:
            print(result.file_error, file=sys.stderr)
            return
        if result.error_rows:
            print(f"VALIDATION FAILED: {result.error_rows} row(s)")
        else:
            print("VALIDATION OK: 0 row errors")
        print(f"Wrote reviewed CSV ({result.reviewed_path.name}): {result.reviewed_path}")

    def validate_dev_courses_csv(
        self,
        csv_path: Path,
        code_dir: Path,
        *,
        use_llm_programme: bool = True,
    ) -> DevCoursesValidationResult:
        code_dir = resolve_code_dir(code_dir)
        output_dir = resolve_output_dir(code_dir)
        university_name, _base = load_env_config(code_dir)
        reviewed_path = csv_path.parent / f"dev_courses_{university_name}_reviewed.csv"

        if not csv_path.is_file():
            result = DevCoursesValidationResult(
                csv_path=csv_path,
                reviewed_path=reviewed_path,
                row_count=0,
                error_rows=0,
                file_error=f"CSV not found: {csv_path}",
            )
            return result

        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = list(reader.fieldnames or [])
            rows = [{key: (value or "") for key, value in row.items()} for row in reader]

        missing_headers = [col for col in DEV_COURSE_CSV_COLUMNS if col not in headers]
        if missing_headers:
            return DevCoursesValidationResult(
                csv_path=csv_path,
                reviewed_path=reviewed_path,
                row_count=len(rows),
                error_rows=0,
                empty_counts={},
                file_error=(
                    "MISSING_REQUIRED_FIELD: Missing required CSV headers: "
                    f"{', '.join(missing_headers)}. Found: {', '.join(headers)}"
                ),
            )
        if not rows:
            return DevCoursesValidationResult(
                csv_path=csv_path,
                reviewed_path=reviewed_path,
                row_count=0,
                error_rows=0,
                empty_counts={col: 0 for col in DEV_COURSE_CSV_COLUMNS},
                file_error="MISSING_REQUIRED_FIELD: CSV contains no data rows.",
            )

        level_resolver = CourseLevelResolver(output_dir)
        scholarship_catalog = self.load_scholarship_catalog(output_dir)
        programme_dict = load_programme_name_dictionary()
        comments: list[str] = []
        inferred_rows = 0
        for row in rows:
            inferred = self.infer_programme_name(row, programme_dict)
            if inferred:
                inferred_rows += 1
            comments.append(inferred)

        llm_inferred_rows = 0
        if use_llm_programme:
            empties = [row for row in rows if not self.cell(row, "programmeName") and self.cell(row, "courseName")]
            if empties:
                print(
                    f"LLM programmeName lookup for {len(empties)} empty row(s) "
                    f"using {len(programme_dict.unique_programme_names())} closed names"
                )
                picks = infer_programme_names_with_llm(
                    [self.cell(row, "courseName") for row in empties],
                    programme_dict,
                )
                for index, row in enumerate(rows):
                    llm_comment = self.infer_programme_name_from_llm(row, picks)
                    if not llm_comment:
                        continue
                    llm_inferred_rows += 1
                    comments[index] = llm_comment

        reviewed_rows: list[dict[str, str]] = []
        for row, inferred in zip(rows, comments):
            issues = self.validate_row(
                row,
                level_resolver=level_resolver,
                scholarship_catalog=scholarship_catalog,
            )
            if inferred:
                issues.append(inferred)
            out = dict(row)
            out["errorReason"] = " | ".join(issues)
            reviewed_rows.append(out)

        if inferred_rows or llm_inferred_rows:
            write_dev_courses_csv(csv_path, rows)

        self.write_reviewed_csv(reviewed_path, list(DEV_COURSE_CSV_COLUMNS), reviewed_rows)
        real_errors = sum(
            1
            for row in reviewed_rows
            if row.get("errorReason")
            and any(
                not part.strip().startswith("COMMENT:")
                for part in row["errorReason"].split(" | ")
            )
        )
        return DevCoursesValidationResult(
            csv_path=csv_path,
            reviewed_path=reviewed_path,
            row_count=len(rows),
            error_rows=real_errors,
            inferred_rows=inferred_rows,
            llm_inferred_rows=llm_inferred_rows,
            empty_counts=self.empty_column_counts(rows, list(DEV_COURSE_CSV_COLUMNS)),
        )


class DevCoursesValidateCLI:
    """Command-line interface for dev courses CSV validation."""

    def __init__(self, validator: DevCoursesValidator | None = None) -> None:
        self.validator = validator or DevCoursesValidator()

    def build_parser(self, argv: list[str] | None = None) -> argparse.Namespace:
        parser = argparse.ArgumentParser(
            description="Validate dev_courses_{UNIVERSITY_NAME}.csv after export."
        )
        parser.add_argument(
            "code_dir",
            nargs="?",
            default=".",
            help="University code/ directory (default: cwd)",
        )
        parser.add_argument(
            "--skip-llm-programme",
            action="store_true",
            help="Do not ask Ollama to fill leftover empty programmeName values",
        )
        return parser.parse_args(argv)

    def main(self, argv: list[str] | None = None) -> int:
        args = self.build_parser(argv)
        try:
            code_dir = resolve_code_dir(Path(args.code_dir))
            university_name, _base = load_env_config(code_dir)
            output_dir = resolve_output_dir(code_dir)
            csv_path = output_dir / f"dev_courses_{university_name}.csv"
            result = self.validator.validate_dev_courses_csv(
                csv_path,
                code_dir,
                use_llm_programme=not args.skip_llm_programme,
            )
        except (FileNotFoundError, ValueError) as exc:
            print(exc, file=sys.stderr)
            return 1
        self.validator.print_validation_report(result)
        if result.file_error:
            return 1
        return 1 if result.error_rows else 0


_default_validator = DevCoursesValidator()
_default_cli = DevCoursesValidateCLI(_default_validator)

# Backward-compatible module-level aliases
url_path_key = DevCoursesValidator.url_path_key
cell = DevCoursesValidator.cell
format_import_error = DevCoursesValidator.format_import_error
infer_programme_name = DevCoursesValidator.infer_programme_name
infer_programme_name_from_llm = DevCoursesValidator.infer_programme_name_from_llm
parse_optional_decimal = DevCoursesValidator.parse_optional_decimal
parse_intake_tokens = DevCoursesValidator.parse_intake_tokens
parse_metadata_items = DevCoursesValidator.parse_metadata_items
metadata_has_block = DevCoursesValidator.metadata_has_block
flatten_metadata_text = DevCoursesValidator.flatten_metadata_text
known_degree = DevCoursesValidator.known_degree
pick_primary_level = DevCoursesValidator.pick_primary_level
load_scholarship_catalog = DevCoursesValidator.load_scholarship_catalog
scholarship_declared_level = DevCoursesValidator.scholarship_declared_level
scholarship_match_level = DevCoursesValidator.scholarship_match_level
scholarship_level_mismatch = DevCoursesValidator.scholarship_level_mismatch
validate_row = DevCoursesValidator.validate_row
empty_column_counts = DevCoursesValidator.empty_column_counts
write_reviewed_csv = DevCoursesValidator.write_reviewed_csv
print_validation_report = DevCoursesValidator.print_validation_report
validate_dev_courses_csv = _default_validator.validate_dev_courses_csv
parse_args = _default_cli.build_parser
main = _default_cli.main


if __name__ == "__main__":
    raise SystemExit(main())
