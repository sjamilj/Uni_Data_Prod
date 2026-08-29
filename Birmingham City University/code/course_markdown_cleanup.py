"""Birmingham City University course markdown cleanup.

Pipeline pass (automatic):
  - COURSE_MARKDOWN_REMOVE_SECTIONS in code/.env
  - cleanup_course_markdown_uni()

Manual extra pass (shared/extra_clean_courses.py):
  - EXTRA_CLEAN_REMOVE_SECTIONS_* in code/.env
  - extra_clean_course_markdown_uni(markdown, study_level=...)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import main, remove_markdown_heading_section

_CLEARING_CMS_LINE = re.compile(
    r"^(?:"
    r"Clearing 2026\s*-\s*.*"
    r"|Entry Requirements Statement Clearing 2026.*"
    r"|Call the hotline Apply online See hotline opening hours"
    r"|Book an Open Day"
    r"|Book Clearing Open Days"
    r"|Key Stats"
    r"|Similar Courses"
    r"|Professional Placement Year"
    r"|Introduction Called 'Essential qualifications' in the CMS"
    r"|Download now"
    r"|View fees for continuing students"
    r"|This course is aligned to the following organisations"
    r")$",
    re.I,
)
_TARIFF_CALCULATOR_ONLY = re.compile(
    r"^Use the \[UCAS tariff calculator\].*$",
    re.I,
)
_POINTS_LINE = re.compile(r"^\d+ points required$", re.I)
_HOTLINE_LINE = re.compile(r"^Call 0121 331 6777$", re.I)
_OPEN_DAY_DATE = re.compile(r"^Next Open Days:", re.I)
_STUDENT_TESTIMONIAL = re.compile(
    r"^(?:"
    r".+,\s*.+\s+student$"
    r"|The whole three years here have been amazing\."
    r"|BCU is developing and tailoring my professional"
    r")$",
    re.I,
)


def _normalize_blank_lines(markdown: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", markdown.strip())


def _drop_noise_lines(markdown: str) -> str:
    lines: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append(line)
            continue
        if _CLEARING_CMS_LINE.match(stripped):
            continue
        if _TARIFF_CALCULATOR_ONLY.match(stripped):
            continue
        if _POINTS_LINE.match(stripped):
            continue
        if _HOTLINE_LINE.match(stripped):
            continue
        if _OPEN_DAY_DATE.match(stripped):
            continue
        if _STUDENT_TESTIMONIAL.match(stripped):
            continue
        lines.append(line)
    return "\n".join(lines)


def _drop_empty_overview(markdown: str) -> str:
    """Drop a bare ## Overview with only clearing/marketing content before the next h2."""
    lines = markdown.splitlines()
    kept: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.strip() == "## Overview":
            next_index = index + 1
            while next_index < len(lines) and not lines[next_index].strip():
                next_index += 1
            if next_index < len(lines) and lines[next_index].startswith("## "):
                index = next_index
                continue
        kept.append(line)
        index += 1
    return "\n".join(kept)


def _drop_clearing_boilerplate(markdown: str) -> str:
    cleaned = markdown
    for heading in ("Clearing 2026", "Clearing"):
        while True:
            next_cleaned = remove_markdown_heading_section(
                cleaned,
                heading=heading,
                level=2,
                until_level=2,
            )
            if next_cleaned == cleaned:
                next_cleaned = remove_markdown_heading_section(
                    cleaned,
                    heading=heading,
                    level=3,
                    until_level=2,
                )
            if next_cleaned == cleaned:
                break
            cleaned = next_cleaned
    return cleaned


def cleanup_course_markdown_uni(markdown: str) -> str:
    """BCU rules applied during the pipeline clean pass."""
    return markdown


def extra_clean_course_markdown_uni(markdown: str, *, study_level: str) -> str:
    """BCU manual second-pass rules (run via shared/extra_clean_courses.py)."""
    cleaned = _drop_clearing_boilerplate(markdown)
    cleaned = _drop_empty_overview(cleaned)
    cleaned = _drop_noise_lines(cleaned)

    if study_level in {"foundation", "undergraduate"}:
        cleaned = remove_markdown_heading_section(
            cleaned,
            heading="Why Choose Us?",
            level=3,
            until_level=2,
        )
        cleaned = remove_markdown_heading_section(
            cleaned,
            heading="Open Days",
            level=3,
            until_level=2,
        )

    return _normalize_blank_lines(cleaned)


if __name__ == "__main__":
    raise SystemExit(main())
