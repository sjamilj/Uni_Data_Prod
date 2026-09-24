"""University of Greenwich — keep international full-time duration, intake, fee, and UK entry text."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import main
from llm_extract import ExtractionPathConfig, Stage1MarkdownParser

_MONTHS = (
    "January|February|March|April|May|June|July|August|"
    "September|October|November|December"
)
_MONTH_YEAR_RE = re.compile(
    rf"\b({_MONTHS})\s+((?:19|20)\d{{2}})(?:/\d{{2}})?\b",
    re.I,
)
_MONTH_ONLY_RE = re.compile(rf"\b({_MONTHS})\b", re.I)
_FEE_RE = re.compile(r"£\s*([\d,]+)")
_INTL_FEE_PROSE_RE = re.compile(
    r"International(?:\s+students?)?\s+fees?\s*[-–:]\s*£\s*([\d,]+)",
    re.I,
)
_YEAR_RE = re.compile(r"\b((?:19|20)\d{2})(?:/\d{2})?\b")
_SKIP_UK_ENTRY_RE = re.compile(
    r"contact form|admissions policy|call us on|020[\s-]?8331|"
    r"read our admissions|clearing line|live chat|clearing advisors|"
    r"don.?t meet the criteria|available to overseas|"
    r"recognition of prior|prior learning|join live chat",
    re.I,
)
_UCAS_CLEARING_RE = re.compile(
    r"Typical UCAS(?: Tariff)? points for Clearing entry:\s*(\d{2,3})",
    re.I,
)
_UCAS_POINTS_RE = re.compile(r"(\d{2,3})\s*UCAS(?: Tariff)? points", re.I)
_UK_CLASS_RE = re.compile(r"\b(2\s*:\s*[12])\b", re.I)


def _is_part_time(text: str) -> bool:
    return bool(re.search(r"part[\s-]?time", text or "", re.I))


def _is_full_time(text: str) -> bool:
    return bool(re.search(r"full[\s-]?time", text or "", re.I))


def _is_sandwich(text: str) -> bool:
    return bool(re.search(r"\bsandwich\b|\bindustrial practice\b", text or "", re.I))


def _normalize_duration(raw: str) -> str:
    text = re.sub(r"\s+", " ", raw or "").strip(" ,")
    text = re.sub(r"\b1 years\b", "1 year", text, flags=re.I)
    if not text:
        return ""
    if _is_full_time(text):
        return text
    return f"{text} full-time"


def _academic_year(soup: BeautifulSoup) -> str:
    for option in soup.select("option[data-select-year]"):
        year = (option.get("data-select-year") or "").strip()
        label = option.get_text(" ", strip=True)
        if year.isdigit() and "international" in label.lower() and _is_full_time(label):
            return year
    heading = soup.select_one("#prog-fees-precis")
    if heading:
        match = _YEAR_RE.search(heading.get_text(" ", strip=True))
        if match:
            return match.group(1)
    return ""


def _collect_intakes(soup: BeautifulSoup) -> list[str]:
    seen: list[str] = []
    for option in soup.select("option"):
        label = option.get_text(" ", strip=True)
        if "international" not in label.lower():
            continue
        if _is_part_time(label) or not _is_full_time(label):
            continue
        match = _MONTH_YEAR_RE.search(label)
        if not match:
            continue
        value = f"{match.group(1).title()} {match.group(2)}"
        if value not in seen:
            seen.append(value)
    if seen:
        return seen

    start = soup.select_one("#prog-start")
    year = _academic_year(soup)
    if start is None or not year:
        return []
    for month in _MONTH_ONLY_RE.findall(start.get_text(" ", strip=True)):
        value = f"{month.title()} {year}"
        if value not in seen:
            seen.append(value)
    return seen


def _duration_from_soup(soup: BeautifulSoup) -> str:
    mode = soup.select_one("#prog-mode")
    if mode is not None:
        for item in mode.select("li"):
            text = item.get_text(" ", strip=True)
            if _is_part_time(text) or _is_sandwich(text):
                continue
            if _is_full_time(text) or re.search(r"\d+\s+year", text, re.I):
                return _normalize_duration(text)
    for option in soup.select("option"):
        label = option.get_text(" ", strip=True)
        if "international" not in label.lower() or _is_part_time(label) or _is_sandwich(label):
            continue
        if not _is_full_time(label):
            continue
        duration = (option.get("data-select-duration") or "").strip()
        if duration:
            return _normalize_duration(duration)
    return ""


def _international_fee(soup: BeautifulSoup) -> str:
    cell = soup.select_one("tr.gre-fees-intl td.gre-fees-ft")
    if cell is not None:
        match = _FEE_RE.search(cell.get_text(" ", strip=True))
        if match:
            return match.group(1).replace(",", "")
    precis = soup.select_one("#prog-fees-precis")
    if precis is not None:
        amounts = _FEE_RE.findall(precis.get_text(" ", strip=True))
        if amounts:
            return amounts[-1].replace(",", "")
    fees_root = soup.select_one(".prog-finance-text") or soup.select_one(".gre-prog-fees")
    if fees_root is None:
        return ""
    match = _INTL_FEE_PROSE_RE.search(fees_root.get_text(" ", strip=True))
    if not match:
        return ""
    return match.group(1).replace(",", "")


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _uk_entry_block(soup: BeautifulSoup):
    for selector in (
        ".entry-req-uk",
        ".prog-entry-req",
        ".prog-entry-requirements",
    ):
        block = soup.select_one(selector)
        if block is not None:
            return block
    return None


def _uk_entry_paragraphs(soup: BeautifulSoup) -> list[str]:
    block = _uk_entry_block(soup)
    if block is None:
        return []
    paragraphs: list[str] = []
    for node in block.find_all(["p", "li"]):
        text = _clean_text(node.get_text(" ", strip=True))
        if not text or _SKIP_UK_ENTRY_RE.search(text):
            continue
        if text not in paragraphs:
            paragraphs.append(text)
    if paragraphs:
        return paragraphs
    text = _clean_text(block.get_text(" ", strip=True))
    return [text] if text and not _SKIP_UK_ENTRY_RE.search(text) else []


_ACADEMIC_UK_ENTRY_RE = re.compile(
    r"\bucas\b|\bgcse\b|\ba[- ]?level\b|\bbtec\b|"
    r"honou?rs?.{0,8}degree|\b2\s*[.:]\s*[12]\b",
    re.I,
)


def _is_academic_uk_entry(text: str) -> bool:
    return bool(
        _UCAS_CLEARING_RE.search(text)
        or _UCAS_POINTS_RE.search(text)
        or _UK_CLASS_RE.search(text)
        or _ACADEMIC_UK_ENTRY_RE.search(text)
    )


def _normalize_uk_entry_lines(paragraphs: list[str]) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        cleaned = _clean_text(text)
        if not cleaned or cleaned in seen:
            return
        lines.append(cleaned)
        seen.add(cleaned)

    for paragraph in paragraphs:
        if _SKIP_UK_ENTRY_RE.search(paragraph) or not _is_academic_uk_entry(paragraph):
            continue
        clearing = _UCAS_CLEARING_RE.search(paragraph)
        if clearing:
            add(f"Typical UCAS Tariff points for Clearing entry: {clearing.group(1)}.")
            add(f"{clearing.group(1)} UCAS Tariff points.")
            continue
        rewritten = re.sub(r"UCAS points", "UCAS Tariff points", paragraph, flags=re.I)
        add(rewritten)
        tariff = _UCAS_POINTS_RE.search(rewritten)
        if tariff:
            add(f"{tariff.group(1)} UCAS Tariff points.")
    return lines


def _append_entry_section(facts, soup: BeautifulSoup, uk_lines: list[str]) -> None:
    if not uk_lines:
        return
    heading = soup.new_tag("h4")
    heading.string = "Entry requirements"
    facts.append(heading)
    for line in uk_lines:
        para = soup.new_tag("p")
        para.string = line
        facts.append(para)


def _uk_lines_from_markdown(markdown: str) -> list[str]:
    paragraphs: list[str] = []
    for raw in markdown.splitlines():
        stripped = raw.strip().lstrip("- ").strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("**Start date:") or stripped.startswith("**Duration:"):
            continue
        if stripped.startswith("Award ") or stripped.startswith("Annual tuition fees"):
            continue
        if _SKIP_UK_ENTRY_RE.search(stripped):
            continue
        if _is_academic_uk_entry(stripped):
            paragraphs.append(stripped)
    return _normalize_uk_entry_lines(paragraphs)


def _build_entry_markdown(uk_lines: list[str]) -> str:
    if not uk_lines:
        return ""
    return "\n".join(["## Entry requirements", ""] + uk_lines)


def preprocess_course_html_uni(soup: BeautifulSoup) -> None:
    """Keep title plus Stage 1 start / duration / international fee and UK entry."""
    title_node = soup.select_one("h1.gre-long-title") or soup.select_one("h1")
    title = title_node.get_text(" ", strip=True) if title_node else ""
    intakes = _collect_intakes(soup)
    duration = _duration_from_soup(soup)
    fee = _international_fee(soup)
    award = ExtractionPathConfig.infer_degree_name(title) if title else ""
    uk_lines = _normalize_uk_entry_lines(_uk_entry_paragraphs(soup))

    facts = soup.new_tag("div")
    facts["id"] = "gre-clean-facts"
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
    _append_entry_section(facts, soup, uk_lines)

    host = soup.select_one("main") or soup.body
    if host is None:
        return
    host.clear()
    if title_node is not None:
        host.append(BeautifulSoup(str(title_node), "html.parser").find(True))
    host.append(facts)


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Force Stage 1 shapes; keep course-page UK entry for the LLM to map."""
    title = ""
    for line in markdown.splitlines():
        if re.match(r"^# [^#]", line):
            title = line.strip()
            break
    course_name = title[2:].strip() if title.startswith("# ") else ""
    award = ExtractionPathConfig.infer_degree_name(course_name)

    intakes = Stage1MarkdownParser.normalize_intake_text(
        ", ".join(
            f"{month} {year}" for month, year in _MONTH_YEAR_RE.findall(markdown)
        )
    )
    duration_match = re.search(r"\*\*Duration:\*\*\s*(.+)", markdown, re.I)
    duration = duration_match.group(1).strip() if duration_match else ""
    if duration and _is_part_time(duration) and not _is_full_time(duration):
        duration = ""
    if duration and _is_sandwich(duration) and not _is_full_time(duration):
        duration = ""
    fee_match = re.search(
        r"(?:Annual tuition fees|First year tuition fee):\s*\|\s*£([\d,]+)",
        markdown,
        re.I,
    )
    fee = fee_match.group(1).replace(",", "") if fee_match else ""
    if not fee:
        amounts = [raw.replace(",", "") for raw in _FEE_RE.findall(markdown)]
        if amounts:
            fee = amounts[-1]

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
    entry_section = _build_entry_markdown(_uk_lines_from_markdown(markdown))
    if entry_section:
        lines.extend(["", entry_section])
    return "\n".join(line for line in lines if line is not None).strip() + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
