"""Brunel University London course markdown cleanup."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import main, remove_markdown_heading_section

_SCROLL_LINE = re.compile(r"^Scroll to #", re.I)
_APPLY_LINE = re.compile(r"^Visit https?://.*#entryRequirements to apply$", re.I)
_SCHOLARSHIP_PROMO = re.compile(
    r"^Vice-Chancellor.*(?:Award|scholarship).*(?:Find out more)?$",
    re.I,
)
_PART_TIME_FEE = re.compile(r"^£[\d,]+ part-time$", re.I)
_STAGED_MASTER_FEE = re.compile(r"^Staged Master (?:UK/EU|International):", re.I)
_COUNTRY_SELECT = re.compile(r"^Select your country/region$", re.I)
_MAP_JUNK = re.compile(r"^\+ − Leaflet \| © OpenStreetMap", re.I)
_APPLY_NAV = re.compile(
    r"^(?:"
    r"Enquire now"
    r"|Find scholarships"
    r"|Apply .+"
    r"|Subject area:"
    r"|Postgraduate events"
    r")$",
    re.I,
)
_MARKETING_TO_INTL = re.compile(
    r"\nScroll to #entryRequirements\n.*?(?=\n## International entry requirements)",
    re.S | re.I,
)


def _normalize_blank_lines(markdown: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", markdown.strip())


def _drop_duplicate_h1(markdown: str) -> str:
    lines = markdown.splitlines()
    seen_title = False
    kept: list[str] = []
    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            if seen_title:
                continue
            seen_title = True
        kept.append(line)
    return "\n".join(kept)


def _drop_noise_lines(markdown: str) -> str:
    kept: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            kept.append(line)
            continue
        if _SCROLL_LINE.match(stripped):
            continue
        if _APPLY_LINE.match(stripped):
            continue
        if _SCHOLARSHIP_PROMO.match(stripped):
            continue
        if _PART_TIME_FEE.match(stripped):
            continue
        if _STAGED_MASTER_FEE.match(stripped):
            continue
        if _COUNTRY_SELECT.match(stripped):
            continue
        if _MAP_JUNK.match(stripped):
            continue
        if _APPLY_NAV.match(stripped):
            continue
        if stripped.startswith("- - Apply "):
            continue
        kept.append(line)
    return "\n".join(kept)


def _drop_marketing_before_international_entry(markdown: str) -> str:
    return _MARKETING_TO_INTL.sub("\n", markdown)


def _truncate_from_teaching_and_learning(markdown: str) -> str:
    marker = "## Teaching and learning"
    index = markdown.find(marker)
    if index == -1:
        return markdown
    return markdown[:index].rstrip()


def _truncate_duplicate_tail(markdown: str) -> str:
    """Drop repeated entry/fees blocks appended from #fees extraction."""
    marker = "## International entry requirements"
    first = markdown.find(marker)
    if first == -1:
        return markdown
    second = markdown.find(marker, first + len(marker))
    if second == -1:
        return markdown
    return markdown[:second].rstrip()


def cleanup_course_markdown_uni(markdown: str) -> str:
    cleaned = _drop_duplicate_h1(markdown)
    cleaned = _drop_marketing_before_international_entry(cleaned)
    cleaned = _drop_noise_lines(cleaned)
    cleaned = _truncate_from_teaching_and_learning(cleaned)
    cleaned = _truncate_duplicate_tail(cleaned)
    cleaned = remove_markdown_heading_section(
        cleaned,
        heading="Overview",
        level=2,
        until_level=2,
    )
    return _normalize_blank_lines(cleaned)


if __name__ == "__main__":
    raise SystemExit(main())
