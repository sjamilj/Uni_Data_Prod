"""University-specific course markdown cleanup (optional).

Configure simple heading removal in code/.env:

  COURSE_MARKDOWN_REMOVE_SECTIONS="
  4 :: With placement
  3 :: UK students
  "

Add conditional rules here via cleanup_course_markdown_uni() when .env is not enough.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, Tag

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import main, remove_markdown_heading_section

SALFORD_KEY_FACTS_ID = "salford-course-key-facts"
_KEY_FACT_ORDER = ("Duration", "UCAS code", "Campus")
_SUMMARY_LABELS = {
    "how long will i study?": "Duration",
    "what is the ucas code?": "UCAS code",
    "where will i study?": "Campus",
}

_SALFORD_YEAR_FEE_BLOCK = re.compile(
    r"### (\d{4}/\d{2})\s*\n+\| Type of study \| Fees \|\n\| --- \| --- \|\n(.*?)(?=\n\n)",
    re.S,
)
_FEES_SECTION = re.compile(
    r"(## Fees and funding\s*\n)(.*?)(?=\n## |\Z)",
    re.S | re.I,
)
_ENTRY_INTL_IELTS = re.compile(
    r"\nInternational students\s*\n+"
    r"(If you are an international student[^\n]*IELTS[^\n]+\.)",
    re.I,
)
_FULL_TIME_FEE = re.compile(r"\|\s*Full-time\s*\|\s*£([\d,]+)\s*per year", re.I)


def _summary_item_bodies(item: Tag) -> list[str]:
    bodies = item.select(".uos-course__summary__item__body p")
    if bodies:
        return [p.get_text(" ", strip=True) for p in bodies if p.get_text(strip=True)]
    body = item.select_one(".uos-course__summary__item__body")
    if body is None:
        return []
    text = body.get_text(" ", strip=True)
    return [text] if text else []


def _facts_from_course_summary(soup: BeautifulSoup) -> dict[str, str]:
    summary = soup.select_one(".uos-course__summary")
    if summary is None:
        return {}
    facts: dict[str, str] = {}
    for item in summary.select(".uos-course__summary__item"):
        title_el = item.select_one(".uos-course__summary__item__title")
        if title_el is None:
            continue
        label_key = title_el.get_text(" ", strip=True).casefold()
        fact_label = _SUMMARY_LABELS.get(label_key)
        if not fact_label:
            continue
        parts = _summary_item_bodies(item)
        if not parts:
            continue
        if fact_label == "Duration":
            facts[fact_label] = parts[0]
        else:
            facts[fact_label] = ", ".join(parts)
    return facts


def _inject_key_facts(soup: BeautifulSoup) -> None:
    host = soup.select_one("main") or soup.body
    if host is None:
        return
    existing = host.select_one(f"#{SALFORD_KEY_FACTS_ID}")
    if existing:
        existing.decompose()
    facts = _facts_from_course_summary(soup)
    if not facts:
        return
    wrapper = soup.new_tag("div", id=SALFORD_KEY_FACTS_ID)
    heading = soup.new_tag("h2")
    heading.string = "Key facts"
    wrapper.append(heading)
    ul = soup.new_tag("ul")
    for label in _KEY_FACT_ORDER:
        value = facts.get(label)
        if not value:
            continue
        li = soup.new_tag("li")
        strong = soup.new_tag("strong")
        strong.string = f"{label}:"
        li.append(strong)
        li.append(f" {value}")
        ul.append(li)
    wrapper.append(ul)
    host.insert(0, wrapper)


def _expose_international_fee_tab(soup: BeautifulSoup) -> None:
    fees = soup.select_one("#fees")
    if fees is None:
        return
    for panel in fees.select("#uos-fees-home, .js-uos-home-block"):
        panel.decompose()
    for tablist in fees.select('[role="tablist"]'):
        tablist.decompose()
    for panel in fees.select("#uos-fees-international, .js-uos-international-block"):
        classes = panel.get("class") or []
        panel["class"] = [c for c in classes if c != "uos-course__price__hidden-content"]


def preprocess_course_html_uni(soup: BeautifulSoup) -> None:
    """Promote `.uos-course__summary` into parser-owned Key facts bullets."""
    _expose_international_fee_tab(soup)
    _inject_key_facts(soup)


def _drop_course_summary_section(markdown: str) -> str:
    return remove_markdown_heading_section(
        markdown,
        heading="Course summary",
        level=2,
        until_level=2,
    )


def _pick_latest_international_fee_amount(section: str) -> str | None:
    """International blocks omit Part-time; UK home blocks include it."""
    best_year = -1
    best_fee: str | None = None
    for match in _SALFORD_YEAR_FEE_BLOCK.finditer(section):
        year_label = match.group(1)
        table_body = match.group(2)
        if re.search(r"Part-time", table_body, re.I):
            continue
        fee_match = _FULL_TIME_FEE.search(table_body)
        if not fee_match:
            continue
        start_year = int(year_label.split("/")[0])
        if start_year >= best_year:
            best_year = start_year
            best_fee = fee_match.group(1).replace(",", "")
    return best_fee


def _format_gbp(amount_digits: str) -> str:
    value = int(amount_digits)
    return f"£{value:,}"


def _rewrite_salford_fees_section(section: str) -> str:
    fee_digits = _pick_latest_international_fee_amount(section)
    if not fee_digits:
        return section

    stripped = _SALFORD_YEAR_FEE_BLOCK.sub("", section)
    stripped = re.sub(r"\n{3,}", "\n\n", stripped).strip()

    fee_line = f"Annual tuition fees: | {_format_gbp(fee_digits)}"
    intl_heading = "### International students"
    if intl_heading in stripped:
        return stripped

    block = f"{intl_heading}\n\n{fee_line}\n"
    review_marker = "We review tuition fees"
    if review_marker in stripped:
        return stripped.replace(review_marker, f"{block}\n{review_marker}", 1)
    return f"{stripped}\n\n{block}"


def _drop_overview_section(markdown: str) -> str:
    """Marketing overview from #overview is not needed for Stage 1 / entry extraction."""
    return remove_markdown_heading_section(
        markdown,
        heading="Overview",
        level=2,
        until_level=2,
    )


def _drop_main_content_block(markdown: str) -> str:
    """`.uos-course__main-content` duplicates overview/modules already in COURSE_CLEAN_BLOCKS."""
    start = re.search(r"^## Main content\s*$", markdown, re.M)
    if not start:
        return markdown
    tail = markdown[start.end() :]
    entry = re.search(r"^## Entry requirements\s*$", tail, re.M)
    if entry:
        return (markdown[: start.start()] + tail[entry.start() :]).rstrip() + "\n"
    return remove_markdown_heading_section(
        markdown,
        heading="Main content",
        level=2,
        until_level=1,
    )


def _drop_duplicate_overview_through_entry(markdown: str) -> str:
    """Drop a second ## Overview … ## Entry requirements block (main-content tail)."""
    if markdown.count("## Overview") < 2 or "## Entry requirements" not in markdown:
        return markdown
    first = markdown.find("## Overview")
    second = markdown.find("## Overview", first + 1)
    entry = markdown.find("## Entry requirements", second)
    if second < 0 or entry < 0 or second >= entry:
        return markdown
    return markdown[:second].rstrip() + "\n\n" + markdown[entry:].lstrip()


def _drop_trailing_duplicate_fees(markdown: str) -> str:
    token = "## Fees and funding"
    parts = markdown.split(token)
    if len(parts) <= 2:
        return markdown
    return (token.join(parts[:2])).rstrip() + "\n"


_ENTRY_APL_TAIL = re.compile(r"\nAlternative entry requirements\b", re.I)

_ENTRY_H4_DROP = (
    "APPLICANT PROFILE",
    "PRE-ENROLLMENT ATTENDANCE",
    "INTERNATIONAL APPLICATIONS",
    "PROFESSIONAL ACCREDITATION",
)
_ENTRY_SECTION = re.compile(
    r"(## Entry requirements\s*\n)(.*?)(?=\n## |\Z)",
    re.S | re.I,
)
_ENTRY_PREAMBLE_MARKERS = re.compile(
    r"APPPLICANT\s+PROFILE|The Application and Audition Process",
    re.I,
)
_ENGLISH_H3_SECTION = re.compile(
    r"### English language requirements\s*\n+(.*?)(?=\n### |\nStandard entry|\Z)",
    re.S | re.I,
)
_ENTRY_H3_DROP_RE = re.compile(
    r"(?:^|\n)### (?:Applicant profile|International applications)\s*\n+"
    r".*?(?=\n### |\nStandard entry|\Z)",
    re.S | re.I,
)
_STANDARD_ENTRY_START = re.compile(r"Standard entry requirements\b", re.I)
_STANDARD_ENTRY_DUP = re.compile(
    r"^Standard entry requirements(?:\s+Standard entry requirements)+\s*",
    re.I | re.M,
)


def _drop_additional_costs(markdown: str) -> str:
    return remove_markdown_heading_section(
        markdown,
        heading="Additional costs",
        level=3,
        until_level=3,
    )


def _extract_english_language_requirements(body: str) -> tuple[str, str]:
    """Keep IELTS prose from HTML `### English language requirements` (in #requirement)."""
    match = _ENGLISH_H3_SECTION.search(body)
    if not match:
        return body, ""
    prose = match.group(1).strip()
    body = remove_markdown_heading_section(
        body,
        heading="English language requirements",
        level=3,
        until_level=3,
    )
    return body, prose


def _drop_entry_h3_boilerplate(body: str) -> str:
    return _ENTRY_H3_DROP_RE.sub("\n", body).strip() + "\n" if body.strip() else body


_UCAS_QUAL_BLOCK = re.compile(
    r"(?:^|\n)(UCAS [Tt]ariff(?: points)?)\s*\n+(.+?)"
    r"(?=\n(?:A-Levels|A levels|Scottish|Irish|T Levels?|BTEC|Foundation|Access|International|\n## |\Z))",
    re.S | re.I,
)
_ALEVEL_QUAL_BLOCK = re.compile(
    r"(?:^|\n)(A-Levels|A levels)\s*\n+(.+?)"
    r"(?=\n(?:Scottish|Irish|T Levels?|BTEC|Foundation|Access|International Baccalaureate|International Students|UCAS|\n## |\Z))",
    re.S | re.I,
)


def _keep_ug_ucas_and_alevels_only(body: str) -> str:
    """UG standard entry: keep UCAS tariff + A-Levels rows only (for UK-equivalent mapping)."""
    if not re.search(r"UCAS\s+[Tt]ariff", body, re.I):
        return body

    ucas_match = _UCAS_QUAL_BLOCK.search(body)
    alevel_match = _ALEVEL_QUAL_BLOCK.search(body)
    if not ucas_match and not alevel_match:
        return body

    prefix = body
    for marker in (
        r"\nStandard entry requirements\b",
        r"\nInternational student entry requirements\b",
    ):
        parts = re.split(marker, prefix, maxsplit=1, flags=re.I)
        prefix = parts[0].rstrip()

    blocks: list[str] = []
    if ucas_match:
        blocks.append(f"{ucas_match.group(1).strip()}\n\n{ucas_match.group(2).strip()}")
    if alevel_match:
        blocks.append(f"{alevel_match.group(1).strip()}\n\n{alevel_match.group(2).strip()}")

    joined = "\n\n".join(blocks) + "\n"
    return f"{prefix}\n\n{joined}" if prefix else joined


def _trim_entry_applicant_preamble(body: str) -> str:
    if not _ENTRY_PREAMBLE_MARKERS.search(body):
        return body
    match = _STANDARD_ENTRY_START.search(body)
    if not match:
        return body
    trimmed = body[match.start() :].lstrip()
    return _STANDARD_ENTRY_DUP.sub("Standard entry requirements\n\n", trimmed, count=1)


def _trim_entry_requirements(markdown: str) -> str:
    """Keep standard academic entry + IELTS; drop profile, pre-enrolment, accreditation, APL."""
    study_level = ""
    level_match = re.search(r"study_level=(\w+)", markdown)
    if level_match:
        study_level = level_match.group(1).casefold()

    def entry_replacer(match: re.Match[str]) -> str:
        heading = match.group(1)
        body = match.group(2)
        body, english_prose = _extract_english_language_requirements(body)
        body = _drop_entry_h3_boilerplate(body)
        body = _trim_entry_applicant_preamble(body)
        body = _format_entry_english_block(body)
        if english_prose and "#### ENGLISH LANGUAGE REQUIREMENTS" not in body:
            body = (
                f"#### ENGLISH LANGUAGE REQUIREMENTS\n\n{english_prose}\n\n"
                + body.lstrip()
            )
        apl = _ENTRY_APL_TAIL.search(body)
        if apl:
            body = body[: apl.start()].rstrip() + "\n"
        for h4 in _ENTRY_H4_DROP:
            body = remove_markdown_heading_section(
                body,
                heading=h4,
                level=4,
                until_level=4,
            )
        if study_level == "undergraduate":
            body = _keep_ug_ucas_and_alevels_only(body)
        return heading + body.rstrip() + "\n\n"

    return _ENTRY_SECTION.sub(entry_replacer, markdown)


def _normalize_fees_headings(markdown: str) -> str:
    return re.sub(
        r"## Fees\s*\n+## Fees and funding",
        "## Fees and funding",
        markdown,
        count=1,
    )


def _format_entry_english_block(body: str) -> str:
    """PG-style 'International students' + IELTS → #### ENGLISH LANGUAGE REQUIREMENTS."""

    def replacer(match: re.Match[str]) -> str:
        paragraph = match.group(1).strip()
        return (
            "\n\n#### ENGLISH LANGUAGE REQUIREMENTS\n\n"
            + paragraph
            + "\n"
        )

    return _ENTRY_INTL_IELTS.sub(replacer, body, count=1)


def _apply_salford_international_fees(markdown: str) -> str:
    markdown = _normalize_fees_headings(markdown)

    def replacer(match: re.Match[str]) -> str:
        heading = match.group(1)
        body = match.group(2)
        return heading + _rewrite_salford_fees_section(body)

    return _FEES_SECTION.sub(replacer, markdown)


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Salford: drop overview marketing, dedupe main content, international fees."""
    markdown = _normalize_fees_headings(markdown)
    markdown = _drop_course_summary_section(markdown)
    markdown = _drop_overview_section(markdown)
    markdown = _drop_main_content_block(markdown)
    markdown = _drop_duplicate_overview_through_entry(markdown)
    markdown = _apply_salford_international_fees(markdown)
    markdown = _drop_additional_costs(markdown)
    markdown = _drop_trailing_duplicate_fees(markdown)
    return _trim_entry_requirements(markdown)


if __name__ == "__main__":
    raise SystemExit(main())
