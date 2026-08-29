"""ARU-specific course markdown cleanup (conditional rules).

Simple heading removal is configured in code/.env via COURSE_MARKDOWN_REMOVE_SECTIONS
(shared/course_markdown_cleanup.py). This module only handles rules that need
document context (dual MSc / Professional Experience track).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import main

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_PROFESSIONAL_EXPERIENCE_H4 = re.compile(r"^####\s+Professional\s+Experience\s*$", re.I | re.M)
_PRIMARY_MSC_H4 = re.compile(r"^####\s+MSc\s*$", re.I | re.M)
_PROFESSIONAL_EXPERIENCE_TAGLINE = re.compile(
    r"^Professional\s+Experience\s+option\s+available\s*$",
    re.I | re.M,
)


def _parse_heading(line: str) -> tuple[int, str] | None:
    match = _HEADING_RE.match(line)
    if not match:
        return None
    return len(match.group(1)), match.group(2).strip()


def remove_markdown_heading_section(
    markdown: str,
    *,
    heading: str,
    level: int,
    until_level: int | None = None,
) -> str:
    """Drop one section that starts at an exact heading until the next stop heading."""
    target = heading.strip().lower()
    stop_level = level if until_level is None else until_level
    lines = markdown.splitlines()
    kept: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        parsed = _parse_heading(line)
        if parsed and parsed[0] == level and parsed[1].lower() == target:
            index += 1
            while index < len(lines):
                next_heading = _parse_heading(lines[index])
                if next_heading and next_heading[0] <= stop_level:
                    break
                index += 1
            continue
        kept.append(line)
        index += 1
    return "\n".join(kept)


def _normalize_blank_lines(markdown: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", markdown.strip())


def _has_dual_msc_track(markdown: str) -> bool:
    return bool(_PRIMARY_MSC_H4.search(markdown) and _PROFESSIONAL_EXPERIENCE_H4.search(markdown))


def strip_professional_experience_variant(markdown: str) -> str:
    """
    When both #### MSc and #### Professional Experience are present, keep the
    standard MSc track only.
    """
    if not _has_dual_msc_track(markdown):
        return markdown

    cleaned = _PROFESSIONAL_EXPERIENCE_TAGLINE.sub("", markdown)
    while _PROFESSIONAL_EXPERIENCE_H4.search(cleaned):
        cleaned = remove_markdown_heading_section(
            cleaned,
            heading="Professional Experience",
            level=4,
            until_level=3,
        )
    cleaned = remove_markdown_heading_section(
        cleaned,
        heading="Professional Experience modules",
        level=3,
    )
    return _normalize_blank_lines(cleaned)


def cleanup_course_markdown_uni(markdown: str) -> str:
    """ARU-only rules applied after shared .env section removal."""
    return strip_professional_experience_variant(markdown)


if __name__ == "__main__":
    raise SystemExit(main())
