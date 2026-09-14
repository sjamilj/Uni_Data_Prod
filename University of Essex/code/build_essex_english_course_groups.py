#!/usr/bin/env python3
"""Build University of Essex english-course-groups.md from PG English PDF markdown."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
_UNI_DIR = _CODE_DIR.parent
_REPO = _CODE_DIR.parents[1]


def parse_course_groups(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    current_award = "taught"
    current_department = ""

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("### "):
            current_department = line[4:].strip()
            current_award = "taught"
            continue

        if not line.startswith("|"):
            continue

        parts = [part.strip() for part in line.split("|")]
        parts = [part for part in parts if part]
        if not parts:
            continue

        if len(parts) >= 3 and not parts[1] and not parts[2]:
            current_department = parts[0].strip("* ")
            current_award = "taught"
            continue

        if len(parts) == 1 and len(parts[0]) > 10 and "Group" not in parts[0]:
            if re.search(
                r"\([A-Z]+\)|SCHOOL|SCIENCES|STUDIES|ENGINEERING|ECONOMICS|GOVERNMENT|LAW|CARE|HOTEL",
                parts[0],
            ):
                current_department = parts[0].strip("* ")
                current_award = "taught"
            continue

        if parts[0].startswith("**Taught Courses"):
            current_award = "taught"
            continue
        if parts[0].startswith("**Research Courses"):
            current_award = "research"
            continue

        group_match = re.fullmatch(r"Group\s+(\d+)", parts[-1], re.I)
        if not group_match or len(parts) < 2:
            continue

        course_name = parts[-2].strip()
        if not course_name or course_name.lower() in {"course", "award"}:
            continue

        rows.append(
            {
                "courseName": course_name,
                "englishGroup": f"Group {group_match.group(1)}",
                "studyLevel": "postgraduate",
                "department": current_department.strip("* "),
            }
        )

    seen: set[tuple[str, ...]] = set()
    unique: list[dict[str, str]] = []
    for row in rows:
        key = (
            row["courseName"].casefold(),
            row["englishGroup"].casefold(),
            row["department"].casefold(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return sorted(unique, key=lambda item: (item["courseName"].casefold(), item["department"]))


def render_markdown(rows: list[dict[str, str]], *, source_url: str) -> str:
    payload = json.dumps(rows, indent=2, ensure_ascii=False)
    return f"""---
source_html: uni_req/english-course-groups.html
source_url: {source_url}
page_type: uni
university: University of Essex
cleaned_at: 2026-09-14
---
# English Course Groups

{payload}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("uploads/english_language_requirements.pdf-0.md"),
        help="Extracted markdown from english_language_requirements.pdf",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_UNI_DIR / "output" / "clean" / "uni" / "english-course-groups.md",
        help="Output clean/uni markdown path",
    )
    parser.add_argument(
        "--source-url",
        default="https://www.essex.ac.uk/-/media/documents/study/english_language_requirements.pdf",
    )
    args = parser.parse_args()

    text = args.input.read_text(encoding="utf-8")
    rows = parse_course_groups(text)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_markdown(rows, source_url=args.source_url), encoding="utf-8")
    print(f"Wrote {len(rows)} course-group rows to {args.output}")


if __name__ == "__main__":
    main()
