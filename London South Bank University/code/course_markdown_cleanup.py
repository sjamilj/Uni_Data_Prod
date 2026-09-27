"""LSBU course HTML preprocess + markdown cleanup for Stage 1 parser fields."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, Tag

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import EnvFileLoader, main, remove_markdown_heading_section

_CODE_DIR = Path(__file__).resolve().parent
LSBU_KEY_FACTS_ID = "lsbu-course-key-facts"
LSBU_ENTRY_BLOCK_ID = "lsbu-course-entry-requirements"
LSBU_PARSER_FEES_ID = "lsbu-parser-international-fees"
_KEY_FACT_ORDER = ("Start date", "Duration", "Study mode", "UCAS code")

_MONTH_ONLY_RE = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|November|December)$",
    re.I,
)
_GBP_AMOUNT_RE = re.compile(r"£\s*([\d,]+)")
_FEES_SECTION = re.compile(
    r"(## Fees\s*\n|## Fees and funding\s*\n)(.*?)(?=\n## |\Z)",
    re.S | re.I,
)
_INTL_FEE_CARD_MD = re.compile(
    r"(?:^|\n)#+\s*International\s*\n+\s*£([\d,]+)",
    re.I | re.M,
)
_FEES_BOILERPLATE_START = re.compile(
    r"\n### Possible fee changes\b",
    re.I,
)


def _default_intake_year() -> str:
    env = EnvFileLoader.load_from_code_dir(_CODE_DIR)
    return (env.get("COURSE_DEFAULT_INTAKE_YEAR") or "2026").strip() or "2026"


def _entry_country_slug() -> str:
    env = EnvFileLoader.load_from_code_dir(_CODE_DIR)
    return (env.get("LSBU_ENTRY_COUNTRY_SLUG") or "bangladesh").strip().casefold() or "bangladesh"


def _expand_start_date(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if re.search(r"\b(19|20)\d{2}\b", text):
        return text
    if _MONTH_ONLY_RE.match(text):
        return f"{text.title()} {_default_intake_year()}"
    return text


def _normalize_gbp_display(amount: str) -> str:
    digits = amount.replace(",", "").strip()
    if not digits.isdigit():
        return amount.strip()
    return f"£{int(digits):,}"


def _facts_from_hero_icons(soup: BeautifulSoup) -> dict[str, str]:
    facts: dict[str, str] = {}
    for component in soup.select(".hero-banner-courses__icon-components .icon-component"):
        header_el = component.select_one(".icon-component__header")
        desc_el = component.select_one(".icon-component__description")
        if header_el is None or desc_el is None:
            continue
        header = header_el.get_text(" ", strip=True).casefold()
        value = desc_el.get_text(" ", strip=True)
        if not value:
            continue
        if header == "duration":
            facts["Duration"] = value
        elif header == "start date":
            facts["Start date"] = _expand_start_date(value)
        elif header == "study":
            facts["Study mode"] = value
        elif header == "ucas code":
            facts["UCAS code"] = value
    return facts


def _apply_table_mode_score(mode: str) -> int:
    text = mode.casefold()
    if text == "full-time":
        return 100
    if "full-time" in text and "sandwich" not in text and "part-time" not in text:
        return 50
    if "full-time" in text:
        return 10
    return -1


def _delivery_table_cell_value(cell: Tag) -> str:
    """LSBU overview/apply tables duplicate header labels in mobile-only spans."""
    for span in cell.select("span"):
        classes = " ".join(span.get("class") or [])
        if "hide_desktop" in classes or "show_mobile" in classes:
            continue
        text = span.get_text(" ", strip=True)
        if text:
            return text
    return cell.get_text(" ", strip=True)


def _facts_from_delivery_table(table: Tag) -> dict[str, str]:
    """Mode | Duration | Start date | Application code (full-time row preferred)."""
    rows: list[list[str]] = []
    for tr in table.select("tr"):
        cells = [
            _delivery_table_cell_value(cell) if cell.name == "td" else cell.get_text(" ", strip=True)
            for cell in tr.find_all(["th", "td"])
        ]
        if cells:
            rows.append(cells)
    if len(rows) < 2:
        return {}
    headers = [cell.casefold() for cell in rows[0]]
    try:
        mode_i = headers.index("mode")
        duration_i = headers.index("duration")
        start_i = headers.index("start date")
        code_i = headers.index("application code")
    except ValueError:
        return {}

    best_row: list[str] | None = None
    best_score = -1
    for row in rows[1:]:
        if len(row) <= max(mode_i, duration_i, start_i, code_i):
            continue
        score = _apply_table_mode_score(row[mode_i])
        if score > best_score:
            best_score = score
            best_row = row
    if best_row is None or best_score < 0:
        return {}

    mode_label = best_row[mode_i]
    study_mode = "Full-time" if "full-time" in mode_label.casefold() else mode_label
    return {
        "Duration": best_row[duration_i],
        "Start date": _expand_start_date(best_row[start_i]),
        "Study mode": study_mode,
        "UCAS code": best_row[code_i],
    }


def _facts_from_apply_delivery_table(soup: BeautifulSoup) -> dict[str, str]:
    """Apply tab delivery table."""
    table = soup.select_one("table.apply__table")
    if table is None:
        return {}
    return _facts_from_delivery_table(table)


def _facts_from_overview_course_info_table(soup: BeautifulSoup) -> dict[str, str]:
    """Overview tab: table.overview_course_info_table (top-up / some PG courses)."""
    table = soup.select_one("table.overview_course_info_table")
    if table is None:
        return {}
    return _facts_from_delivery_table(table)


def _merge_key_facts(hero: dict[str, str], table: dict[str, str]) -> dict[str, str]:
    merged = dict(hero)
    for key in ("Duration", "Start date", "Study mode", "UCAS code"):
        value = table.get(key)
        if value:
            merged[key] = value
    return merged


def _international_fee_amount(soup: BeautifulSoup) -> str:
    for card in soup.select(".fees__card"):
        title = card.select_one(".fees__card-header-title")
        if title is None or "international" not in title.get_text(" ", strip=True).casefold():
            continue
        subtitle = card.select_one(".fees__card-subtitle")
        if subtitle is None:
            continue
        match = _GBP_AMOUNT_RE.search(subtitle.get_text(" ", strip=True))
        if match:
            return match.group(1).replace(",", "")
    return ""


def _inject_key_facts(soup: BeautifulSoup) -> None:
    host = soup.select_one("main") or soup.body
    if host is None:
        return
    existing = host.select_one(f"#{LSBU_KEY_FACTS_ID}")
    if existing:
        existing.decompose()
    facts = _merge_key_facts(_facts_from_hero_icons(soup), {})
    facts = _merge_key_facts(facts, _facts_from_overview_course_info_table(soup))
    facts = _merge_key_facts(facts, _facts_from_apply_delivery_table(soup))
    if not facts:
        return
    wrapper = soup.new_tag("div", id=LSBU_KEY_FACTS_ID)
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


def _inject_international_fee_block(soup: BeautifulSoup) -> None:
    amount = _international_fee_amount(soup)
    if not amount:
        return
    fees_root = soup.select_one("#fees")
    if fees_root is None:
        return
    existing = fees_root.select_one(f"#{LSBU_PARSER_FEES_ID}")
    if existing:
        existing.decompose()
    block = soup.new_tag("div", id=LSBU_PARSER_FEES_ID)
    heading = soup.new_tag("h3")
    heading.string = "International students"
    block.append(heading)
    paragraph = soup.new_tag("p")
    paragraph.string = f"Annual tuition fees: | {_normalize_gbp_display(amount)}"
    block.append(paragraph)
    fees_root.insert(0, block)


def _trim_fees_tab_to_international_only(soup: BeautifulSoup) -> None:
    fees_root = soup.select_one("#fees")
    if fees_root is None:
        return
    parser = fees_root.select_one(f"#{LSBU_PARSER_FEES_ID}")
    if parser is None:
        return
    for child in list(fees_root.children):
        if isinstance(child, Tag) and child.get("id") == LSBU_PARSER_FEES_ID:
            continue
        if isinstance(child, Tag):
            child.decompose()


def _strip_non_entry_blocks(soup: BeautifulSoup) -> None:
    for selector in ("#overview", "#course-content"):
        node = soup.select_one(selector)
        if node is not None:
            node.decompose()


def _append_cloned_children(wrapper: Tag, source: Tag) -> None:
    for child in list(source.children):
        if isinstance(child, Tag):
            wrapper.append(child.extract())
        elif str(child).strip():
            wrapper.append(str(child))


def _entry_source_paragraphs(source: Tag) -> list[str]:
    """Plain paragraphs for markdown; avoids broken nested lists from tab clones."""
    paragraphs: list[str] = []
    for li in source.select("li"):
        text = li.get_text(" ", strip=True)
        if text and len(text) > 15:
            paragraphs.append(text)
    if paragraphs:
        return paragraphs
    text = source.get_text(" ", strip=True)
    return [text] if text else []


def _is_country_picker_text(text: str) -> bool:
    lowered = (text or "").casefold()
    return lowered.startswith("choose your country") or "choose your country choose your country" in lowered


def _prune_entry_noise(root: Tag) -> None:
    for node in root.select(
        ".dropdown-select, .advanced-entry, script, "
        ".countries-list-container, .select-country-controls, .component-description"
    ):
        node.decompose()
    for heading in root.find_all(["h2", "h3", "h4"]):
        text = heading.get_text(" ", strip=True).casefold()
        if "missing english and maths" in text:
            section = heading.find_parent("div") or heading
            section.decompose()


def _course_entry_content_box(entry: Tag) -> Tag | None:
    """Course-specific entry copy on the v2 Entry Level Requirements tab set."""
    uk_panel = entry.select_one('[data-sq-field="ukQualificationsTab.content"]')
    if uk_panel is None:
        uk_panel = entry.select_one("#tab-0")
    if uk_panel is None:
        return None
    return uk_panel.select_one(".tab-content-box") or uk_panel


def _append_entry_subsection(
    wrapper: Tag, soup: BeautifulSoup, title: str, source: Tag | None
) -> None:
    if source is None:
        return
    paragraphs = [
        text
        for text in _entry_source_paragraphs(source)
        if text and not _is_country_picker_text(text)
    ]
    if not paragraphs:
        return
    sub = soup.new_tag("h3")
    sub.string = title
    wrapper.append(sub)
    for text in paragraphs:
        paragraph = soup.new_tag("p")
        paragraph.string = text
        wrapper.append(paragraph)


def _inject_entry_level_requirements(
    soup: BeautifulSoup, entry: Tag, wrapper: Tag
) -> None:
    """V2 pages put course-specific copy on the UK Qualifications tab."""
    course_box = _course_entry_content_box(entry)
    _append_entry_subsection(
        wrapper, soup, "International Qualifications", course_box
    )


def _inject_entry_requirements_block(soup: BeautifulSoup) -> None:
    """Flatten entry tabs + JS-filled country content for markdown export."""
    entry = soup.select_one("#entry-requirements") or soup.select_one(
        "#entry-level-requirements"
    )
    if entry is None:
        return
    existing = soup.select_one(f"#{LSBU_ENTRY_BLOCK_ID}")
    if existing:
        existing.decompose()

    is_level_v2 = entry.get("id") == "entry-level-requirements"
    country_content = soup.select_one("#er-country-content")
    uk_panel = soup.select_one("#entry-requirements_first")
    _prune_entry_noise(entry)

    wrapper = soup.new_tag("div", id=LSBU_ENTRY_BLOCK_ID)
    heading = soup.new_tag("h2")
    heading.string = "Entry requirements"
    wrapper.append(heading)

    if is_level_v2:
        _inject_entry_level_requirements(soup, entry, wrapper)
    else:
        if country_content and country_content.get_text(" ", strip=True):
            _append_entry_subsection(
                wrapper, soup, "International Qualifications", country_content
            )
        if uk_panel and uk_panel.get_text(" ", strip=True):
            _append_entry_subsection(
                wrapper, soup, "UK entry requirements", uk_panel
            )

    if len(wrapper.contents) <= 1:
        _append_cloned_children(wrapper, entry)

    entry.decompose()
    anchor = soup.select_one("#fees") or soup.select_one("main") or soup.body
    if anchor is not None:
        anchor.insert_before(wrapper)


def prepare_course_page_for_download(page) -> None:
    """Load Bangladesh (or LSBU_ENTRY_COUNTRY_SLUG) international entry via the on-page dropdown."""
    country_slug = _entry_country_slug()
    try:
        page.locator("#entry-level-requirements").scroll_into_view_if_needed(timeout=8000)
        page.locator('button[data-tab="tab-1"]').click(timeout=4000)
        page.locator(".country-item").filter(
            has_text=re.compile(r"bangladesh", re.I)
        ).locator(".country-link").first.click(timeout=5000)
        page.wait_for_function(
            "() => { const open = document.querySelector("
            "'.country-item .country-content:not(.hidden)'); "
            "return open && open.innerText.trim().length > 80; }",
            timeout=15000,
        )
    except Exception:
        pass
    for selector in ("#label_entry-requirements", "a[aria-controls='entry-requirements']"):
        try:
            page.locator(selector).first.click(timeout=4000)
            break
        except Exception:
            continue
    try:
        page.locator("#label_entry-requirements_second").click(timeout=4000)
    except Exception:
        pass
    try:
        page.locator(
            f".dropdown-select__menu-item[data-url*='{country_slug}']"
        ).first.click(timeout=5000)
        page.locator("#er-button").click(timeout=5000)
        page.wait_for_function(
            "() => { const el = document.querySelector('#er-country-content'); "
            "return el && el.innerText.trim().length > 60; }",
            timeout=20000,
        )
    except Exception:
        pass


def preprocess_course_html_uni(soup: BeautifulSoup) -> None:
    """Promote hero icons + international fees card into parser-owned shapes."""
    _strip_non_entry_blocks(soup)
    _inject_key_facts(soup)
    _inject_entry_requirements_block(soup)
    _inject_international_fee_block(soup)
    _trim_fees_tab_to_international_only(soup)


def _pick_international_fee_from_markdown(markdown: str) -> str | None:
    match = _INTL_FEE_CARD_MD.search(markdown)
    if match:
        return match.group(1).replace(",", "")
    for line in markdown.splitlines():
        fee_match = _GBP_AMOUNT_RE.search(line)
        if fee_match and "international" in line.casefold():
            return fee_match.group(1).replace(",", "")
    return None


def _slim_fees_section(section: str) -> str:
    """Keep only Stage-1 international fee line; drop UK cards, tables, scholarships."""
    amount = _pick_international_fee_from_markdown(section)
    if not amount:
        trimmed = _FEES_BOILERPLATE_START.split(section, maxsplit=1)[0].rstrip()
        return trimmed + "\n" if trimmed else section
    intl_heading = "### International students"
    fee_line = f"Annual tuition fees: | {_normalize_gbp_display(amount)}"
    return f"{intl_heading}\n\n{fee_line}\n"


def _drop_uk_fee_blocks(section: str) -> str:
    return re.sub(
        r"(?:^|\n)#{3,5}\s*United Kingdom\s*\n+£[\d,]+\s*\n+Tuition fees for home students\s*",
        "\n",
        section,
        flags=re.I,
    )


def _inject_key_facts_from_hero_markdown(markdown: str) -> str:
    if re.search(r"-\s*\*\*Start date:\*\*", markdown, re.I):
        return markdown
    facts: dict[str, str] = {}
    for header, description in re.findall(
        r"icon-component__header[^>]*>\s*([^<]+?)\s*</div>\s*"
        r"<div[^>]*icon-component__description[^>]*>\s*([^<]+?)\s*</div>",
        markdown,
        re.I | re.S,
    ):
        key = header.strip().casefold()
        value = description.strip()
        if key == "duration":
            facts["Duration"] = value
        elif key == "start date":
            facts["Start date"] = _expand_start_date(value)
        elif key == "study":
            facts["Study mode"] = value
        elif key in {"ucas points", "ucas code"}:
            facts["UCAS code"] = value
    if not facts:
        return markdown

    bullets = []
    for label in _KEY_FACT_ORDER:
        value = facts.get(label)
        if value:
            bullets.append(f"- **{label}:** {value}")
    if not bullets:
        return markdown
    block = "## Key facts\n\n" + "\n".join(bullets) + "\n\n"
    if "## Key facts" in markdown:
        return markdown
    h1 = re.search(r"^#\s+.+\n", markdown, re.M)
    if h1:
        insert_at = h1.end()
        return markdown[:insert_at] + "\n" + block + markdown[insert_at:].lstrip("\n")
    return block + markdown


_IELTS_AVG_RE = re.compile(
    r"IELTS average score of ([\d.]+)(?:\s+on entry into the course)?",
    re.I,
)


def _normalize_entry_ielts(markdown: str) -> str:
    return _IELTS_AVG_RE.sub(
        lambda match: (
            f"IELTS {match.group(1)} overall with no less than {match.group(1)} in each band"
        ),
        markdown,
    )


def _trim_entry_requirements(markdown: str) -> str:
    markdown = _normalize_entry_ielts(markdown)
    markdown = remove_markdown_heading_section(
        markdown,
        heading="Entry Level Requirements",
        level=2,
        until_level=2,
    )
    for heading in (
        "Choose your country",
        "Missing English and Maths qualifications?",
    ):
        markdown = remove_markdown_heading_section(
            markdown,
            heading=heading,
            level=3,
            until_level=3,
        )
    markdown = remove_markdown_heading_section(
        markdown,
        heading="Non-standard entry",
        level=2,
        until_level=2,
    )
    return markdown


def cleanup_course_markdown_uni(markdown: str) -> str:
    markdown = _inject_key_facts_from_hero_markdown(markdown)
    markdown = _trim_entry_requirements(markdown)
    markdown = remove_markdown_heading_section(
        markdown,
        heading="Overview",
        level=2,
        until_level=2,
    )
    markdown = remove_markdown_heading_section(
        markdown,
        heading="Course content",
        level=2,
        until_level=2,
    )

    def replacer(match: re.Match[str]) -> str:
        heading = match.group(1)
        body = _drop_uk_fee_blocks(match.group(2))
        return heading + _slim_fees_section(body)

    return _FEES_SECTION.sub(replacer, markdown)


if __name__ == "__main__":
    raise SystemExit(main())
