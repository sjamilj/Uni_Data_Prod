#!/usr/bin/env python3
"""List LSBU clean course markdown missing duration, intake, tuition, or entry requirements."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
_REPO = _CODE_DIR.parents[1]
_SHARED = _REPO / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from llm_extract import (  # noqa: E402
    Stage1MarkdownParser,
    extract_entry_lines_from_course_markdown,
)
from uni_pages import split_frontmatter  # noqa: E402
from uni_paths import resolve_code_dir, resolve_output_dir  # noqa: E402

FIELD_LABELS = {
    "intakeInfo": "Intake (start date)",
    "courseDuration": "Course duration",
    "tuitionFee": "International tuition fee",
    "entry": "Entry requirements",
}

# LSBU Fees blocks sometimes omit the pipe before £
_LSBU_ANNUAL_FEE_RE = re.compile(
    r"(?:Annual tuition fees|First year tuition fee)\s*:\s*(?:\|\s*)?£([\d,]+)",
    re.I,
)


@dataclass
class CourseFieldAudit:
    rel_path: str
    slug: str
    course_url: str
    study_level: str
    intake: str = ""
    duration: str = ""
    tuition_fee: str = ""
    missing: list[str] = field(default_factory=list)


def entry_requirements_section(body: str) -> str:
    section_match = re.search(r"^##\s+Entry requirements\s*$", body, re.I | re.M)
    if not section_match:
        return ""
    rest = body[section_match.end() :]
    next_heading = re.search(r"^##\s+", rest, re.M)
    return rest[: next_heading.start()] if next_heading else rest


def has_entry_content(body: str, *, min_chars: int = 40) -> bool:
    section = entry_requirements_section(body)
    if len(section.strip()) >= min_chars:
        return True
    return bool(extract_entry_lines_from_course_markdown(body))


def extract_lsbu_fields(body: str) -> dict[str, str]:
    hints = Stage1MarkdownParser.extract_stage1_fields_from_md(body)
    if not (hints.get("tuitionFee") or "").strip():
        fee = _LSBU_ANNUAL_FEE_RE.search(body)
        if fee:
            hints["tuitionFee"] = fee.group(1).replace(",", "")
            hints.setdefault("currency", "GBP")
    return hints


def audit_courses(courses_dir: Path, *, entry_min_chars: int) -> list[CourseFieldAudit]:
    rows: list[CourseFieldAudit] = []
    for md_path in sorted(courses_dir.rglob("*.md")):
        text = md_path.read_text(encoding="utf-8")
        meta, body = split_frontmatter(text)
        hints = extract_lsbu_fields(body)
        intake = (hints.get("intakeInfo") or "").strip()
        duration = (hints.get("courseDuration") or "").strip()
        tuition = (hints.get("tuitionFee") or "").strip()

        missing: list[str] = []
        if not intake:
            missing.append("intakeInfo")
        if not duration:
            missing.append("courseDuration")
        if not tuition:
            missing.append("tuitionFee")
        if not has_entry_content(body, min_chars=entry_min_chars):
            missing.append("entry")

        rel = md_path.relative_to(courses_dir).as_posix()
        rows.append(
            CourseFieldAudit(
                rel_path=f"clean/courses/{rel}",
                slug=md_path.stem,
                course_url=str(meta.get("course_url") or "").strip(),
                study_level=str(meta.get("study_level") or "").strip(),
                intake=intake,
                duration=duration,
                tuition_fee=tuition,
                missing=missing,
            )
        )
    return rows


def print_report(rows: list[CourseFieldAudit]) -> None:
    total = len(rows)
    by_field: dict[str, list[CourseFieldAudit]] = {key: [] for key in FIELD_LABELS}
    for row in rows:
        for key in row.missing:
            by_field[key].append(row)

    any_missing = [r for r in rows if r.missing]
    complete = total - len(any_missing)

    print(f"Scanned {total} course markdown file(s) under output/clean/courses/\n")
    for field_key, label in FIELD_LABELS.items():
        missing_rows = by_field[field_key]
        print(f"{label}: {total - len(missing_rows)} / {total}  ({len(missing_rows)} missing)")
        for row in missing_rows:
            url = row.course_url or row.slug
            print(f"  - [{row.study_level or '?'}] {url}")
        print()

    print(f"Complete (all four fields): {complete} / {total}")
    print(f"Missing at least one field: {len(any_missing)} / {total}\n")

    if any_missing:
        print("Missing course list (any field):")
        for row in any_missing:
            fields = ", ".join(row.missing)
            url = row.course_url or row.rel_path
            print(f"  {row.slug}  [{fields}]  {url}")


def write_csv(rows: list[CourseFieldAudit], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "rel_path",
                "slug",
                "course_url",
                "study_level",
                "intake",
                "duration",
                "tuition_fee",
                "missing_fields",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "rel_path": row.rel_path,
                    "slug": row.slug,
                    "course_url": row.course_url,
                    "study_level": row.study_level,
                    "intake": row.intake,
                    "duration": row.duration,
                    "tuition_fee": row.tuition_fee,
                    "missing_fields": ",".join(row.missing),
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit output/clean/courses/**/*.md for intake, duration, "
            "international tuition fee, and entry requirements."
        ),
    )
    parser.add_argument(
        "--code-dir",
        type=Path,
        default=None,
        help="University code directory (default: this script's folder)",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Write audit CSV (default: output/clean_course_field_audit.csv)",
    )
    parser.add_argument(
        "--entry-min-chars",
        type=int,
        default=40,
        help="Minimum characters in ## Entry requirements section (default: 40)",
    )
    parser.add_argument(
        "--missing-only-csv",
        type=Path,
        default=None,
        help="Optional CSV with only rows that have missing_fields",
    )
    args = parser.parse_args()

    code_dir = resolve_code_dir(args.code_dir or _CODE_DIR)
    output_dir = resolve_output_dir(code_dir)
    courses_dir = output_dir / "clean" / "courses"
    if not courses_dir.is_dir():
        print(f"Error: not found: {courses_dir}", file=sys.stderr)
        return 1

    rows = audit_courses(courses_dir, entry_min_chars=args.entry_min_chars)
    print_report(rows)

    csv_path = args.csv or (output_dir / "clean_course_field_audit.csv")
    write_csv(rows, csv_path)
    print(f"\nWrote {csv_path}")

    if args.missing_only_csv:
        missing_rows = [r for r in rows if r.missing]
        write_csv(missing_rows, args.missing_only_csv)
        print(f"Wrote {args.missing_only_csv} ({len(missing_rows)} row(s))")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
