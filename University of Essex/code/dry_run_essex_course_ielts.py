#!/usr/bin/env python3
"""Inspect IELTS text variations across Essex clean course markdown files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
_UNI_DIR = _CODE_DIR.parent
_REPO = _CODE_DIR.parents[1]

_SHARED = _REPO / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import parse_uni_json_payload  # noqa: E402
from llm_extract import (  # noqa: E402
    ExtractionPathConfig,
    Stage2Enricher,
    load_uni_section,
    resolve_english_course_group,
    select_english_json_program,
)
from uni_pages import split_frontmatter  # noqa: E402


def normalize_pattern(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r"[\d.]+", "N", text)
    return text


def profile_key(profile: dict[str, str]) -> str:
    if not profile:
        return "UNPARSED"
    parts = [f"{key}={profile[key]}" for key in sorted(profile)]
    return ", ".join(parts)


def extract_ielts_snippet(section: str) -> str:
    section = Stage2Enricher._normalize_ielts_text(section)
    match = re.search(r"IELTS.{0,220}", section, re.I | re.S)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(0)).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--uni-dir",
        type=Path,
        default=_UNI_DIR,
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Optional path to write full inspection report JSON",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=2,
        help="Example snippets per normalized pattern (default: 2)",
    )
    args = parser.parse_args()

    output_dir = args.uni_dir / "output"
    courses_dir = output_dir / "clean" / "courses"
    groups = ExtractionPathConfig.load_english_course_groups(output_dir)
    english_programs = parse_uni_json_payload(
        load_uni_section(output_dir, "english-requirements.md"),
        "english-requirements",
    ) or []

    rows: list[dict] = []
    pattern_examples: dict[str, list[str]] = {}
    profile_counts: Counter[str] = Counter()
    missing_counts: Counter[str] = Counter()

    for md_path in sorted(courses_dir.rglob("*.md")):
        raw = md_path.read_text(encoding="utf-8")
        meta, body = split_frontmatter(raw)
        level = (meta.get("study_level") or md_path.parent.name).strip().lower()
        section = Stage2Enricher.extract_english_language_section(body)
        snippet = extract_ielts_snippet(section) if section else ""
        profile = Stage2Enricher.extract_course_ielts_profile(body) if section else {}
        pattern = normalize_pattern(snippet) if snippet else "NO_IELTS"
        profile_counts[profile_key(profile)] += 1

        h1 = re.search(r"^#\s+(.+)$", body, re.M)
        course_name = h1.group(1).strip() if h1 else md_path.stem
        course_label_match = re.search(r"\*\*Course:\*\*\s*(.+)", body, re.I)
        course_label = course_label_match.group(1).strip() if course_label_match else ""

        group = ""
        mapped_overall = ""
        mapped_section = ""
        mapped_source = ""
        if level in {"postgraduate", "postgraduate_research"}:
            course_level = "postgraduate_research" if "research" in level else "postgraduate"
            group = resolve_english_course_group(
                groups,
                course_name=course_name,
                course_body=body,
                course_level=course_level,
                english_programs=english_programs if isinstance(english_programs, list) else None,
            )
            program = select_english_json_program(
                english_programs,
                course_level=course_level,
                course_name=course_name,
                course_body=body,
            )
            if isinstance(program, dict):
                mapped_overall = str(program.get("ieltsMinOverall", "") or "")
                mapped_section = str(program.get("ieltsMinSection", "") or "")
                if str(program.get("ProgramName", "") or "").strip():
                    mapped_source = str(program.get("ProgramName", ""))
                elif program.get("requiredIelts"):
                    mapped_source = "flat-row"
        elif profile:
            flat = Stage2Enricher.select_english_flat_row_by_ielts(english_programs, body)
            if flat:
                mapped_overall = str(flat.get("ieltsMinOverall", "") or "")
                mapped_section = str(flat.get("ieltsMinSection", "") or "")
                mapped_source = "flat-row"

        if not section:
            missing_counts["no_english_section"] += 1
        elif not snippet:
            missing_counts["no_ielts_text"] += 1
        elif not profile:
            missing_counts["ielts_not_parsed"] += 1

        rel = str(md_path.relative_to(output_dir))
        row = {
            "file": rel,
            "level": level,
            "course_name": course_name,
            "course_label": course_label,
            "course_url": meta.get("course_url", ""),
            "ielts_snippet": snippet,
            "pattern": pattern,
            "profile": profile,
            "group": group,
            "mapped_overall": mapped_overall,
            "mapped_section": mapped_section,
            "mapped_source": mapped_source,
        }
        rows.append(row)
        if snippet and pattern not in pattern_examples:
            pattern_examples[pattern] = []
        if snippet and len(pattern_examples[pattern]) < args.sample:
            pattern_examples[pattern].append(snippet)

    print("=== Essex course IELTS dry run ===")
    print(f"Course files scanned: {len(rows)}")
    print()
    print("Missing / unparsed:")
    for key, count in missing_counts.most_common():
        print(f"  {key}: {count}")
    print()
    print("Parsed IELTS profiles:")
    for key, count in profile_counts.most_common(12):
        print(f"  {count:4d}  {key}")
    print()
    print("Normalized IELTS text patterns:")
    pattern_counter = Counter(row["pattern"] for row in rows if row["ielts_snippet"])
    for pattern, count in pattern_counter.most_common(15):
        print(f"  {count:4d}  {pattern}")
        for example in pattern_examples.get(pattern, [])[: args.sample]:
            print(f"        e.g. {example[:130]}")
    print()

    target = next((r for r in rows if "pg00427-1-msc-financial-economics-and-accounting" in r["file"]), None)
    if target:
        print("=== pg00427 Financial Economics and Accounting ===")
        print(f"URL: {target['course_url']}")
        print(f"Snippet: {target['ielts_snippet']}")
        print(f"Parsed: {target['profile']}")
        print(f"Group: {target['group'] or '(none)'}")
        print(f"Mapped: IELTS {target['mapped_overall']}/{target['mapped_section']} via {target['mapped_source']}")
        print()

    pg_rows = [r for r in rows if r["level"] in {"postgraduate", "postgraduate_research"}]
    pg_resolved = sum(1 for r in pg_rows if r["group"])
    print(f"PG/PGR group resolve: {pg_resolved}/{len(pg_rows)} ({pg_resolved/len(pg_rows)*100:.1f}%)")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(
                {
                    "total": len(rows),
                    "missing": dict(missing_counts),
                    "profiles": dict(profile_counts),
                    "patterns": [
                        {"pattern": p, "count": c, "examples": pattern_examples.get(p, [])}
                        for p, c in pattern_counter.most_common()
                    ],
                    "rows": rows,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"Full report: {args.json_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
