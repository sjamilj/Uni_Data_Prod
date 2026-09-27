#!/usr/bin/env python3
"""Count missing Stage-1 fields and entry content in output/clean/courses/**/*.md."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from llm_extract import Stage1MarkdownParser, extract_entry_lines_from_course_markdown  # noqa: E402
from scrape_course_urls import add_code_dir_argument, resolve_work_dir  # noqa: E402
from study_level import clean_courses_root, iter_course_markdown, relative_course_md  # noqa: E402
from uni_paths import resolve_output_dir  # noqa: E402

FIELD_KEYS = (
    "entry",
    "intakeInfo",
    "courseDuration",
    "tuitionFee",
    "ielts",
)

IELTS_LOOSE_RE = re.compile(r"IELTS\s+[\d.]+", re.I)


@dataclass
class CourseAuditRow:
    rel_path: str
    course_url: str
    study_level: str
    missing: list[str] = field(default_factory=list)
    intakeInfo: str = ""
    courseDuration: str = ""
    tuitionFee: str = ""
    ieltsMinOverall: str = ""
    entry_section_chars: int = 0
    entry_parsed_lines: int = 0


def read_md_body(path: Path) -> tuple[str, str, str]:
    """Return (body_after_frontmatter, course_url, study_level)."""
    text = path.read_text(encoding="utf-8")
    course_url = ""
    study_level = ""
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            header = text[3:end]
            body = text[end + 4 :].lstrip("\n")
            for line in header.splitlines():
                if line.startswith("course_url:"):
                    course_url = line.split(":", 1)[1].strip()
                elif line.startswith("study_level:"):
                    study_level = line.split(":", 1)[1].strip()
    return body, course_url, study_level


def entry_requirements_section(body: str) -> str:
    section_match = re.search(r"^##\s+Entry requirements\s*$", body, re.I | re.M)
    if not section_match:
        return ""
    rest = body[section_match.end() :]
    next_heading = re.search(r"^##\s+", rest, re.M)
    return rest[: next_heading.start()] if next_heading else rest


def has_entry_content(body: str, *, min_chars: int) -> bool:
    section = entry_requirements_section(body)
    if len(section.strip()) >= min_chars:
        return True
    if extract_entry_lines_from_course_markdown(body):
        return True
    return False


def audit_markdown(body: str, *, entry_min_chars: int, ielts_loose: bool) -> tuple[list[str], dict[str, str]]:
    hints = Stage1MarkdownParser.extract_stage1_fields_from_md(body)
    missing: list[str] = []

    if not has_entry_content(body, min_chars=entry_min_chars):
        missing.append("entry")

    if not (hints.get("intakeInfo") or "").strip():
        missing.append("intakeInfo")

    if not (hints.get("courseDuration") or "").strip():
        missing.append("courseDuration")

    if not (hints.get("tuitionFee") or "").strip():
        missing.append("tuitionFee")

    ielts_ok = bool((hints.get("ieltsMinOverall") or "").strip())
    if not ielts_ok and ielts_loose and IELTS_LOOSE_RE.search(body):
        ielts_ok = True
    if not ielts_ok:
        missing.append("ielts")

    return missing, hints


class CleanCourseMarkdownAuditor:
    """Audit clean course markdown for parser-owned Stage 1 fields."""

    def __init__(self, code_dir: Path) -> None:
        self.code_dir = resolve_work_dir(code_dir)
        self.output_dir = resolve_output_dir(self.code_dir)
        self.courses_dir = clean_courses_root(self.output_dir, presetup=False)

    def run(
        self,
        *,
        entry_min_chars: int = 80,
        ielts_loose: bool = True,
        list_missing: str | None = None,
        csv_path: Path | None = None,
    ) -> list[CourseAuditRow]:
        paths = iter_course_markdown(self.courses_dir)
        rows: list[CourseAuditRow] = []
        for path in paths:
            body, course_url, study_level = read_md_body(path)
            missing, hints = audit_markdown(
                body,
                entry_min_chars=entry_min_chars,
                ielts_loose=ielts_loose,
            )
            section = entry_requirements_section(body)
            rows.append(
                CourseAuditRow(
                    rel_path=relative_course_md(path, self.courses_dir),
                    course_url=course_url,
                    study_level=study_level,
                    missing=missing,
                    intakeInfo=hints.get("intakeInfo", ""),
                    courseDuration=hints.get("courseDuration", ""),
                    tuitionFee=hints.get("tuitionFee", ""),
                    ieltsMinOverall=hints.get("ieltsMinOverall", ""),
                    entry_section_chars=len(section.strip()),
                    entry_parsed_lines=len(extract_entry_lines_from_course_markdown(body)),
                )
            )

        if csv_path:
            self._write_csv(rows, csv_path)
        if list_missing:
            self._print_missing_list(rows, list_missing)
        self._print_summary(rows, entry_min_chars=entry_min_chars, ielts_loose=ielts_loose)
        return rows

    @staticmethod
    def _write_csv(rows: list[CourseAuditRow], csv_path: Path) -> None:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "rel_path",
                    "course_url",
                    "study_level",
                    "missing",
                    "intakeInfo",
                    "courseDuration",
                    "tuitionFee",
                    "ieltsMinOverall",
                    "entry_section_chars",
                    "entry_parsed_lines",
                ],
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        "rel_path": row.rel_path,
                        "course_url": row.course_url,
                        "study_level": row.study_level,
                        "missing": ";".join(row.missing),
                        "intakeInfo": row.intakeInfo,
                        "courseDuration": row.courseDuration,
                        "tuitionFee": row.tuitionFee,
                        "ieltsMinOverall": row.ieltsMinOverall,
                        "entry_section_chars": row.entry_section_chars,
                        "entry_parsed_lines": row.entry_parsed_lines,
                    }
                )
        print(f"Wrote {csv_path}")

    @staticmethod
    def _print_missing_list(rows: list[CourseAuditRow], field: str) -> None:
        key = field.strip()
        if key not in FIELD_KEYS:
            print(f"Unknown field for --list-missing: {key} (choose: {', '.join(FIELD_KEYS)})", file=sys.stderr)
            return
        print(f"\n=== Missing: {key} ===")
        for row in rows:
            if key in row.missing:
                print(f"  {row.rel_path}")
                if row.course_url:
                    print(f"    {row.course_url}")

    @staticmethod
    def _print_summary(
        rows: list[CourseAuditRow],
        *,
        entry_min_chars: int,
        ielts_loose: bool,
    ) -> None:
        total = len(rows)
        if total == 0:
            print("No course markdown found under output/clean/courses — run download/clean first.")
            return

        missing_counts: dict[str, int] = {key: 0 for key in FIELD_KEYS}
        by_level: dict[str, dict[str, int]] = defaultdict(lambda: {key: 0 for key in FIELD_KEYS})
        complete = 0
        for row in rows:
            if not row.missing:
                complete += 1
            level = row.study_level or "unknown"
            for key in row.missing:
                missing_counts[key] += 1
                by_level[level][key] += 1

        print(f"Audited {total} course markdown file(s)")
        print(f"Entry rule: ## Entry requirements section >= {entry_min_chars} chars, or parsed entry table lines")
        print(f"IELTS rule: Stage 1 parser match" + ("; loose 'IELTS n.n' counts as present" if ielts_loose else ""))
        print()
        print("Missing counts (files lacking each field):")
        for key in FIELD_KEYS:
            have = total - missing_counts[key]
            print(f"  {key:16} missing {missing_counts[key]:4} / {total}  (have {have})")
        print(f"\nAll five present: {complete} / {total}")

        if by_level:
            print("\nBy study_level (missing counts):")
            for level in sorted(by_level.keys()):
                counts = by_level[level]
                level_total = sum(1 for r in rows if (r.study_level or "unknown") == level)
                parts = ", ".join(f"{k}={counts[k]}" for k in FIELD_KEYS if counts[k])
                print(f"  {level} ({level_total} files): {parts or 'none missing'}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit clean/courses markdown for entry, intake, duration, fee, and IELTS.",
    )
    add_code_dir_argument(parser)
    parser.add_argument(
        "--entry-min-chars",
        type=int,
        default=80,
        help="Min characters in ## Entry requirements section (default: 80)",
    )
    parser.add_argument(
        "--strict-ielts",
        action="store_true",
        help="Only count IELTS if Stage 1 parser extracts ieltsMinOverall (not loose mention)",
    )
    parser.add_argument(
        "--list-missing",
        metavar="FIELD",
        choices=FIELD_KEYS,
        help="Print paths missing a single field (entry, intakeInfo, courseDuration, tuitionFee, ielts)",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        metavar="PATH",
        help="Write per-course audit CSV (default: output/clean_course_audit.csv under university)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    code_dir = resolve_work_dir(args.code_dir)
    output_dir = resolve_output_dir(code_dir)
    csv_path = args.csv or (output_dir / "clean_course_audit.csv")
    CleanCourseMarkdownAuditor(code_dir).run(
        entry_min_chars=args.entry_min_chars,
        ielts_loose=not args.strict_ielts,
        list_missing=args.list_missing,
        csv_path=csv_path,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
