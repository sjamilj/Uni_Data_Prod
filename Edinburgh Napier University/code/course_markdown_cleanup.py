"""Edinburgh Napier — course markdown cleanup.

Course pages: strip overview marketing copy, CTA noise, the ### Entry requirements
FAQ block, ### Year 1 UK entry, and fees boilerplate (keep **Overseas fee:** only under ## Fees).

ENUIC IS1 foundation courses (catalogue URLs under /global/enuic/is1/) are cleaned to:

  Course: {progression degree with Foundation Year}

  Key information 2026/27
  Duration - …
  …
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import main, remove_markdown_heading_section


def is_enuic_foundation_catalogue_url(catalogue_url: str) -> bool:
    return "/global/enuic/is1/" in (catalogue_url or "").lower()


def enuic_foundation_clean_blocks() -> list[tuple[str, str]]:
    return [("", "section.featured-text")]


def preprocess_course_html_uni(
    soup: BeautifulSoup,
    *,
    catalogue_url: str = "",
    course_name: str = "",
) -> None:
    """Keep only the IS1 pathway Key information block before generic clean."""
    if not is_enuic_foundation_catalogue_url(catalogue_url):
        return

    featured = soup.select_one("section.featured-text")
    if featured is None:
        return

    for selector in (
        ".introText",
        "section.mainBodyText",
        "#mainContentArea",
    ):
        for node in soup.select(selector):
            node.decompose()

    wrapper = soup.select_one(".contentWrapper") or soup.body
    if wrapper is None:
        return

    clone = BeautifulSoup(str(featured), "html.parser")
    featured_copy = clone.select_one("section.featured-text") or clone
    wrapper.clear()
    wrapper.append(featured_copy)


def _strip_course_overview_lead_prose(markdown: str) -> str:
    """Drop marketing copy under ## Course overview; keep ### Mode of Study, etc."""
    lines = markdown.splitlines()
    out: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.strip() == "## Course overview":
            out.append(line)
            index += 1
            while index < len(lines):
                stripped = lines[index].strip()
                if stripped.startswith("### "):
                    break
                if stripped.startswith("## "):
                    break
                index += 1
            continue
        out.append(line)
        index += 1
    return "\n".join(out)


_NAPIER_OVERVIEW_CTA_RE = re.compile(
    r"\nVisit us Apply for [^\n]+ Enquire about this course >\s*\n",
    re.I,
)


def _strip_entry_requirements_subsection(markdown: str) -> str:
    """Drop ### Entry requirements FAQ under ## Entry requirements; keep English language, etc."""
    return remove_markdown_heading_section(
        markdown,
        heading="Entry requirements",
        level=3,
    )


def _strip_year_one_uk_entry(markdown: str) -> str:
    """Drop ### Year 1 / #### Minimum Year 1 UK qualification blocks (use uni bangladesh-entry)."""
    return remove_markdown_heading_section(
        markdown,
        heading="Year 1",
        level=3,
    )


_OVERSEAS_FEE_LINE_RE = re.compile(r"\*\*Overseas fee:\*\*\s*£[\d,]+", re.I)
_OVERSEAS_FEE_TABLE_RE = re.compile(r"Overseas and EU\s*\|\s*£([\d,]+)", re.I)


def _overseas_fee_line(markdown: str) -> str | None:
    match = _OVERSEAS_FEE_LINE_RE.search(markdown)
    if match:
        return match.group(0).strip()
    table = _OVERSEAS_FEE_TABLE_RE.search(markdown)
    if table:
        return f"**Overseas fee:** £{table.group(1)}"
    return None


def _trim_fees_to_overseas_line(markdown: str) -> str:
    """Keep ## Fees + **Overseas fee:** only; drop funding prose, tables, and alumni notes."""
    overseas = _overseas_fee_line(markdown)
    if not overseas:
        return markdown

    overseas_match = None
    for match in _OVERSEAS_FEE_LINE_RE.finditer(markdown):
        overseas_match = match
    if overseas_match is None:
        return markdown

    overseas_start = overseas_match.start()
    fees_start: int | None = None
    for heading in re.finditer(r"^## Fees\b[^\n]*$", markdown[:overseas_start], re.M | re.I):
        fees_start = heading.start()
    if fees_start is None:
        return markdown

    after_overseas = markdown[overseas_match.end() :]
    next_section = re.search(r"^## ", after_overseas, re.M)
    tail = after_overseas[next_section.start() :] if next_section else ""

    before = markdown[:fees_start]
    return f"{before}## Fees\n\n{overseas}\n{tail}".rstrip() + "\n"


def cleanup_course_markdown_uni(markdown: str) -> str:
    text = _strip_course_overview_lead_prose(markdown)
    text = _NAPIER_OVERVIEW_CTA_RE.sub("\n", text)
    text = _strip_entry_requirements_subsection(text)
    text = _strip_year_one_uk_entry(text)
    text = _trim_fees_to_overseas_line(text)

    if not text.strip().startswith("Course:"):
        return text

    text = text.strip()
    text = re.sub(r"^## Key information\b", "Key information", text, count=1)
    text = re.sub(
        r"(Key information\s*\d{4}/\d{2})\s*\n+\1",
        r"\1",
        text,
        count=1,
    )
    return text + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
