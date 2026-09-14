#!/usr/bin/env python3
"""Dry-run: match Essex clean courses against english-course-groups.md."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
_UNI_DIR = _CODE_DIR.parent
_REPO = _CODE_DIR.parents[1]

_SHARED = _REPO / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from llm_extract import ExtractionPathConfig, Stage2Enricher, resolve_english_course_group  # noqa: E402
from course_markdown_cleanup import parse_uni_json_payload  # noqa: E402
from uni_pages import split_frontmatter  # noqa: E402


def course_level_from_meta(meta: dict, parent_name: str) -> str:
    study_level = (meta.get("study_level") or parent_name or "").strip().lower()
    if "research" in study_level:
        return "postgraduate_research"
    if study_level == "postgraduate":
        return "postgraduate"
    return study_level


def diagnose_unresolved(
    groups: list[dict],
    *,
    course_name: str,
    course_body: str,
    course_level: str,
) -> str:
    labels = Stage2Enricher.english_course_labels(course_name, course_body)
    normalized = [
        Stage2Enricher.normalize_english_lookup_name(label)
        for label in labels
        if Stage2Enricher.normalize_english_lookup_name(label)
    ]
    partial: list[dict] = []
    for row in groups:
        row_level = str(row.get("studyLevel", "") or "").strip()
        if row_level and row_level not in {"postgraduate", "postgraduate_research"}:
            continue
        row_name = Stage2Enricher.normalize_english_lookup_name(str(row.get("courseName", "") or ""))
        if not row_name:
            continue
        for label in normalized:
            if label == row_name or row_name in label or label in row_name:
                partial.append(row)
                break
    if not partial:
        return "no match in mapping"
    groups_found = {str(row.get("englishGroup", "") or "").strip() for row in partial}
    groups_found.discard("")
    if len(groups_found) > 1:
        return f"ambiguous ({len(partial)} rows, groups: {', '.join(sorted(groups_found))})"
    return "partial match but unresolved"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--uni-dir",
        type=Path,
        default=_UNI_DIR,
        help="University folder (default: University of Essex)",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Optional path to write full dry-run report JSON",
    )
    args = parser.parse_args()

    output_dir = args.uni_dir / "output"
    courses_dir = output_dir / "clean" / "courses"
    groups = ExtractionPathConfig.load_english_course_groups(output_dir)
    english_programs = parse_uni_json_payload(
        ExtractionPathConfig.load_uni_section(output_dir, "english-requirements.md"),
        "english-requirements",
    ) or []

    by_level: dict[str, int] = {}
    resolved: list[dict] = []
    missing: list[dict] = []
    skipped: list[dict] = []

    for md_path in sorted(courses_dir.rglob("*.md")):
        raw = md_path.read_text(encoding="utf-8")
        meta, body = split_frontmatter(raw)
        level_key = (meta.get("study_level") or md_path.parent.name).strip().lower()
        by_level[level_key] = by_level.get(level_key, 0) + 1

        if level_key not in {"postgraduate", "postgraduate_research"}:
            skipped.append({"file": str(md_path.relative_to(output_dir)), "level": level_key})
            continue

        course_level = course_level_from_meta(meta, md_path.parent.name)
        h1 = re.search(r"^#\s+(.+)$", body, re.M)
        course_name = h1.group(1).strip() if h1 else md_path.stem
        course_label_match = re.search(r"\*\*Course:\*\*\s*(.+)", body, re.I)
        course_label = course_label_match.group(1).strip() if course_label_match else ""

        group = resolve_english_course_group(
            groups,
            course_name=course_name,
            course_body=body,
            course_level=course_level,
            english_programs=english_programs if isinstance(english_programs, list) else None,
        )
        record = {
            "file": str(md_path.relative_to(output_dir)),
            "course_name": course_name,
            "course_label": course_label,
            "level": course_level,
            "group": group,
        }
        if group:
            resolved.append(record)
        else:
            record["reason"] = diagnose_unresolved(
                groups,
                course_name=course_name,
                course_body=body,
                course_level=course_level,
            )
            missing.append(record)

    pg_total = len(resolved) + len(missing)
    coverage = (len(resolved) / pg_total * 100) if pg_total else 0.0

    print(f"=== Essex english-course-groups dry run ===")
    print(f"Mapping rows loaded: {len(groups)}")
    print()
    print("Course counts by level:")
    for level, count in sorted(by_level.items()):
        print(f"  {level}: {count}")
    print()
    print("PG/PGR lookup (english-course-groups.md scope):")
    print(f"  Total PG/PGR courses: {pg_total}")
    print(f"  Resolved to a group:  {len(resolved)} ({coverage:.1f}%)")
    print(f"  Unresolved:           {len(missing)}")
    print(f"  Skipped (UG/foundation): {len(skipped)}")
    print()
    print("Note: english-course-groups.md only covers postgraduate taught/research.")
    print("UG and foundation use english-requirements.md study-level rows instead.")
    print()

    if missing:
        print(f"--- Unresolved ({len(missing)}) ---")
        for item in missing:
            label = item["course_label"] or item["course_name"]
            print(f"  {item['file']}")
            print(f"    {label} [{item['level']}] -> {item['reason']}")
        print()

    report = {
        "mapping_rows": len(groups),
        "by_level": by_level,
        "pg_total": pg_total,
        "resolved_count": len(resolved),
        "missing_count": len(missing),
        "coverage_percent": round(coverage, 2),
        "resolved": resolved,
        "missing": missing,
        "skipped": skipped,
    }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Full report written to {args.json_out}")

    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
