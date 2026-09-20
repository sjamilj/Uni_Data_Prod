"""University of West London — course HTML preprocess + markdown cleanup."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import main, remove_markdown_heading_section
from normalize_admission_data import derive_hsc_gpa_from_uk_entry_text

UWL_KEY_FACTS_ID = "uwl-course-key-facts"
UWL_UK_ENTRY_ID = "uwl-uk-entry-requirements"
_KEY_FACT_ORDER = ("Duration", "Start date", "Annual tuition fees", "UCAS code")

_ENTRY_SECTION = re.compile(
    r"(## Entry requirements\s*\n)(.*?)(?=\n## |\Z)",
    re.S | re.I,
)
_UK_ENTRY_SECTION = re.compile(
    r"(## UK entry requirements\s*\n)(.*?)(?=\n## |\Z)",
    re.S | re.I,
)
_UCAS_POINTS_HEADLINE = re.compile(
    r"^(\d{2,3})(?:\s*[-–]\s*(\d{2,3}))?\s*\n+\s*UCAS\s+points\s+required",
    re.I | re.M,
)
_FEES_SECTION = re.compile(
    r"(## Fees (?:&|and) funding\s*\n)(.*?)(?=\n## |\Z)",
    re.S | re.I,
)
_TAB_LABEL_LINE = re.compile(
    r"^- (?:Requirements|Funding): International\s*\n",
    re.I | re.M,
)
_PER_YEAR_FEE = re.compile(
    r"£([\d,]+)\s*(?:\n+|\s+)per year",
    re.I,
)
_IELTS_ENTRY_PROSE = re.compile(
    r"(You need to meet our English language requirement[^\n]+(?:\n[^\n#]+)*)",
    re.I,
)
_FOUNDATION_PROMO = re.compile(
    r"Looking for .+?Foundation Year\?.*?(?=\n\n|\Z)",
    re.S | re.I,
)


def _clone_node(soup: BeautifulSoup, node) -> BeautifulSoup | None:
    if node is None:
        return None
    fragment = BeautifulSoup(str(node), "html.parser")
    return fragment.find() or fragment


def _inject_uk_entry_requirements(soup: BeautifulSoup) -> None:
    panel = soup.select_one("#t-requirements-1")
    if panel is None:
        return
    label = panel.select_one(".course-information__label")
    info = panel.select_one(".entry-requirements__general-information")
    if label is None and info is None:
        return
    existing = soup.select_one(f"#{UWL_UK_ENTRY_ID}")
    if existing is not None:
        existing.decompose()
    wrapper = soup.new_tag("div", id=UWL_UK_ENTRY_ID)
    heading = soup.new_tag("h2")
    heading.string = "UK entry requirements"
    wrapper.append(heading)
    label_clone = _clone_node(soup, label)
    if label_clone is not None:
        wrapper.append(label_clone)
    info_clone = _clone_node(soup, info)
    if info_clone is not None:
        wrapper.append(info_clone)
    anchor = soup.select_one(f"#{UWL_KEY_FACTS_ID}")
    if anchor is not None:
        anchor.insert_after(wrapper)
    else:
        host = soup.select_one("#entry-and-fees") or soup.select_one("main")
        if host is not None:
            host.insert_before(wrapper)


def _decompose_uk_tabs(soup: BeautifulSoup) -> None:
    for panel_id in ("t-funding-1", "t-requirements-1"):
        panel = soup.select_one(f"#{panel_id}")
        if panel is not None:
            panel.decompose()
    for tab_id in ("t-funding-1-label", "t-requirements-1-label"):
        tab = soup.select_one(f"#{tab_id}")
        if tab is not None:
            li = tab.find_parent("li")
            if li is not None:
                li.decompose()


def _drop_foundation_year_promos(soup: BeautifulSoup) -> None:
    for node in soup.select(".info-panel, a.btn-primary"):
        text = node.get_text(" ", strip=True)
        if "Foundation Year" in text and "View Foundation Year" in text:
            node.decompose()


def _fee_from_nationality_select(soup: BeautifulSoup) -> str | None:
    for select in soup.select(
        "#nationality_pricing_input_mobile, select[id*='nationality_pricing']"
    ):
        for option in select.find_all("option"):
            label = option.get_text(" ", strip=True)
            if "International" not in label:
                continue
            match = re.search(r"£([\d,]+)", label)
            if match:
                return f"£{match.group(1)}"
    return None


def _duration_from_page(soup: BeautifulSoup) -> str | None:
    duration_input = soup.select_one("#duration")
    if duration_input is not None:
        value = (duration_input.get("value") or "").strip()
        if value:
            return value
    for label in soup.select('label[for^="possibleStudyOptionsDurations"]'):
        text = label.get_text(" ", strip=True)
        if "Full-time" not in text:
            continue
        match = re.search(r"Duration:\s*(.+)$", text, re.I)
        if match:
            return match.group(1).strip()
    return None


def _start_dates_from_page(soup: BeautifulSoup) -> str | None:
    select = soup.select_one("#startYearMonthSelect")
    if select is None:
        return None
    dates = [opt.get_text(strip=True) for opt in select.find_all("option") if opt.get_text(strip=True)]
    return ", ".join(dates) if dates else None


def _ucas_from_page(soup: BeautifulSoup) -> str | None:
    ucas = soup.select_one("#ucasCode")
    if ucas is None:
        return None
    code = (ucas.get("value") or ucas.get("placeholder") or "").strip()
    return code or None


def _facts_from_header(soup: BeautifulSoup) -> dict[str, str]:
    facts: dict[str, str] = {}
    duration = _duration_from_page(soup)
    if duration:
        facts["Duration"] = duration
    starts = _start_dates_from_page(soup)
    if starts:
        facts["Start date"] = starts
    fee = _fee_from_nationality_select(soup)
    if fee:
        facts["Annual tuition fees"] = fee
    ucas = _ucas_from_page(soup)
    if ucas:
        facts["UCAS code"] = ucas
    return facts


def _inject_key_facts(soup: BeautifulSoup) -> None:
    anchor = soup.select_one("#entry-and-fees")
    if anchor is None:
        anchor = soup.select_one("main") or soup.body
    if anchor is None:
        return
    existing = soup.select_one(f"#{UWL_KEY_FACTS_ID}")
    if existing is not None:
        existing.decompose()
    facts = _facts_from_header(soup)
    if not facts:
        return
    wrapper = soup.new_tag("div", id=UWL_KEY_FACTS_ID)
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
    if anchor.get("id") == "entry-and-fees":
        anchor.insert_before(wrapper)
    else:
        anchor.insert(0, wrapper)


def preprocess_course_html_uni(soup: BeautifulSoup) -> None:
    """UK + international entry, international fees, key facts for Stage 1 parser."""
    _inject_key_facts(soup)
    _inject_uk_entry_requirements(soup)
    _decompose_uk_tabs(soup)
    _drop_foundation_year_promos(soup)


def _inject_fee_table_line(body: str) -> str:
    if "Annual tuition fees:" in body:
        return body
    match = _PER_YEAR_FEE.search(body)
    if not match:
        return body
    amount = match.group(1)
    block = f"### International students\n\nAnnual tuition fees: | £{amount}\n\n"
    return block + body


def _normalize_ucas_headline(body: str) -> str:
    def repl(match: re.Match[str]) -> str:
        low, high = match.group(1), match.group(2)
        if high:
            points = f"{low}–{high}"
        else:
            points = low
        return f"{points} UCAS Tariff points required\nfrom level 3 qualifications"

    body = _UCAS_POINTS_HEADLINE.sub(repl, body)
    body = re.sub(
        r"^(\d{2,3})(?:\s*[-–]\s*(\d{2,3}))?\s+UCAS points required",
        lambda m: (
            f"{m.group(1)}–{m.group(2)} UCAS Tariff points required"
            if m.group(2)
            else f"{m.group(1)} UCAS Tariff points required"
        ),
        body,
        flags=re.I | re.M,
    )
    return body


def _promote_uk_entry_block(body: str) -> str:
    if "#### UK ENTRY REQUIREMENTS" in body:
        return body
    body = _normalize_ucas_headline(body)
    body = re.sub(
        r"^- Requirements: UK\s*\n+",
        "",
        body,
        flags=re.I | re.M,
    )
    body = body.strip()
    if not body:
        return body
    hsc_equiv = derive_hsc_gpa_from_uk_entry_text(body)
    if not hsc_equiv:
        points = re.search(r"(\d{2,3})(?:\s*[-–]\s*(\d{2,3}))?\s+UCAS", body, re.I)
        if points:
            tariff = points.group(1)
            if points.group(2):
                tariff = points.group(2)
            hsc_equiv = derive_hsc_gpa_from_uk_entry_text(
                f"{tariff} UCAS Tariff points required"
            )
    if hsc_equiv and hsc_equiv not in body:
        body = f"{body}\n\nBangladesh HSC equivalent (from UK entry): {hsc_equiv}"
    return f"#### UK ENTRY REQUIREMENTS\n\n{body}\n\n"


def _trim_uk_entry_requirements(markdown: str) -> str:
    def replacer(match: re.Match[str]) -> str:
        heading = match.group(1)
        body = match.group(2)
        body = _FOUNDATION_PROMO.sub("", body)
        body = _promote_uk_entry_block(body)
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        return heading + body + "\n\n"

    return _UK_ENTRY_SECTION.sub(replacer, markdown)


def _promote_ielts_block(body: str) -> str:
    if "#### ENGLISH LANGUAGE REQUIREMENTS" in body:
        return body
    match = _IELTS_ENTRY_PROSE.search(body)
    if not match:
        return body
    prose = match.group(1).strip()
    body = body.replace(prose, "").strip()
    return f"#### ENGLISH LANGUAGE REQUIREMENTS\n\n{prose}\n\n{body}".strip() + "\n\n"


def _trim_fees_section(markdown: str) -> str:
    def replacer(match: re.Match[str]) -> str:
        heading = match.group(1)
        body = match.group(2)
        body = _TAB_LABEL_LINE.sub("", body)
        body = _inject_fee_table_line(body)
        body = re.sub(
            r"^£[\d,]+\s+per year[^\n]*\n+",
            "",
            body,
            flags=re.I | re.M,
        )
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        return heading + body + "\n\n"

    return _FEES_SECTION.sub(replacer, markdown)


def _trim_entry_requirements(markdown: str) -> str:
    def replacer(match: re.Match[str]) -> str:
        heading = match.group(1)
        body = match.group(2)
        body = _TAB_LABEL_LINE.sub("", body)
        body = _FOUNDATION_PROMO.sub("", body)
        body = re.sub(
            r"^\d+\.\d+\s+IELTS or above\s*\n+",
            "",
            body,
            flags=re.I | re.M,
        )
        body = _promote_ielts_block(body)
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        return heading + body + "\n\n"

    return _ENTRY_SECTION.sub(replacer, markdown)


def _drop_overview(markdown: str) -> str:
    return remove_markdown_heading_section(
        markdown,
        heading="Overview",
        level=2,
        until_level=2,
    )


def cleanup_course_markdown_uni(markdown: str) -> str:
    markdown = _drop_overview(markdown)
    markdown = _trim_uk_entry_requirements(markdown)
    markdown = _trim_entry_requirements(markdown)
    markdown = _trim_fees_section(markdown)
    return markdown


if __name__ == "__main__":
    raise SystemExit(main())
