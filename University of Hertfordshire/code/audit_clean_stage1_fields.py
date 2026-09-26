#!/usr/bin/env python3
"""Report missing tuition fee, intake, and duration in cleaned course markdown."""

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

from uni_pages import split_frontmatter  # noqa: E402
from uni_paths import resolve_code_dir, resolve_output_dir  # noqa: E402

_START_DATES_RE = re.compile(
    r"^\s*(?:\*\*)?Start dates?(?:\*\*)?:\s*(.+?)\s*$",
    re.I | re.M,
)
_DURATION_RE = re.compile(
    r"^\s*(?:\*\*)?Duration(?:\*\*)?:\s*(.+?)\s*$",
    re.I | re.M,
)
_INTL_FEE_FACTS_RE = re.compile(
    r"International tuition fee:\s*(.+)",
    re.I,
)
_INTL_FULL_TIME_FEE_RE = re.compile(
    r"####\s+International Students\s*\n+#####\s+Full time\s*\n+\s*-\s*£([\d,]+)",
    re.I | re.M,
)
_ANY_INTL_FEE_RE = re.compile(
    r"####\s+International Students[\s\S]*?£([\d,]+)",
    re.I,
)


@dataclass
class CourseFieldAudit:
    rel_path: str
    course_url: str
    study_level: str
    intake: str = ""
    duration: str = ""
    tuition_fee: str = ""
    missing: list[str] = field(default_factory=list)


def extract_herts_stage1_fields(body: str) -> tuple[str, str, str]:
    intake = ""
    start = _START_DATES_RE.search(body)
    if start and start.group(1).strip():
        intake = start.group(1).strip()

    duration = ""
    dur = _DURATION_RE.search(body)
    if dur and dur.group(1).strip():
        duration = dur.group(1).strip()

    tuition = ""
    facts_fee = _INTL_FEE_FACTS_RE.search(body)
    if facts_fee:
        tuition = facts_fee.group(1).strip()
    else:
        ft = _INTL_FULL_TIME_FEE_RE.search(body)
        if ft:
            tuition = f"£{ft.group(1)}"
        else:
            any_fee = _ANY_INTL_FEE_RE.search(body)
            if any_fee:
                tuition = f"£{any_fee.group(1)}"

    return intake, duration, tuition


def audit_courses(courses_dir: Path) -> list[CourseFieldAudit]:
    rows: list[CourseFieldAudit] = []
    for md_path in sorted(courses_dir.rglob("*.md")):
        text = md_path.read_text(encoding="utf-8")
        meta, body = split_frontmatter(text)
        intake, duration, tuition = extract_herts_stage1_fields(body)
        missing: list[str] = []
        if not intake:
            missing.append("intake")
        if not duration:
            missing.append("duration")
        if not tuition:
            missing.append("tuitionFee")
        rows.append(
            CourseFieldAudit(
                rel_path=md_path.relative_to(courses_dir.parent.parent).as_posix(),
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
    by_field: dict[str, list[CourseFieldAudit]] = {
        "intake": [],
        "duration": [],
        "tuitionFee": [],
    }
    for row in rows:
        for key in row.missing:
            by_field[key].append(row)

    any_missing = [r for r in rows if r.missing]
    all_three = [r for r in rows if len(r.missing) == 3]

    print(f"Scanned {total} course markdown file(s)\n")
    for field_name, label in (
        ("intake", "Intake (Start dates)"),
        ("duration", "Course duration"),
        ("tuitionFee", "International tuition fee"),
    ):
        missing_rows = by_field[field_name]
        print(f"{label}: {len(missing_rows)} missing / {total} total")
        for row in missing_rows:
            url = row.course_url or row.rel_path
            print(f"  - [{row.study_level or '?'}] {url}")
        print()

    print(
        f"Missing any field: {len(any_missing)} | "
        f"Missing all three: {len(all_three)} | "
        f"Complete: {total - len(any_missing)}"
    )


def write_csv(rows: list[CourseFieldAudit], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "rel_path",
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
            "Count and list cleaned course markdown missing "
            "intake, duration, or international tuition fee."
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
        help="Optional path to write full audit CSV (default: output/clean_stage1_field_audit.csv)",
    )
    args = parser.parse_args()

    code_dir = resolve_code_dir(args.code_dir or _CODE_DIR)
    output_dir = resolve_output_dir(code_dir)
    courses_dir = output_dir / "clean" / "courses"
    if not courses_dir.is_dir():
        print(f"Error: not found: {courses_dir}", file=sys.stderr)
        return 1

    rows = audit_courses(courses_dir)
    print_report(rows)

    csv_path = args.csv or (output_dir / "clean_stage1_field_audit.csv")
    write_csv(rows, csv_path)
    print(f"\nWrote {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
