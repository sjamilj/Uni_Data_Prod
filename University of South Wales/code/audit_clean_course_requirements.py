#!/usr/bin/env python3
"""Audit USW clean course markdown for typical entry and English requirement coverage.

Reads foundation, undergraduate, and postgraduate folders under output/clean/courses/
and writes a CSV flagging files missing expected fields.

UG / foundation — missing entry only if none of: ## UCAS points, - A Level:, or Typical qualification body.
Postgraduate — missing entry only if no Typical qualification body (unchanged).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

UCAS_HEADING_RE = re.compile(r"^##\s+UCAS points:\s*(.+)$", re.M | re.I)
A_LEVEL_LINE_RE = re.compile(r"^- A Level:\s*(.+)$", re.M | re.I)
ENGLISH_INTL_RE = re.compile(
    r"International applicants will need to have achieved an IELTS",
    re.I,
)
FRONTMATTER_COURSE_URL_RE = re.compile(
    r"^course_url:\s*(.+)$",
    re.M,
)
IELTS_PAIR_PATTERNS = (
    re.compile(
        r"IELTS\s+([\d.]+)\s+overall with no less than\s+([\d.]+)\s+in each band",
        re.I,
    ),
    re.compile(
        r"achieved an IELTS\s+([\d.]+)\s+overall with no less than\s+([\d.]+)\s+in each band",
        re.I,
    ),
    re.compile(
        r"overall of IELTS\s+([\d.]+)\s+with a minimum of\s+([\d.]+)\s+in each component",
        re.I,
    ),
)
PG_DEGREE_22_RE = re.compile(r"2\s*:\s*2|2\.2", re.I)
PG_DEGREE_21_RE = re.compile(r"2\s*:\s*1|2\.1", re.I)


def _code_dir() -> Path:
    return Path(__file__).resolve().parent


def _default_courses_dir(code_dir: Path) -> Path:
    return code_dir.parent / "output" / "clean" / "courses"


def _default_output_csv(code_dir: Path) -> Path:
    return code_dir.parent / "output" / "clean_course_requirements_audit.csv"


def _default_value_counts_json(code_dir: Path) -> Path:
    return code_dir.parent / "output" / "clean_a_level_value_counts.json"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _course_url(text: str) -> str:
    match = FRONTMATTER_COURSE_URL_RE.search(text)
    return match.group(1).strip() if match else ""


def _typical_qualification_body(text: str) -> str:
    for heading in (
        r"Typical qualification requirements:",
        r"Typical requirements:",
    ):
        match = re.search(
            rf"^###\s+{re.escape(heading)}\s*\n(.*?)(?=^#{{1,3}}\s|\Z)",
            text,
            re.M | re.S | re.I,
        )
        if match and match.group(1).strip():
            return match.group(1).strip()
    return ""


def _english_under_entry_requirements(text: str) -> str:
    match = re.search(
        r"^##\s+Entry requirements\s*\n(.*?)(?=^##\s+International fees|\Z)",
        text,
        re.M | re.S | re.I,
    )
    if not match:
        return ""
    block = match.group(1)
    sub = re.search(
        r"^###\s+English language requirements\s*\n(.*?)(?=^#{1,3}\s|\Z)",
        block,
        re.M | re.S | re.I,
    )
    if sub:
        return sub.group(1).strip()
    for line in block.splitlines():
        if ENGLISH_INTL_RE.search(line):
            return line.strip()
    return ""


def _has_typical_qualification_pg(text: str) -> tuple[bool, str]:
    if "## Typical entry" not in text:
        return False, ""
    _, _, typical = text.partition("## Typical entry")
    if "## Entry requirements" in typical:
        typical, _, _ = typical.partition("## Entry requirements")
    body = _typical_qualification_body(typical)
    snippet = " ".join(body.split())[:200] if body else ""
    if not body:
        return False, ""
    non_empty = [ln.strip() for ln in body.splitlines() if ln.strip()]
    return bool(non_empty), snippet


def audit_markdown(text: str, study_level: str) -> dict[str, str]:
    ucas_match = UCAS_HEADING_RE.search(text)
    a_level_match = A_LEVEL_LINE_RE.search(text)
    english_body = _english_under_entry_requirements(text)
    has_english = bool(english_body and ENGLISH_INTL_RE.search(english_body))

    ucas_value = ucas_match.group(1).strip() if ucas_match else ""
    a_level_value = a_level_match.group(1).strip() if a_level_match else ""
    english_snippet = " ".join(english_body.split())[:200] if english_body else ""

    level = study_level.lower()
    is_pg = level == "postgraduate"
    is_ug_or_foundation = level in ("undergraduate", "foundation")

    has_typical, typical_snippet = _has_typical_qualification_pg(text)

    if is_ug_or_foundation:
        has_ucas = bool(ucas_match)
        has_a_level = bool(a_level_match)
        has_entry_signal = has_ucas or has_a_level or has_typical
        missing_entry = not has_entry_signal
        entry_issues: list[str] = []
        if not has_ucas:
            entry_issues.append("ucas_points")
        if not has_a_level:
            entry_issues.append("a_level")
        if not has_typical:
            entry_issues.append("typical_qualification")
    elif is_pg:
        has_ucas = False
        has_a_level = False
        missing_entry = not has_typical
        entry_issues = [] if has_typical else ["typical_qualification"]
    else:
        has_ucas = bool(ucas_match)
        has_a_level = bool(a_level_match)
        missing_entry = True
        entry_issues = ["unknown_study_level"]

    missing_english = not has_english

    return {
        "has_ucas_points": "Y" if has_ucas else ("N/A" if is_pg else "N"),
        "has_a_level": "Y" if has_a_level else ("N/A" if is_pg else "N"),
        "has_typical_qualification": "Y" if has_typical else "N",
        "has_english_requirements": "Y" if has_english else "N",
        "missing_entry_requirements": "Y" if missing_entry else "N",
        "missing_english_requirements": "Y" if missing_english else "N",
        "ucas_points_value": ucas_value,
        "a_level_value": a_level_value,
        "typical_qualification_snippet": typical_snippet,
        "english_requirements_snippet": english_snippet,
        "entry_issues": ";".join(entry_issues),
    }


def iter_course_markdown(courses_dir: Path) -> list[tuple[str, Path]]:
    rows: list[tuple[str, Path]] = []
    for level in ("foundation", "undergraduate", "postgraduate"):
        folder = courses_dir / level
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.md")):
            rows.append((level, path))
    return rows


def _ielts_overall_and_minimum(text: str) -> tuple[str, str]:
    for pattern in IELTS_PAIR_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).strip(), match.group(2).strip()
    return "", ""


def _ielts_group_key(overall: str, minimum: str) -> str:
    if overall and minimum:
        return f"{overall}/{minimum}"
    return overall or ""


def _ielts_counter_to_section(counter: Counter[str]) -> dict[str, object]:
    entries: list[dict[str, int | str]] = []
    by_value: dict[str, int] = {}
    for key, count in counter.most_common():
        by_value[key] = count
        overall, _, minimum = key.partition("/")
        entries.append(
            {
                "overall": overall,
                "minimum": minimum,
                "value": key,
                "count": count,
            }
        )
    return {"by_value": by_value, "entries": entries}


def _postgraduate_degree_labels(text: str) -> list[str]:
    labels: list[str] = []
    if PG_DEGREE_22_RE.search(text):
        labels.append("2:2")
    if PG_DEGREE_21_RE.search(text):
        labels.append("2:1")
    return labels


def _counter_to_section(counter: Counter[str]) -> dict[str, object]:
    entries = [{"value": value, "count": count} for value, count in counter.most_common()]
    return {
        "by_value": {rec["value"]: rec["count"] for rec in entries},
        "entries": entries,
    }


def _build_missing_course_views(
    pending_rows: list[dict[str, str]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """One row per course_url with entry / english / ielts flags; common = 2+ gaps."""
    by_url: dict[str, dict[str, object]] = {}
    for row in pending_rows:
        url = (row.get("course_url") or "").strip().rstrip("/")
        if not url:
            continue
        missing_entry = row["missing_entry_requirements"] == "Y"
        missing_english = row["missing_english_requirements"] == "Y"
        missing_ielts = not row.get("ielts_group")
        if not (missing_entry or missing_english or missing_ielts):
            continue
        gap_count = sum((missing_entry, missing_english, missing_ielts))
        by_url[url] = {
            "course_url": row["course_url"],
            "md_file": row["md_file"],
            "study_level": row["study_level"],
            "missing_entry": missing_entry,
            "missing_english": missing_english,
            "missing_ielts": missing_ielts,
            "gap_count": gap_count,
            "entry_issues": row.get("entry_issues", ""),
        }
    courses = sorted(
        by_url.values(),
        key=lambda item: (-int(item["gap_count"]), str(item["course_url"])),
    )
    common = [item for item in courses if int(item["gap_count"]) >= 2]
    return courses, common


def run_audit(
    courses_dir: Path,
    output_csv: Path,
    value_counts_json: Path,
) -> int:
    if not courses_dir.is_dir():
        print(f"courses dir not found: {courses_dir}", file=sys.stderr)
        return 1

    fieldnames = [
        "study_level",
        "md_file",
        "course_url",
        "has_ucas_points",
        "has_a_level",
        "has_typical_qualification",
        "has_english_requirements",
        "missing_entry_requirements",
        "missing_english_requirements",
        "entry_issues",
        "ucas_points_value",
        "a_level_value",
        "a_level_count",
        "ielts_group",
        "typical_qualification_snippet",
        "english_requirements_snippet",
    ]

    items = iter_course_markdown(courses_dir)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    missing_entry_count = 0
    missing_english_count = 0
    a_level_counter: Counter[str] = Counter()
    ielts_counter: Counter[str] = Counter()
    pg_degree_counter: Counter[str] = Counter()
    pending_rows: list[dict[str, str]] = []

    for study_level, path in items:
        text = _read_text(path)
        audit = audit_markdown(text, study_level)
        a_level_value = audit["a_level_value"]
        if a_level_value:
            a_level_counter[a_level_value] += 1
        ielts_overall, ielts_min = _ielts_overall_and_minimum(text)
        ielts_group = _ielts_group_key(ielts_overall, ielts_min)
        if ielts_group:
            ielts_counter[ielts_group] += 1
        if study_level.lower() == "postgraduate":
            for label in _postgraduate_degree_labels(text):
                pg_degree_counter[label] += 1
        rel = path.relative_to(courses_dir.parent.parent).as_posix()
        pending_rows.append(
            {
                "study_level": study_level,
                "md_file": rel,
                "course_url": _course_url(text),
                "ielts_group": ielts_group,
                **audit,
            }
        )

    def _course_ref(row: dict[str, str]) -> dict[str, str]:
        return {
            "course_url": row["course_url"],
            "md_file": row["md_file"],
            "study_level": row["study_level"],
        }

    missing_entry_courses: list[dict[str, str]] = []
    missing_english_courses: list[dict[str, str]] = []
    missing_ielts_courses: list[dict[str, str]] = []
    missing_by_issue: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in pending_rows:
        ref = _course_ref(row)
        if row["missing_entry_requirements"] == "Y":
            missing_entry_courses.append(
                {**ref, "entry_issues": row["entry_issues"]}
            )
        if row["missing_english_requirements"] == "Y":
            missing_english_courses.append(ref)
            missing_by_issue["english_requirements"].append(ref)
        if not row.get("ielts_group"):
            missing_ielts_courses.append(ref)
            missing_by_issue["ielts_overall_minimum"].append(ref)
        for issue in row["entry_issues"].split(";"):
            issue = issue.strip()
            if issue:
                missing_by_issue[issue].append(ref)

    missing_courses, missing_common = _build_missing_course_views(pending_rows)

    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in pending_rows:
            value = row["a_level_value"]
            row["a_level_count"] = str(a_level_counter[value]) if value else ""
            writer.writerow(row)
            if row["missing_entry_requirements"] == "Y":
                missing_entry_count += 1
            if row["missing_english_requirements"] == "Y":
                missing_english_count += 1

    value_counts_json.parent.mkdir(parents=True, exist_ok=True)
    with value_counts_json.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "a_level": _counter_to_section(a_level_counter),
                "ielts": _ielts_counter_to_section(ielts_counter),
                "postgraduate_degree": _counter_to_section(pg_degree_counter),
                "missing": {
                    "summary": {
                        "entry_requirements": len(missing_entry_courses),
                        "english_requirements": len(missing_english_courses),
                        "ielts_overall_minimum": len(missing_ielts_courses),
                        "unique_courses_with_any_gap": len(missing_courses),
                        "common_courses_multiple_gaps": len(missing_common),
                    },
                    "common": missing_common,
                    "courses": missing_courses,
                    "entry_requirements": missing_entry_courses,
                    "english_requirements": missing_english_courses,
                    "ielts_overall_minimum": missing_ielts_courses,
                    "by_issue": dict(sorted(missing_by_issue.items())),
                },
            },
            handle,
            indent=2,
            ensure_ascii=False,
        )

    print(f"Audited {len(items)} course markdown files under {courses_dir}")
    print(f"Wrote {output_csv}")
    print(
        f"Wrote {value_counts_json} "
        f"(a_level={len(a_level_counter)}, ielts={len(ielts_counter)}, "
        f"postgraduate_degree={len(pg_degree_counter)})"
    )
    print(f"  missing_entry_requirements: {missing_entry_count}")
    print(f"  missing_english_requirements: {missing_english_count}")
    print(f"  missing_ielts_overall_minimum: {len(missing_ielts_courses)}")
    print(f"  unique missing courses: {len(missing_courses)}")
    print(f"  common (2+ gaps): {len(missing_common)}")
    print(f"  (see missing.common / missing.courses in JSON)")
    return 0


def main(argv: list[str] | None = None) -> int:
    code_dir = _code_dir()
    parser = argparse.ArgumentParser(
        description="Audit USW clean course markdown for entry and English requirements.",
    )
    parser.add_argument(
        "--courses-dir",
        type=Path,
        default=_default_courses_dir(code_dir),
        help="Path to output/clean/courses (default: ../output/clean/courses)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_default_output_csv(code_dir),
        help="CSV output path (default: ../output/clean_course_requirements_audit.csv)",
    )
    parser.add_argument(
        "--value-counts-json",
        type=Path,
        default=_default_value_counts_json(code_dir),
        help=(
            "JSON value counts plus missing course URL lists "
            "(default: ../output/clean_a_level_value_counts.json)"
        ),
    )
    args = parser.parse_args(argv)
    return run_audit(
        args.courses_dir.resolve(),
        args.output.resolve(),
        args.value_counts_json.resolve(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
