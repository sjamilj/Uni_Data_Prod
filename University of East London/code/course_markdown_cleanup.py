"""University of East London — keep international full-time options + intakes."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, Tag

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import main
from llm_extract import ExtractionPathConfig, Stage1MarkdownParser

_MONTH_YEAR_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+((?:19|20)\d{2})\b",
    re.I,
)
_FEE_RE = re.compile(r"£\s*([\d,]+)")
_DURATION_RE = re.compile(r"Full time,?\s*([^\n|,]+)", re.I)


def _item_label(item: Tag) -> str:
    hidden = item.select_one(".visually-hidden-text")
    return (hidden.get_text(" ", strip=True) if hidden else item.get_text(" ", strip=True)).lower()


def _is_international_full_time(item: Tag) -> bool:
    label = _item_label(item)
    if "international applicant" not in label:
        return False
    if "part time" in label or "part-time" in label:
        return False
    return "full time" in label or "full-time" in label


def _collect_intakes(soup: BeautifulSoup) -> list[str]:
    seen: list[str] = []
    for node in soup.select(".course-options__btn, select.wrapper-dropdown-module option"):
        text = node.get_text(" ", strip=True)
        match = _MONTH_YEAR_RE.search(text)
        if not match:
            continue
        value = f"{match.group(1).title()} {match.group(2)}"
        if value not in seen:
            seen.append(value)
    return seen


def _first_year_fee(fee_text: str) -> str:
    amounts = [int(raw.replace(",", "")) for raw in _FEE_RE.findall(fee_text or "")]
    if not amounts:
        return ""
    year1 = re.search(r"Year\s*1:\s*£\s*([\d,]+)", fee_text or "", re.I)
    if year1:
        return year1.group(1).replace(",", "")
    return str(max(amounts))


def _duration_from_item(item: Tag) -> str:
    year = item.select_one(".attendance-type-yr")
    raw = year.get_text(" ", strip=True) if year else ""
    if not raw:
        match = _DURATION_RE.search(item.get_text(" ", strip=True))
        raw = match.group(1).strip() if match else ""
    raw = re.sub(r"\s+", " ", raw).strip(" ,")
    if not raw:
        return "full-time"
    if re.search(r"full[\s-]?time", raw, re.I):
        return raw
    return f"{raw} full-time"


def preprocess_course_html_uni(soup: BeautifulSoup) -> None:
    """Keep title, start-date buttons, and international full-time option cards."""
    items = [
        item
        for item in soup.select(".course-option-details__list-item")
        if _is_international_full_time(item)
    ]
    preferred = [
        item
        for item in items
        if "placement" not in _item_label(item)
    ]
    keep = preferred or items
    if not keep:
        return

    intakes = _collect_intakes(soup)
    title_node = soup.select_one("h1")
    title = title_node.get_text(" ", strip=True) if title_node else ""
    duration = _duration_from_item(keep[0])
    fee_node = keep[0].select_one(".fee-type")
    fee = _first_year_fee(fee_node.get_text(" ", strip=True) if fee_node else "")
    award = ExtractionPathConfig.infer_degree_name(title) if title else ""

    facts = soup.new_tag("div")
    facts["id"] = "uel-clean-facts"
    ul = soup.new_tag("ul")
    if intakes:
        li = soup.new_tag("li")
        strong = soup.new_tag("strong")
        strong.string = "Start date:"
        li.append(strong)
        li.append(" " + ", ".join(intakes))
        ul.append(li)
    if duration:
        li = soup.new_tag("li")
        strong = soup.new_tag("strong")
        strong.string = "Duration:"
        li.append(strong)
        li.append(" " + duration)
        ul.append(li)
    if award:
        li = soup.new_tag("li")
        li.string = f"Award {award}"
        ul.append(li)
    facts.append(ul)
    if fee:
        heading = soup.new_tag("h3")
        heading.string = "International students"
        facts.append(heading)
        para = soup.new_tag("p")
        para.string = f"Annual tuition fees: | £{int(fee):,}"
        facts.append(para)

    host = soup.select_one("main") or soup.body
    if host is None:
        return
    host.clear()
    if title_node is not None:
        host.append(BeautifulSoup(str(title_node), "html.parser").find(True))
    host.append(facts)


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Force Stage 1 shapes; drop leftover Home / part-time / apply chrome."""
    title = ""
    for line in markdown.splitlines():
        if re.match(r"^# [^#]", line):
            title = line.strip()
            break
    course_name = title[2:].strip() if title.startswith("# ") else ""
    award = ExtractionPathConfig.infer_degree_name(course_name)

    intakes = Stage1MarkdownParser.normalize_intake_text(
        ", ".join(f"{month} {year}" for month, year in _MONTH_YEAR_RE.findall(markdown))
    )
    duration_match = re.search(r"\*\*Duration:\*\*\s*(.+)", markdown, re.I)
    duration = duration_match.group(1).strip() if duration_match else ""
    if not duration:
        dur = _DURATION_RE.search(markdown)
        if dur:
            duration = dur.group(1).strip()
            if duration and not re.search(r"full[\s-]?time", duration, re.I):
                duration = f"{duration} full-time"
    fee_match = re.search(
        r"(?:Annual tuition fees|First year tuition fee):\s*\|\s*£([\d,]+)",
        markdown,
        re.I,
    )
    fee = fee_match.group(1).replace(",", "") if fee_match else _first_year_fee(markdown)

    lines = [title or f"# {course_name}".strip(), ""]
    if intakes:
        lines.append(f"- **Start date:** {intakes}")
    if duration:
        lines.append(f"- **Duration:** {duration}")
    if award:
        lines.append(f"- Award {award}")
    if fee:
        lines.extend(
            [
                "",
                "### International students",
                "",
                f"Annual tuition fees: | £{int(fee):,}",
            ]
        )
    return "\n".join(line for line in lines if line is not None).strip() + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
