"""Aston University course markdown cleanup (conditional rules).

Simple heading removal is configured in code/.env via COURSE_MARKDOWN_REMOVE_SECTIONS.
This module handles Aston-specific noise that .env cannot express cleanly.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import _parse_heading, main, remove_markdown_heading_section

_COURSE_NAV_LINE = re.compile(
    r"^(Apply now|Why choose Aston\?|Course type|Full-time|Location|Funding Type|Discipline).*$",
    re.I,
)
_DUPLICATE_H1 = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_COURSE_DETAILS_STOP_HEADINGS = {
    "entry requirements",
    "clearing entry requirements",
    "fees and scholarships",
}
_NOISE_LINE = re.compile(
    r"^(?:"
    r"ENTRY REQUIREMENTS|HOW TO APPLY|ASTON POWER SKILLS|Discover Power Skills"
    r"|The Modal Modal content.*"
    r"|(?:First|Second|Third|Fourth) box.*"
    r"|End (?:first|second|third|fourth) box.*"
    r"|<div class=.*"
    r")$",
    re.I,
)
_TESTIMONIAL_LINE = re.compile(
    r"(Hear from Carina|journey beyond graduation|Careers and Placements\. First box)",
    re.I,
)
_UK_FEE_LABEL = re.compile(r"^UK students\b", re.I)
_FEE_BOILERPLATE_LINE = re.compile(
    r"^(?:Placement year fee|Subject to parliamentary approval|"
    r"On 20 October 2025, the Government announced|"
    r"According to the Department for Education|"
    r"The duration of (?:your|this) programme is set out|"
    r"The placement year fee stated here is for September \d{4} entry|"
    r"The United Kingdom government has confirmed that European Union|"
    r"Tuition fees for students are reviewed annually|"
    r"An increase in fees will allow the University to cover the increased costs|"
    r"Fees and funding|More information on fees)\b",
    re.I,
)


def _normalize_blank_lines(markdown: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", markdown.strip())


def _drop_duplicate_title(markdown: str) -> str:
    """Drop repeated top-level headings with the same text (common on Aston pages)."""
    lines = markdown.splitlines()
    seen_title: str | None = None
    kept: list[str] = []
    for line in lines:
        match = _DUPLICATE_H1.match(line)
        if match and match.group(1) == "#":
            title = match.group(2).strip().casefold()
            if title == seen_title:
                continue
            seen_title = title
        kept.append(line)
    return "\n".join(kept)


def _drop_course_nav_bullets(markdown: str) -> str:
    """Remove in-page nav bullets rendered as a markdown list after the title."""
    lines = markdown.splitlines()
    kept: list[str] = []
    in_nav = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- ") and _COURSE_NAV_LINE.match(stripped[2:].strip()):
            in_nav = True
            continue
        if in_nav and stripped.startswith("- "):
            continue
        if in_nav and stripped and not stripped.startswith("- "):
            in_nav = False
        if not in_nav:
            kept.append(line)
    return "\n".join(kept)


def _drop_start_date_nav(markdown: str) -> str:
    """Remove lone 'Start date' blocks that only contain anchor links."""
    cleaned = markdown
    for heading in ("Start date", "Apply now"):
        cleaned = remove_markdown_heading_section(
            cleaned,
            heading=heading,
            level=2,
            until_level=2,
        )
    return cleaned


def _drop_markdown_section_until(
    markdown: str,
    *,
    start_heading: str,
    start_level: int,
    stop_headings: set[str],
) -> str:
    """Remove one section and following siblings until a stop heading at start_level."""
    lines = markdown.splitlines()
    kept: list[str] = []
    index = 0
    start_key = start_heading.strip().casefold()
    while index < len(lines):
        line = lines[index]
        heading = _parse_heading(line)
        if heading and heading[0] == start_level and heading[1].strip().casefold() == start_key:
            index += 1
            while index < len(lines):
                next_heading = _parse_heading(lines[index])
                if next_heading and next_heading[0] <= start_level:
                    if next_heading[1].strip().casefold() in stop_headings:
                        break
                index += 1
            continue
        kept.append(line)
        index += 1
    return "\n".join(kept)


def _drop_course_overview_boilerplate(markdown: str) -> str:
    """Drop overview / marketing blocks before entry requirements or fees."""
    cleaned = markdown
    for start_heading in ("course overview", "course description"):
        while True:
            next_cleaned = _drop_markdown_section_until(
                cleaned,
                start_heading=start_heading,
                start_level=2,
                stop_headings=_COURSE_DETAILS_STOP_HEADINGS,
            )
            if next_cleaned == cleaned:
                break
            cleaned = next_cleaned
    return cleaned


def _drop_empty_course_details(markdown: str) -> str:
    """Remove a bare '## Course details' heading with no body before the next h2."""
    lines = markdown.splitlines()
    kept: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.strip() == "## Course details":
            next_index = index + 1
            while next_index < len(lines) and not lines[next_index].strip():
                next_index += 1
            if next_index < len(lines) and lines[next_index].startswith("## "):
                index = next_index
                continue
        kept.append(line)
        index += 1
    return "\n".join(kept)


def _drop_uk_fee_blocks(markdown: str) -> str:
    """Remove UK student fee labels and their markdown tables."""
    lines = markdown.splitlines()
    kept: list[str] = []
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if _UK_FEE_LABEL.match(stripped):
            index += 1
            while index < len(lines):
                row = lines[index].strip()
                if not row or row.startswith("|"):
                    index += 1
                    continue
                break
            continue
        kept.append(lines[index])
        index += 1
    return "\n".join(kept)


def _drop_noise_lines(markdown: str) -> str:
    lines = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append(line)
            continue
        if _NOISE_LINE.match(stripped):
            continue
        if _TESTIMONIAL_LINE.search(stripped):
            continue
        if _FEE_BOILERPLATE_LINE.match(stripped):
            continue
        lines.append(line)
    return "\n".join(lines)


def _drop_power_skills_leftovers(markdown: str) -> str:
    """Remove any remaining Power Skills modal blocks between box markers."""
    lines = markdown.splitlines()
    kept: list[str] = []
    skipping = False
    for line in lines:
        stripped = line.strip()
        if re.match(r"^(?:First|Second|Third|Fourth) box", stripped, re.I):
            skipping = True
            continue
        if skipping and re.match(r"^End (?:first|second|third|fourth) box", stripped, re.I):
            skipping = False
            continue
        if skipping:
            continue
        if stripped == "ASTON POWER SKILLS":
            skipping = True
            continue
        kept.append(line)
    return "\n".join(kept)


def _normalize_course_summary_entry_requirements(markdown: str) -> str:
    """Collapse mashed key-info entry requirement lines into structured bullets."""
    lines = markdown.splitlines()
    out: list[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if line.strip() == "## Course summary":
            out.append(line)
            idx += 1
            while idx < len(lines) and not lines[idx].startswith("## "):
                current = lines[idx]
                if (
                    "Entry requirements" in current
                    and "**A-levels:**" not in current
                    and "### Entry requirements" not in current
                ):
                    # Mashed line: "... Entry requirements" then following grade lines
                    tail = current.split("Entry requirements", 1)[-1].strip()
                    if tail:
                        out.append(tail)
                    out.append("")
                    out.append("### Entry requirements")
                    out.append("")
                    idx += 1
                    while idx < len(lines) and lines[idx].strip() and not lines[idx].startswith("## "):
                        grade_line = lines[idx].strip()
                        if grade_line.startswith("- "):
                            out.append(grade_line)
                        elif re.search(r"\bBBB\b|\bBBC\b|\bBCC\b|\bCCD\b|\bDDM\b|\bDMM\b", grade_line):
                            out.append(f"- {grade_line}")
                        else:
                            out.append(grade_line)
                        idx += 1
                    out.append("")
                    continue
                out.append(current)
                idx += 1
            continue
        out.append(line)
        idx += 1
    return "\n".join(out)


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Aston-only rules applied after shared .env section removal."""
    cleaned = _drop_duplicate_title(markdown)
    cleaned = _drop_course_nav_bullets(cleaned)
    cleaned = _drop_start_date_nav(cleaned)
    cleaned = _normalize_course_summary_entry_requirements(cleaned)
    cleaned = _drop_course_overview_boilerplate(cleaned)
    cleaned = _drop_power_skills_leftovers(cleaned)
    cleaned = _drop_uk_fee_blocks(cleaned)
    cleaned = _drop_noise_lines(cleaned)
    cleaned = _drop_empty_course_details(cleaned)
    return _normalize_blank_lines(cleaned)


if __name__ == "__main__":
    raise SystemExit(main())
