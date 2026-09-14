#!/usr/bin/env python3
"""Compare course-page IELTS vs uni-mapped IELTS in Essex course markdown."""

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

from inject_english_requirements_md import (  # noqa: E402
    ENGLISH_TESTS_MARKER,
    body_before_mapped_block,
    build_english_json_from_uni_mapping,
    english_requirement_descriptions,
    iter_course_markdown_files,
)
from llm_extract import ExtractionPathConfig, Stage2Enricher, load_uni_section  # noqa: E402
from uni_pages import split_frontmatter  # noqa: E402

IELTS_OVERALL_RE = re.compile(r"IELTS\s+([\d.]+)\s+overall", re.I)
SECTION_RE = re.compile(
    r"(?:minimum of|no element below|minimum score of|with)\s+([\d.]+)\s+in "
    r"(?:each component|all components|all elements|each band|all other)",
    re.I,
)
NO_ELEMENT_RE = re.compile(r"with no element below\s+([\d.]+)", re.I)


def parse_ielts_line(text: str) -> tuple[str, str]:
    overall = ""
    section = ""
    match = IELTS_OVERALL_RE.search(text)
    if match:
        overall = match.group(1)
    sec = SECTION_RE.search(text)
    if sec:
        section = sec.group(1)
    elif NO_ELEMENT_RE.search(text):
        section = NO_ELEMENT_RE.search(text).group(1)
    return overall, section


def first_mapped_ielts(descriptions: list[str], payload: dict) -> tuple[str, str]:
    for line in descriptions:
        if "ielts" in line.lower():
            overall, section = parse_ielts_line(line)
            if overall:
                return overall, section
    return (
        str(payload.get("ieltsMinOverall", "") or "").strip(),
        str(payload.get("ieltsMinSection", "") or "").strip(),
    )


def compare_status(
    course_overall: str,
    course_section: str,
    mapped_overall: str,
    mapped_section: str,
) -> str:
    if not course_overall and not mapped_overall:
        return "no_ielts_both"
    if not course_overall:
        return "missing_course_ielts"
    if not mapped_overall:
        return "missing_mapped_ielts"
    if course_overall != mapped_overall:
        return "overall_mismatch"
    if course_section and mapped_section and course_section != mapped_section:
        return "section_mismatch"
    return "match"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uni-dir", type=Path, default=_UNI_DIR)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    output_dir = args.uni_dir / "output"
    english_content = load_uni_section(output_dir, "english-requirements.md")
    groups = ExtractionPathConfig.load_english_course_groups(output_dir)

    rows: list[dict[str, object]] = []
    for md_path in iter_course_markdown_files(output_dir):
        raw = md_path.read_text(encoding="utf-8")
        frontmatter, body = split_frontmatter(raw)
        level = (frontmatter.get("study_level") or md_path.parent.name).strip().lower()
        title = re.search(r"^#\s+(.+)$", body, re.M)
        course_name = title.group(1).strip() if title else md_path.stem

        if ENGLISH_TESTS_MARKER not in body:
            rows.append(
                {
                    "file": str(md_path.relative_to(output_dir)).replace("\\", "/"),
                    "status": "no_mapped_block",
                }
            )
            continue

        before = body_before_mapped_block(body)
        course_profile = Stage2Enricher.extract_course_ielts_profile(before)
        mapped_payload = build_english_json_from_uni_mapping(
            before,
            course_level=level,
            course_name=course_name,
            english_content=english_content,
            english_course_groups=groups,
        )
        descriptions = english_requirement_descriptions(mapped_payload)
        mapped_overall, mapped_section = first_mapped_ielts(descriptions, mapped_payload)
        course_overall = str(course_profile.get("overall", "") or "")
        course_section = str(
            course_profile.get("min_section", "")
            or course_profile.get("all_components_min", "")
            or ""
        )
        status = compare_status(
            course_overall, course_section, mapped_overall, mapped_section
        )
        rows.append(
            {
                "file": str(md_path.relative_to(output_dir)).replace("\\", "/"),
                "status": status,
                "course_overall": course_overall,
                "course_section": course_section,
                "mapped_overall": mapped_overall,
                "mapped_section": mapped_section,
                "mappedProgram": mapped_payload.get("mappedProgram", ""),
            }
        )

    counts = Counter(str(row["status"]) for row in rows)
    print("=== Essex IELTS: course text vs mapped parser ===")
    print(f"Courses scanned: {len(rows)}")
    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")

    mismatches = [row for row in rows if row["status"] != "match" and row["status"] != "no_mapped_block"]
    if mismatches:
        print(f"\nNon-matches ({len(mismatches)}):")
        for row in mismatches[:20]:
            print(
                f"  [{row['status']}] {row['file']}\n"
                f"    course {row.get('course_overall','?')}/{row.get('course_section','?')} "
                f"vs mapped {row.get('mapped_overall','?')}/{row.get('mapped_section','?')} "
                f"({row.get('mappedProgram','')})"
            )

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nReport: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
