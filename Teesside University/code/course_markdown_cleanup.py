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

from course_markdown_cleanup import main


def _flatten_course_route_selects(soup: BeautifulSoup) -> None:
    """Turn course route dropdowns into a plain list for markdown extraction."""
    for select in soup.select("select#coursetype, select[name='website']"):
        options = [
            option.get_text(" ", strip=True)
            for option in select.find_all("option")
            if option.get_text(strip=True)
        ]
        if not options:
            continue
        ul = soup.new_tag("ul")
        for text in options:
            li = soup.new_tag("li")
            li.string = text
            ul.append(li)
        form = select.find_parent("form")
        if form is not None:
            form.replace_with(ul)
        else:
            select.replace_with(ul)


def _merge_key_info_block(soup: BeautifulSoup) -> None:
    """Merge notifications + course summary row into one extractable block."""
    notifications = soup.select_one("#notifications")
    courseinfo = soup.select_one(".row.courseinfo")
    if not notifications and not courseinfo:
        return

    wrapper = soup.new_tag("div", id="tees-key-info")
    for node in (notifications, courseinfo):
        if node is not None:
            wrapper.append(node.extract())

    coursepage = soup.select_one("#coursepage")
    if coursepage is not None:
        coursepage.insert(0, wrapper)
        return

    body = soup.body or soup
    if isinstance(body, Tag):
        body.insert(0, wrapper)


def _strip_entry_requirements_noise(soup: BeautifulSoup) -> None:
    tab = soup.select_one("#tab3")
    if tab is None:
        return
    for paragraph in tab.find_all("p"):
        text = paragraph.get_text(" ", strip=True)
        if re.search(r"Clearing \d{4} entry requirements", text, re.I):
            paragraph.decompose()


def _extract_fees_block(soup: BeautifulSoup) -> None:
    """Keep the on-campus full-time fee column without apply/part-time noise."""
    column = soup.select_one("#courseinfopdf .six.columns.col.item.alpha")
    if column is None:
        return

    fees = BeautifulSoup(str(column), "html.parser").find(True)
    if fees is None:
        return

    for selector in (".hide", "#apply", "p.text_center.bottom", "li.offer"):
        for node in fees.select(selector):
            node.decompose()

    for paragraph in list(fees.find_all("p")):
        strong = paragraph.find("strong")
        if strong and "Fee for UK applicants" in strong.get_text(" ", strip=True):
            next_sibling = paragraph.find_next_sibling("p")
            paragraph.decompose()
            if (
                next_sibling
                and next_sibling.find("a")
                and "fees.cfm" in next_sibling.find("a").get("href", "")
            ):
                next_sibling.decompose()

    wrapper = soup.new_tag("div", id="tees-fees")
    wrapper.append(fees)
    coursepage = soup.select_one("#coursepage")
    if coursepage is not None:
        coursepage.append(wrapper)


def preprocess_course_html_uni(soup: BeautifulSoup) -> None:
    """Prepare Teesside course HTML before generic block extraction."""
    _flatten_course_route_selects(soup)
    _merge_key_info_block(soup)
    _strip_entry_requirements_noise(soup)
    _extract_fees_block(soup)


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Strip Teesside marketing sections that survive generic block extraction."""
    for heading in (
        "Course page",
        "Course overview",
        "Course details",
        "Employability",
        "Information for international applicants",
        "Header summary",
    ):
        markdown = re.sub(
            rf"^## {re.escape(heading)}\s*\n+.*?(?=^## |\Z)",
            "",
            markdown,
            flags=re.M | re.S,
        )

    markdown = re.sub(
        r"(?m)^For Clearing \d{4} entry requirements[^\n]*\n+",
        "",
        markdown,
    )
    markdown = re.sub(
        r"(?m)^\[Download pdf\]\([^\)]*\)\s*\n+\[Order prospectus\]\([^\)]*\)\s*\n+",
        "",
        markdown,
    )
    markdown = re.sub(
        r"(?m)^\[Find out more about our disability services\]\([^\)]*\)\s*\n+"
        r"\[Find out more about financial support\]\([^\)]*\)\s*\n+"
        r"\[Find out more about our course related costs\]\([^\)]*\)\s*\n+",
        "",
        markdown,
    )
    entry_pos = markdown.find("## Entry requirements")
    if entry_pos >= 0:
        tail_pos = markdown.rfind("\n# ", entry_pos)
        if tail_pos > entry_pos:
            markdown = markdown[:tail_pos].rstrip() + "\n"

    return markdown


if __name__ == "__main__":
    raise SystemExit(main())
