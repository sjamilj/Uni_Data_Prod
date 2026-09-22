"""University of East Anglia — keep International entry/fees and Stage 1 shapes."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, Tag

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import _normalize_blank_lines, main

_IELTS_OVERALL_RE = re.compile(
    r"IELTS[:\s]+([\d.]+)\s*overall",
    re.I,
)
_IELTS_EACH_RE = re.compile(
    r"minimum\s+([\d.]+)\s+in\s+(?:each|all)\s+components?",
    re.I,
)
_IELTS_COMPONENT_RE = re.compile(
    r"minimum\s+([\d.]+)\s+in\s+(Writing|Listening|Reading|Speaking)",
    re.I,
)
_INTL_FEE_RE = re.compile(
    r"International Students:\s*£([\d,]+)",
    re.I,
)
_DURATION_RE = re.compile(
    r"Course Length[:\s]*\*?\*?:?\s*([^\n]+)",
    re.I,
)
_START_RE = re.compile(
    r"Course Start Date[:\s]*\*?\*?:?\s*([^\n]+)",
    re.I,
)
_START_MD_RE = re.compile(
    r"-\s+\*\*(?:Start date|Course Start Date):\*\*\s*([^\n]+)",
    re.I,
)
_DURATION_MD_RE = re.compile(
    r"-\s+\*\*(?:Duration|Course Length):\*\*\s*([^\n]+)",
    re.I,
)


def _unwrap_dl_wrappers(soup: BeautifulSoup) -> None:
    """UEA wraps each dt/dd pair in a div; shared dl conversion only sees direct children."""
    for dl in soup.find_all("dl"):
        for wrapper in list(dl.find_all("div", recursive=False)):
            wrapper.unwrap()


def _keep_international_tab(soup: BeautifulSoup) -> None:
    """Leave International tabpanel; drop UK (and other) panels when International exists."""
    for tablist in soup.select('[role="tablist"]'):
        international = None
        for tab in tablist.select('[role="tab"]'):
            label = tab.get_text(" ", strip=True).casefold()
            if "international" in label:
                international = tab
                break
        if international is None:
            continue
        panel_id = (international.get("aria-controls") or "").strip()
        if not panel_id:
            continue
        for tab in tablist.select('[role="tab"]'):
            selected = tab is international
            tab["aria-selected"] = "true" if selected else "false"
        parent = tablist.parent
        scope = parent if parent is not None else soup
        for panel in list(scope.select('[role="tabpanel"]')):
            if panel.get("id") != panel_id:
                panel.decompose()


def _strip_key_details_noise(soup: BeautifulSoup) -> None:
    for node in soup.select('[class*="course-variants"]'):
        node.decompose()
    content = soup.select_one("[class*=key-details__content]")
    if content is None:
        return
    for link in content.select("a[data-search-department]"):
        parent = link.find_parent("div")
        if parent is not None and parent is not content:
            parent.decompose()
        else:
            link.decompose()
    label = content.find("p", class_=re.compile("font-semibold"))
    if label and "key details" in label.get_text(" ", strip=True).casefold():
        label.decompose()


def _dl_pairs(root: Tag) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for dt in root.find_all("dt"):
        dd = dt.find_next_sibling("dd")
        if dd is None:
            dd = dt.find_next("dd")
        if dd is None:
            continue
        key = re.sub(r"\s+", " ", dt.get_text(" ", strip=True)).strip().casefold()
        value = re.sub(r"\s+", " ", dd.get_text(" ", strip=True)).strip()
        if key and value:
            pairs[key] = value
    return pairs


def _inject_stage1_key_facts(soup: BeautifulSoup) -> None:
    content = soup.select_one("[class*=key-details__content]")
    if content is None:
        return
    pairs = _dl_pairs(content)
    duration = pairs.get("course length", "")
    start = pairs.get("course start date", "")
    attendance = pairs.get("attendance", "")
    award = pairs.get("award", "")
    typical_offer = pairs.get("typical offer", "")
    contextual_offer = pairs.get("contextual offer", "")
    dl = content.find("dl")
    if dl is not None:
        dl.decompose()
    facts = soup.new_tag("div", id="uea-key-facts")
    if duration:
        line = soup.new_tag("p")
        line.string = f"**Duration:** {duration}"
        facts.append(line)
    if start:
        line = soup.new_tag("p")
        line.string = f"- **Start date:** {start}"
        facts.append(line)
    if attendance:
        line = soup.new_tag("p")
        line.string = f"- **Attendance:** {attendance}"
        facts.append(line)
    if award:
        line = soup.new_tag("p")
        line.string = f"- Award {award}"
        facts.append(line)
    if typical_offer:
        line = soup.new_tag("p")
        line.string = f"- **Typical Offer:** {typical_offer}"
        facts.append(line)
    if contextual_offer:
        line = soup.new_tag("p")
        line.string = f"- **Contextual Offer:** {contextual_offer}"
        facts.append(line)
    if facts.contents:
        content.append(facts)


def _keep_international_fee_line(soup: BeautifulSoup) -> None:
    fees = soup.select_one("#fees_funding")
    if fees is None:
        return
    text = fees.get_text(" ", strip=True)
    match = _INTL_FEE_RE.search(text)
    if not match:
        return
    amount = match.group(1)
    block = soup.new_tag("div", id="uea-international-fees")
    heading = soup.new_tag("h3")
    heading.string = "International students"
    para = soup.new_tag("p")
    para.string = f"Annual tuition fees: | £{amount}"
    block.append(heading)
    block.append(para)
    fees.clear()
    title = soup.new_tag("h2")
    title.string = "Fees and funding"
    fees.append(title)
    fees.append(block)


def preprocess_course_html_uni(soup: BeautifulSoup) -> None:
    """International tab + nested description lists before generic block extract."""
    _unwrap_dl_wrappers(soup)
    _keep_international_tab(soup)
    _strip_key_details_noise(soup)
    _inject_stage1_key_facts(soup)
    _keep_international_fee_line(soup)


def _section_body(markdown: str, heading: str) -> str:
    marker = heading
    if marker not in markdown:
        return ""
    _, tail = markdown.split(marker, 1)
    next_section = re.search(r"\n## ", tail)
    body = tail[: next_section.start()] if next_section else tail
    return body.strip()


def _normalize_ielts_line(text: str) -> str | None:
    overall_match = _IELTS_OVERALL_RE.search(text)
    if not overall_match:
        return None
    overall = overall_match.group(1)
    each = _IELTS_EACH_RE.search(text)
    if each:
        section = each.group(1)
    else:
        components = [float(m.group(1)) for m in _IELTS_COMPONENT_RE.finditer(text)]
        section = f"{min(components):g}" if components else overall
    return f"IELTS {overall} overall with no less than {section} in each band"


def _duration_from(markdown: str) -> str:
    for pattern in (_DURATION_MD_RE, _DURATION_RE):
        match = pattern.search(markdown)
        if match:
            return match.group(1).strip().strip("* ")
    bold = re.search(r"\*\*Duration:\*\*\s*([^\n]+)", markdown, re.I)
    return bold.group(1).strip() if bold else ""


def _start_from(markdown: str) -> str:
    for pattern in (_START_MD_RE, _START_RE):
        match = pattern.search(markdown)
        if match:
            return match.group(1).strip().strip("* ")
    return ""


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Rewrite key facts, IELTS, and international fee into Stage 1 parser shapes."""
    title = ""
    for line in markdown.splitlines():
        if re.match(r"^# [^#]", line):
            title = line.strip()
            break

    key_body = _section_body(markdown, "## Key information")
    entry_body = _section_body(markdown, "## Entry requirements")
    fees_body = _section_body(markdown, "## Fees and funding")

    duration = _duration_from(key_body or markdown)
    start = _start_from(key_body or markdown)
    ielts = _normalize_ielts_line(entry_body or markdown)
    fee_match = _INTL_FEE_RE.search(fees_body or markdown) or re.search(
        r"Annual tuition fees:\s*\|\s*£([\d,]+)",
        fees_body or markdown,
        re.I,
    )

    parts: list[str] = []
    if title:
        parts.extend([title, ""])

    parts.append("## Key information")
    parts.append("")
    if duration:
        parts.append(f"**Duration:** {duration}")
    if start:
        parts.append(f"- **Start date:** {start}")
    if attendance := re.search(
        r"\*\*Attendance:\*\*\s*([^\n]+)",
        key_body or markdown,
        re.I,
    ):
        parts.append(f"- **Attendance:** {attendance.group(1).strip()}")
    if award := re.search(r"- Award\s+([^\n]+)", key_body or markdown, re.I):
        parts.append(f"- Award {award.group(1).strip()}")
    typical_offer = ""
    contextual_offer = ""
    if match := re.search(
        r"-\s+\*\*Typical Offer:\*\*\s*([^\n]+)",
        key_body or markdown,
        re.I,
    ):
        typical_offer = match.group(1).strip()
        parts.append(f"- **Typical Offer:** {typical_offer}")
    if match := re.search(
        r"-\s+\*\*Contextual Offer:\*\*\s*([^\n]+)",
        key_body or markdown,
        re.I,
    ):
        contextual_offer = match.group(1).strip()
        parts.append(f"- **Contextual Offer:** {contextual_offer}")
    if fee_match:
        amount = fee_match.group(1)
        parts.extend(
            [
                "",
                "### International students",
                "",
                f"Annual tuition fees: | £{amount}",
            ]
        )
    parts.append("")

    if entry_body or ielts:
        parts.append("## Entry requirements")
        parts.append("")
        if ielts:
            parts.append(ielts)
            parts.append("")
        if typical_offer or contextual_offer:
            offer_bits = []
            if typical_offer:
                offer_bits.append(f"A Levels **{typical_offer}**")
            if contextual_offer:
                offer_bits.append(f"Contextual offer: **{contextual_offer}**")
            parts.append(
                "- **Typical UK Entry Requirements:** " + " ".join(offer_bits)
            )
            parts.append("")
        if entry_body:
            cleaned_entry = _strip_entry_noise(entry_body)
            if cleaned_entry:
                parts.append(cleaned_entry)
                parts.append("")

    return _normalize_blank_lines("\n".join(parts))


_ALEVEL_GRADE_RE = re.compile(
    r"(?i)(\bA[\s-]?levels?\b:?\s+)(?!\*\*)((?:A\*)?[A-E]{2,4})\b"
)
_UK_CLASS_RE = re.compile(r"(?<!\*)\b(2[:.][12])\b(?!\*)")


def _emphasize_entry_grades(text: str) -> str:
    """Bold UG/foundation A-level offers and PG UK 2:1 / 2:2 classifications."""
    text = _ALEVEL_GRADE_RE.sub(r"\1**\2**", text)
    text = _UK_CLASS_RE.sub(r"**\1**", text)
    return text


def _strip_entry_noise(entry_body: str) -> str:
    text = entry_body
    text = re.sub(
        r"Choose UK or International above to see relevant information\.?\s*",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"Review our \[English Language Equivalencies[^\n]+",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"If you do not meet the English language requirements[\s\S]*?(?=\n### |\n## |\Z)",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"Our \[Admissions Policy\][^\n]+",
        "",
        text,
        flags=re.I,
    )
    return _emphasize_entry_grades(text.strip())


if __name__ == "__main__":
    raise SystemExit(main())
