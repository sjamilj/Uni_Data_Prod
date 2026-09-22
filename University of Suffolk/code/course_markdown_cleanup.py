"""University of Suffolk — course HTML preprocess + markdown tweaks for Stage 1."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, Tag

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import main

import suffolk_alevel_mapping  # noqa: F401 — registers A-Level → HSC map for LLM stage 2

_COUNTRY_PROMPT_RE = re.compile(
    r"select your country of permanent residence",
    re.I,
)
_IELTS_PAREN_RE = re.compile(
    r"IELTS\s+([\d.]+)\s+overall\s*\(\s*minimum\s+([\d.]+)\s+in\s+all\s+components\s*\)",
    re.I,
)
_DURATION_LINE_RE = re.compile(r"(\*\*Duration:\*\*\s*)(.+)", re.I)
_PLAIN_DURATION_RE = re.compile(r"^Duration:\s*(.+)$", re.M | re.I)
_OVERVIEW_SECTION_RE = re.compile(r"\n## Overview\n.*?(?=\n## )", re.S)
_ALEVEL_IN_TYPICAL_OFFER_RE = re.compile(
    r"(?<![A-E\*])([A-E\*]{1,4})\s*\(\s*A-?Levels?\s*\)",
    re.I,
)
_BARE_ALEVEL_BULLET_RE = re.compile(
    r"^(?P<prefix>-\s+)(?P<grade>[A-E\*]{1,4})\s*$",
    re.M,
)
_ALEVEL_PAREN_BULLET_RE = re.compile(
    r"^(?P<prefix>-\s+)(?:\*\*)?(?P<grade>[A-E\*]{1,4})(?:\*\*)?\s*\(A-Level\)\s*$",
    re.M | re.I,
)


def _extract_alevel_from_typical_offer(text: str) -> str:
    normalized = re.sub(r"\s+", " ", (text or "").strip())
    match = _ALEVEL_IN_TYPICAL_OFFER_RE.search(normalized)
    return match.group(1).upper() if match else ""


def _full_time_duration(raw: str) -> str:
    text = re.sub(r"\s+", " ", (raw or "").strip())
    if not text:
        return text
    for part in re.split(r",\s*", text):
        if re.search(r"full[\s-]?time", part, re.I):
            return part.strip()
    return text.split(",")[0].strip()


def _collect_course_table_fields(tables_root: Tag | None) -> dict[str, str]:
    fields: dict[str, str] = {}
    if not tables_root:
        return fields
    for table in tables_root.select("table.course-table-container"):
        for row in table.select("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = th.get_text(" ", strip=True).rstrip(":").strip().lower()
            value = td.get_text(" ", strip=True)
            if label and value:
                fields[label] = value
    return fields


def _default_course_tables(soup: BeautifulSoup) -> Tag | None:
    block = soup.select_one(
        '.js-course-selector-content[data-year="default"] .course-selector__tables'
    )
    if block:
        return block
    return soup.select_one(".course-selector__tables")


def _international_tuition_fee(soup: BeautifulSoup) -> str:
    for body in soup.select(".stats-card__body"):
        label = body.select_one("span.h4, .h4")
        if not label:
            continue
        label_text = label.get_text(" ", strip=True).lower()
        if "international" not in label_text or "tuition" not in label_text:
            continue
        amount = body.select_one("h3.display-3, .display-3")
        if not amount:
            continue
        fee = amount.get_text(" ", strip=True)
        if fee and "£" in fee:
            return fee
    return ""


def _strip_entry_noise(section: Tag) -> None:
    for node in section.select(".entry-requirements__hidden"):
        node.decompose()
    for form in section.select("form.js-form-search"):
        form.decompose()
    for p in section.find_all("p"):
        if _COUNTRY_PROMPT_RE.search(p.get_text(" ", strip=True)):
            p.decompose()
    for item in section.select(".field-item"):
        if _COUNTRY_PROMPT_RE.search(item.get_text(" ", strip=True)):
            item.decompose()


def _insert_after(anchor: Tag | None, new_node: Tag, soup: BeautifulSoup) -> None:
    main = soup.select_one("main#content, main")
    if anchor and anchor.parent:
        anchor.insert_after(new_node)
    elif main:
        main.insert(0, new_node)


def preprocess_course_html_uni(soup: BeautifulSoup) -> None:
    """Inject Stage-1-shaped facts/fees; drop country picker noise and extra entry years."""
    for block in soup.select('.js-course-selector-content[data-year="next"]'):
        block.decompose()

    entry_sections = soup.select('section[id^="entry-requirements"]')
    for extra in entry_sections[1:]:
        extra.decompose()
    for section in soup.select('section[id^="entry-requirements"]'):
        _strip_entry_noise(section)

    for accordion in soup.select(".accordion-container"):
        accordion.decompose()

    fields = _collect_course_table_fields(_default_course_tables(soup))
    start = fields.get("start date", "")
    duration = _full_time_duration(fields.get("duration", ""))
    alevel = _extract_alevel_from_typical_offer(fields.get("typical offer", ""))

    anchor: Tag | None = soup.select_one(".course-selector")
    if start or duration or alevel:
        facts = soup.new_tag("div", id="suffolk-stage1-facts")
        heading = soup.new_tag("h2")
        heading.string = "Key course details"
        facts.append(heading)
        ul: Tag | None = None
        if start or alevel:
            ul = soup.new_tag("ul")
        if start and ul is not None:
            li = soup.new_tag("li")
            strong = soup.new_tag("strong")
            strong.string = "Start date:"
            li.append(strong)
            li.append(f" {start}")
            ul.append(li)
        if alevel and ul is not None:
            li = soup.new_tag("li")
            grade = soup.new_tag("strong")
            grade.string = alevel
            li.append(grade)
            li.append(" (A-Level)")
            ul.append(li)
        if ul is not None:
            facts.append(ul)
        if duration:
            p = soup.new_tag("p")
            p.string = f"Duration: {duration}"
            facts.append(p)
        _insert_after(anchor, facts, soup)
        anchor = facts

    fee = _international_tuition_fee(soup)
    if fee:
        fees = soup.new_tag("div", id="suffolk-international-fees")
        h2 = soup.new_tag("h2")
        h2.string = "Fees"
        fees.append(h2)
        h3 = soup.new_tag("h3")
        h3.string = "International students"
        fees.append(h3)
        p = soup.new_tag("p")
        p.string = f"Annual tuition fees: | {fee}"
        fees.append(p)
        _insert_after(anchor, fees, soup)


def cleanup_course_markdown_uni(markdown: str) -> str:
    markdown = _IELTS_PAREN_RE.sub(
        r"IELTS \1 overall with no less than \2 in each band",
        markdown,
    )

    def _duration_line(match: re.Match[str]) -> str:
        return match.group(1) + _full_time_duration(match.group(2))

    markdown = _DURATION_LINE_RE.sub(_duration_line, markdown)

    def _plain_duration(match: re.Match[str]) -> str:
        return f"**Duration:** {_full_time_duration(match.group(1))}"

    markdown = _PLAIN_DURATION_RE.sub(_plain_duration, markdown)

    def _bold_alevel_bullet(match: re.Match[str]) -> str:
        grade = match.group("grade").upper()
        return f"{match.group('prefix')}**{grade}** (A-Level)"

    markdown = _ALEVEL_PAREN_BULLET_RE.sub(_bold_alevel_bullet, markdown)
    markdown = _BARE_ALEVEL_BULLET_RE.sub(_bold_alevel_bullet, markdown)
    return _OVERVIEW_SECTION_RE.sub("\n", markdown)


if __name__ == "__main__":
    raise SystemExit(main())
