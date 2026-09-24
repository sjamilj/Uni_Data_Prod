#!/usr/bin/env python3
"""Export entry-requirement patterns from cleaned course markdown to CSV.

IELTS: course .md first, then english-requirements.md by study level.
Bangladesh: UCAS / UK class from course .md mapped via bangladesh-entry.md.

  python shared/export_entry_requirements_pattern.py --code-dir "University of East London/code"
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from entry_requirements_mapping import (
    bangladesh_requirements_from_course,
    classify_postgraduate,
    extract_entry_block,
    map_postgraduate_class_to_cgpa,
    map_ucas_to_hsc_gpa,
    resolve_ielts_for_course,
    ucas_points_from_entry,
)
from scrape_course_urls import add_code_dir_argument, resolve_work_dir
from uni_paths import resolve_output_dir

STUDY_LEVEL_DIRS = ("undergraduate", "foundation", "postgraduate")

_A_LEVELS = re.compile(
    r"(A\s*Levels?\s+in\s+at\s+least\s+two\s+subjects)",
    re.I,
)
_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def _parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    block = text[3:end].strip()
    out: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        out[key.strip()] = val.strip()
    return out


def _course_title(text: str) -> str:
    for line in text.splitlines():
        if re.match(r"^# [^#]", line):
            return line[2:].strip()
    return ""


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _strip_md(s: str) -> str:
    return _normalize_ws(_MD_LINK.sub(r"\1", s))


def build_description(
    *,
    study_level: str,
    ucas_standard: str,
    ucas_contextual: str,
    ucas_foundation: str,
    hsc_gpa_standard: str,
    hsc_gpa_contextual: str,
    hsc_gpa_foundation: str,
    bangladesh_cgpa: str,
    postgraduate_class: str,
    a_levels: str,
    ielts: str,
    entry: str,
) -> str:
    parts: list[str] = []

    if study_level == "undergraduate":
        if ucas_standard:
            chunk = f"{ucas_standard} UCAS points (standard offer)"
            if hsc_gpa_standard:
                chunk += f", HSC GPA {hsc_gpa_standard}"
            parts.append(chunk)
        if ucas_contextual:
            chunk = f"{ucas_contextual} UCAS points (contextual offer)"
            if hsc_gpa_contextual:
                chunk += f", HSC GPA {hsc_gpa_contextual}"
            parts.append(chunk)
    elif study_level == "foundation" and ucas_foundation:
        chunk = (
            f"{ucas_foundation} UCAS points from an equivalent Level 3 qualification "
            "listed on the UCAS tariff calculator"
        )
        if hsc_gpa_foundation:
            chunk += f", HSC GPA {hsc_gpa_foundation}"
        parts.append(chunk)
    elif study_level == "postgraduate" and postgraduate_class:
        qual = _primary_pg_line(entry)
        parts.append(qual if qual else postgraduate_class)
        if bangladesh_cgpa:
            parts.append(f"Bangladesh CGPA {bangladesh_cgpa}")

    if a_levels:
        parts.append(a_levels)
    if ielts:
        parts.append(ielts)

    if not parts and entry:
        snippet = _strip_md(entry)
        parts.append(snippet[:397] + "..." if len(snippet) > 400 else snippet)

    return ", ".join(parts)


def _primary_pg_line(entry: str) -> str:
    for line in entry.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if re.search(r"international qualification", line, re.I):
            break
        if len(line) > 20 and not line.lower().startswith("we accept"):
            return _strip_md(line.lstrip("- "))
    return ""


def row_from_markdown(
    path: Path,
    study_level: str,
    *,
    bangladesh_content: str,
    english_content: str,
) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    meta = _parse_frontmatter(text)
    entry = extract_entry_block(text, study_level)

    ucas = ucas_points_from_entry(study_level, entry)
    ucas_standard = ucas["ucas_standard"]
    ucas_contextual = ucas["ucas_contextual"]
    ucas_foundation = ucas["ucas_foundation"]

    postgraduate_class = ""
    if study_level == "postgraduate":
        postgraduate_class = classify_postgraduate(entry)

    a_levels = ""
    m = _A_LEVELS.search(entry)
    if m:
        a_levels = m.group(1)

    ielts_info = resolve_ielts_for_course(
        course_markdown=text,
        study_level=study_level,
        english_requirements_content=english_content,
        entry_block=entry,
    )

    hsc_gpa_standard = map_ucas_to_hsc_gpa(
        ucas_standard,
        study_level="undergraduate",
        bangladesh_content=bangladesh_content,
    )
    hsc_gpa_contextual = map_ucas_to_hsc_gpa(
        ucas_contextual,
        study_level="undergraduate",
        bangladesh_content=bangladesh_content,
    )
    hsc_gpa_foundation = map_ucas_to_hsc_gpa(
        ucas_foundation,
        study_level="foundation",
        bangladesh_content=bangladesh_content,
    )
    bangladesh_cgpa = map_postgraduate_class_to_cgpa(
        postgraduate_class,
        bangladesh_content=bangladesh_content,
    )

    bd_rows = bangladesh_requirements_from_course(
        study_level=study_level,
        entry_block=entry,
        course_markdown=text,
        bangladesh_content=bangladesh_content,
        postgraduate_class=postgraduate_class,
    )

    description = build_description(
        study_level=study_level,
        ucas_standard=ucas_standard,
        ucas_contextual=ucas_contextual,
        ucas_foundation=ucas_foundation,
        hsc_gpa_standard=hsc_gpa_standard,
        hsc_gpa_contextual=hsc_gpa_contextual,
        hsc_gpa_foundation=hsc_gpa_foundation,
        bangladesh_cgpa=bangladesh_cgpa,
        postgraduate_class=postgraduate_class,
        a_levels=a_levels,
        ielts=ielts_info["ielts"],
        entry=entry,
    )

    return {
        "course_slug": path.stem,
        "course_title": _course_title(text),
        "study_level": study_level,
        "course_url": meta.get("course_url", ""),
        "ucas_standard": ucas_standard,
        "ucas_contextual": ucas_contextual,
        "ucas_foundation": ucas_foundation,
        "hsc_gpa_standard": hsc_gpa_standard,
        "hsc_gpa_contextual": hsc_gpa_contextual,
        "hsc_gpa_foundation": hsc_gpa_foundation,
        "postgraduate_class": postgraduate_class,
        "bangladesh_cgpa": bangladesh_cgpa,
        "a_levels_requirement": a_levels,
        "ielts": ielts_info["ielts"],
        "ielts_source": ielts_info["ielts_source"],
        "ielts_overall": ielts_info["ielts_overall"],
        "ielts_min_section": ielts_info["ielts_min_section"],
        "bangladesh_requirements_json": json.dumps(bd_rows, ensure_ascii=False),
        "description": description,
        "entry_requirements_full": entry,
    }


def export_patterns(code_dir: Path, output_csv: Path | None = None) -> Path:
    output_dir = resolve_output_dir(code_dir)
    courses_root = output_dir / "clean" / "courses"
    uni_root = output_dir / "clean" / "uni"
    bangladesh_content = ""
    english_content = ""
    bd_path = uni_root / "bangladesh-entry.md"
    en_path = uni_root / "english-requirements.md"
    if bd_path.is_file():
        bangladesh_content = bd_path.read_text(encoding="utf-8")
    if en_path.is_file():
        english_content = en_path.read_text(encoding="utf-8")

    if output_csv is None:
        output_csv = output_dir / "entry_requirements_pattern.csv"

    fieldnames = [
        "course_slug",
        "course_title",
        "study_level",
        "course_url",
        "ucas_standard",
        "ucas_contextual",
        "ucas_foundation",
        "hsc_gpa_standard",
        "hsc_gpa_contextual",
        "hsc_gpa_foundation",
        "postgraduate_class",
        "bangladesh_cgpa",
        "a_levels_requirement",
        "ielts",
        "ielts_source",
        "ielts_overall",
        "ielts_min_section",
        "bangladesh_requirements_json",
        "description",
        "entry_requirements_full",
    ]

    rows: list[dict[str, str]] = []
    for level in STUDY_LEVEL_DIRS:
        folder = courses_root / level
        if not folder.is_dir():
            continue
        for md_path in sorted(folder.glob("*.md")):
            rows.append(
                row_from_markdown(
                    md_path,
                    level,
                    bangladesh_content=bangladesh_content,
                    english_content=english_content,
                )
            )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} row(s) to {output_csv}")
    return output_csv


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export entry requirement patterns from cleaned course markdown."
    )
    add_code_dir_argument(parser)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="CSV path (default: {output}/entry_requirements_pattern.csv)",
    )
    args = parser.parse_args()
    code_dir = resolve_work_dir(args.code_dir)
    try:
        export_patterns(code_dir, args.output)
    except OSError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
