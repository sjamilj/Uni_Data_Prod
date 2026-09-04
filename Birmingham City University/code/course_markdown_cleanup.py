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
    r"|Fees & How to Apply Statement Clearing 2026.*"
    r"|Call the hotline Apply online See hotline opening hours"
    r"|Book an Open Day"
    r"|Book Clearing Open Days"
    r"|Key Stats"
    r"|Similar Courses"
    r"|Professional Placement Year"
    r"|Introduction Called 'Essential qualifications' in the CMS"
    r"|Entry Requirements Statement.*"
    r"|Download now"
    r"|View fees for continuing students"
    r"|This course is aligned to the following organisations"
    r"|--END-- Full width fees and apply table"
    r")$",
    re.I,
)
_BCU_FEES_UI_LINE = re.compile(
    r"^(?:"
    r"Please select your student status to view fees and apply.*"
    r"|UK students$"
    r"|- International Student$"
    r"|International and part-time students can apply online.*"
    r"|Want to start in September \d{4}\? You can apply via UCAS.*"
    r"|If you.re unable to use our online application form.*"
    r"|An intensive 12-month MMus route may be proposed.*"
    r"|To find out more, see our application timeline\."
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
_COURSE_IN_DEPTH_TAIL = re.compile(
    r"\n(?:Foundation Year|Year One|First Year|Second Year|Final Year)\s*\n+"
    r"In order to complete this course.*",
    re.S | re.I,
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
        if _BCU_FEES_UI_LINE.match(stripped):
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


def _is_clearing_junk_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    lowered = stripped.lower()
    return bool(
        _POINTS_LINE.match(stripped)
        or _TARIFF_CALCULATOR_ONLY.match(stripped)
        or _HOTLINE_LINE.match(stripped)
        or _CLEARING_CMS_LINE.match(stripped)
        or "points required" in lowered
        or "(or equivalent)" in lowered
        or "ucas tariff calculator" in lowered
        or "call the hotline" in lowered
        or "view clearing courses" in lowered
        or "explore your options" in lowered
        or "places available to start in september" in lowered
        or "apply through clearing" in lowered
        or "apply online as normal" in lowered
        or "apply via ucas from september" in lowered
    )


def _is_hotline_junk_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    lowered = stripped.lower()
    return bool(
        _HOTLINE_LINE.match(stripped)
        or "clearing hotline" in lowered
        or "call the hotline" in lowered
        or "see hotline opening hours" in lowered
    )


def _strip_junk_under_h3(markdown: str, heading: str, is_junk_line) -> str:
    lines = markdown.splitlines()
    kept: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.strip() == f"### {heading}":
            kept.append(line)
            index += 1
            while index < len(lines):
                stripped = lines[index].strip()
                if stripped.startswith("#"):
                    break
                if is_junk_line(lines[index]):
                    index += 1
                    continue
                kept.append(lines[index])
                index += 1
            continue
        kept.append(line)
        index += 1
    return "\n".join(kept)


def _drop_empty_h3(markdown: str, heading: str) -> str:
    lines = markdown.splitlines()
    kept: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.strip() == f"### {heading}":
            next_index = index + 1
            while next_index < len(lines) and not lines[next_index].strip():
                next_index += 1
            if next_index < len(lines) and lines[next_index].startswith("#"):
                index = next_index
                continue
        kept.append(line)
        index += 1
    return "\n".join(kept)


def _drop_h3_heading_only(markdown: str, heading: str) -> str:
    target = f"### {heading}"
    return "\n".join(
        line for line in markdown.splitlines() if line.strip() != target
    )


def _drop_clearing_boilerplate(markdown: str) -> str:
    """Strip clearing/hotline junk lines under ### headings; keep course overview copy."""
    cleaned = _strip_junk_under_h3(markdown, "Clearing", _is_clearing_junk_line)
    cleaned = _strip_junk_under_h3(cleaned, "Hotline now open", _is_hotline_junk_line)
    cleaned = _drop_empty_h3(cleaned, "Clearing")
    cleaned = _drop_h3_heading_only(cleaned, "Hotline now open")
    return cleaned


def _study_level_from_markdown(markdown: str) -> str:
    match = re.search(r"^study_level:\s*(\S+)", markdown, re.M)
    return (match.group(1) if match else "").strip().lower()


def _drop_course_in_depth(markdown: str) -> str:
    cleaned = remove_markdown_heading_section(
        markdown,
        heading="Course in depth",
        level=2,
        until_level=1,
    )
    return _COURSE_IN_DEPTH_TAIL.sub("", cleaned).rstrip()


def _drop_empty_h2(markdown: str, heading: str) -> str:
    lines = markdown.splitlines()
    kept: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.strip() == f"## {heading}":
            next_index = index + 1
            while next_index < len(lines) and not lines[next_index].strip():
                next_index += 1
            if next_index < len(lines) and lines[next_index].startswith("## "):
                index = next_index
                continue
        kept.append(line)
        index += 1
    return "\n".join(kept)


def _drop_duplicate_fees_h2(markdown: str) -> str:
    if "## Fees and how to apply" not in markdown:
        return markdown
    return "\n".join(
        line for line in markdown.splitlines() if line.strip() != "## Fees & How to Apply"
    )


def _drop_overview_section(markdown: str) -> str:
    return remove_markdown_heading_section(
        markdown,
        heading="Overview",
        level=2,
        until_level=2,
    )


def preprocess_course_markdown_uni(markdown: str) -> str:
    """BCU rules that must run before .env heading removal (clearing/hotline h3 blocks)."""
    return _drop_clearing_boilerplate(markdown)


def _apply_bcu_python_cleanup(markdown: str, *, study_level: str) -> str:
    cleaned = _drop_overview_section(markdown)
    cleaned = _drop_duplicate_fees_h2(cleaned)
    cleaned = _drop_empty_h2(cleaned, "Clearing 2026")
    cleaned = _drop_course_in_depth(cleaned)
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


def cleanup_course_markdown_uni(markdown: str) -> str:
    """BCU rules applied during the pipeline clean pass."""
    return _apply_bcu_python_cleanup(
        markdown,
        study_level=_study_level_from_markdown(markdown),
    )


def extra_clean_course_markdown_uni(markdown: str, *, study_level: str) -> str:
    """BCU manual second-pass rules (run via shared/extra_clean_courses.py)."""
    return _apply_bcu_python_cleanup(markdown, study_level=study_level)


if __name__ == "__main__":
    raise SystemExit(main())
