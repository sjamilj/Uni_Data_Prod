"""University of Law — Stage 1 key facts, fees (UK + international), and scholarships."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from llm_extract import ExtractionPathConfig, Stage1MarkdownParser

_MONTH_YEAR_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+((?:19|20)\d{2})\b",
    re.I,
)
_ACADEMIC_YEAR_FEE_RE = re.compile(
    r"\b(20\d{2})/\d{2}\s+Course Fees\b",
    re.I,
)
_FEE_YEAR_ROW = re.compile(
    r"^\|\s*((?:20)?\d{2}/\d{2})\s+Course Fees",
    re.I,
)
_LONDON_FEE_ROW = re.compile(r"^\|\s*London\s*\|\s*(.+?)\s*\|?\s*$", re.I)
_BURSARY_RE = re.compile(
    r"including a £([\d,]+)\s+International Bursary",
    re.I,
)
_AMOUNT_RE = re.compile(r"£([\d,]+)")
_NORMALIZED_SECTION = "## Key facts (normalized)"
_START_DATES_SECTION = "## Course Start Dates"
_PLACEMENT_YEAR_START_LINE = re.compile(r"placement\s+year", re.I)
_FEES_SECTION = "## Fees and applying"
_INJECTED_CLASS = "ulaw-normalized-stage1"
_FEES_INJECTED_CLASS = "ulaw-normalized-fees"
_RICHTEXT_INTL_LONDON_RE = re.compile(
    r"London:\s*£([\d,]+)",
    re.I,
)
_RICHTEXT_FEE_YEAR_RE = re.compile(
    r"(20\d{2}/\d{2})\s+Course Fees",
    re.I,
)
_BULLET_LABEL_ORDER = (
    "start date",
    "degree",
    "entry requirements",
    "locations",
    "study mode",
    "duration",
    "method",
    "ucas code",
    "institution code",
    "short name",
    "international fee",
)
_DETAILS_GRID_LABELS = {
    "course length": "Duration",
    "study mode": "Study mode",
    "method": "Method",
    "entry requirements": "Entry requirements",
    "next start date": "Start date",
}


def _bullet(label: str, value: str) -> str:
    return f"- **{label}:** {value.strip()}"


def _degree_bullet_from_markdown(markdown: str) -> str:
    for line in markdown.splitlines():
        if not re.match(r"^#\s+[^#]", line):
            continue
        course_name = line.lstrip("#").strip()
        degree = ExtractionPathConfig.infer_degree_name(course_name)
        if degree:
            return _bullet("Degree", degree)
        break
    return ""


def _bullet_label(line: str) -> str:
    match = re.match(r"-\s*\*\*([^*]+):\*\*", line.strip())
    if not match:
        return ""
    return match.group(1).casefold().split("(")[0].strip()


def _order_normalized_bullets(bullets: list[str]) -> list[str]:
    multi: dict[str, list[str]] = {}
    single: dict[str, str] = {}
    for line in bullets:
        label = _bullet_label(line)
        if not label:
            continue
        if label in {"ucas code", "international fee"}:
            multi.setdefault(label, [])
            if line not in multi[label]:
                multi[label].append(line)
            continue
        if label == "uk fee":
            single[label] = line
        else:
            single[label] = line

    ordered: list[str] = []
    for key in _BULLET_LABEL_ORDER:
        if key in {"ucas code", "international fee"}:
            ordered.extend(multi.get(key, []))
        elif key in single:
            ordered.append(single[key])
    for key, line in single.items():
        if key not in _BULLET_LABEL_ORDER and line not in ordered:
            ordered.append(line)
    return ordered


def _append_unique(seen: list[str], value: str) -> None:
    text = (value or "").strip()
    if not text or text in seen:
        return
    seen.append(text)


def _sort_intakes(values: list[str]) -> list[str]:
    def key(item: str) -> tuple[int, int]:
        match = _MONTH_YEAR_RE.search(item)
        if not match:
            return (9999, 99)
        months = (
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        )
        month = match.group(1).casefold()
        return (int(match.group(2)), months.index(month) if month in months else 99)

    return sorted(values, key=key)


def _first_amount(text: str) -> str:
    match = _AMOUNT_RE.search(text or "")
    return match.group(1).replace(",", "") if match else ""


def _parse_london_fees_by_year(table: str) -> list[tuple[str, str, str]]:
    """Return (academic_year, london_amount, raw_cell) — first London row per fee year only."""
    rows: list[tuple[str, str, str]] = []
    current_year = ""
    years_seen: set[str] = set()
    for line in (table or "").splitlines():
        year_match = _FEE_YEAR_ROW.match(line.strip())
        if year_match:
            current_year = year_match.group(1)
            if len(current_year) == 5 and current_year[2] == "/":
                current_year = "20" + current_year
            continue
        london_match = _LONDON_FEE_ROW.match(line.strip())
        if london_match and current_year and current_year not in years_seen:
            raw = london_match.group(1).strip()
            amount = _first_amount(raw)
            if amount:
                rows.append((current_year, amount, raw))
                years_seen.add(current_year)
    return rows


def _is_international_fee_table(table: str) -> bool:
    return bool(re.search(r"International Bursary", table or "", re.I))


def _chunk_has_fee_rows(chunk: str) -> bool:
    for line in chunk.splitlines():
        stripped = line.strip()
        if _FEE_YEAR_ROW.match(stripped) or _LONDON_FEE_ROW.match(stripped):
            return True
    return False


def _split_fee_tables(fees_body: str) -> list[str]:
    chunks = re.split(r"\r?\n(?=\| Location \| Fees \|)", fees_body)
    tables: list[str] = []
    for chunk in chunks:
        if _chunk_has_fee_rows(chunk):
            tables.append(chunk.strip())
    return tables


def _format_international_block(
    year_rows: list[tuple[str, str, str]],
    *,
    primary_amount: str,
) -> str:
    lines = ["### International students", "", "- Full Time"]
    for year_label, amount, _raw in year_rows:
        lines.append(f"- {year_label} (London)")
        lines.append(f"- £{int(amount):,}")
    lines.append("")
    if primary_amount:
        lines.append(f"Annual tuition fees: | £{int(primary_amount):,}")
    return "\n".join(lines).rstrip()


def _scholarship_lines(intl_table: str) -> list[str]:
    lines: list[str] = []
    intl_years = _parse_london_fees_by_year(intl_table)
    if intl_years:
        year_label, _amount, raw = intl_years[-1]
        bursary = _BURSARY_RE.search(raw)
        if not bursary and len(intl_years) > 1:
            _prev_label, _prev_amount, prev_raw = intl_years[-2]
            bursary = _BURSARY_RE.search(prev_raw)
            year_label = _prev_label
        if bursary:
            lines.append(
                f"- **International bursary ({year_label}):** "
                f"up to £{bursary.group(1)} off tuition (London; see fees table)"
            )
    if re.search(r"international-scholarships", intl_table or "", re.I):
        lines.append(
            "- **International scholarships:** see "
            "[International Scholarships and Bursaries]"
            "(/students/international/why-study-with-us/financial-information/international-scholarships/)"
        )
    return lines


def _html_table_to_fee_markdown(table: Tag) -> str:
    lines: list[str] = []
    for row in table.select("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.select("td, th")]
        if len(cells) >= 2:
            lines.append(f"| {cells[0]} | {cells[1]} |")
    return "\n".join(lines)


def _intl_london_fees_from_richtext(soup: BeautifulSoup) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for block in soup.select(".richtextblock"):
        text = block.get_text("\n", strip=True)
        if not re.search(r"non-domestic\s+students|international\s+students", text, re.I):
            continue
        if "London" not in text:
            continue
        if _RICHTEXT_FEE_YEAR_RE.search(text):
            parts = re.split(r"(20\d{2}/\d{2}\s+Course Fees)", text, flags=re.I)
            idx = 1
            while idx + 1 < len(parts):
                year_match = re.match(r"(20\d{2}/\d{2})", parts[idx], re.I)
                if not year_match:
                    idx += 1
                    continue
                year = year_match.group(1)
                body = parts[idx + 1]
                intl_body = body
                if re.search(r"non-domestic\s+students", body, re.I):
                    intl_body = re.split(
                        r"non-domestic\s+students",
                        body,
                        maxsplit=1,
                        flags=re.I,
                    )[-1]
                london_match = _RICHTEXT_INTL_LONDON_RE.search(intl_body)
                if london_match:
                    amount = london_match.group(1).replace(",", "")
                    rows.append((year, amount, london_match.group(0)))
                idx += 2
            continue
        london_match = _RICHTEXT_INTL_LONDON_RE.search(text)
        year_match = _RICHTEXT_FEE_YEAR_RE.search(text)
        if london_match and year_match:
            rows.append(
                (
                    year_match.group(1),
                    london_match.group(1).replace(",", ""),
                    london_match.group(0),
                )
            )
    seen: set[str] = set()
    ordered: list[tuple[str, str, str]] = []
    for year, amount, raw in rows:
        if year in seen:
            continue
        seen.add(year)
        ordered.append((year, amount, raw))
    return ordered


def _intl_london_fee_data_from_soup(
    soup: BeautifulSoup,
) -> tuple[list[tuple[str, str, str]], str]:
    """International London fees by academic year; second value is table markdown if any."""
    candidates: list[str] = []
    panes = soup.select('[id*="course-fees"]')
    fee_panes = [p for p in panes if p.select_one("table")]
    if len(fee_panes) >= 2:
        intl_table = fee_panes[1].select_one("table")
        if intl_table is not None:
            candidates.append(_html_table_to_fee_markdown(intl_table))
    for pane in fee_panes:
        table = pane.select_one("table")
        if table is None:
            continue
        markdown = _html_table_to_fee_markdown(table)
        if _is_international_fee_table(markdown):
            candidates.insert(0, markdown)
    if not candidates:
        for table in soup.select(
            '.accordion--course-details table, [id*="course-fees"] table, .tab-pane table'
        ):
            markdown = _html_table_to_fee_markdown(table)
            if _parse_london_fees_by_year(markdown):
                candidates.append(markdown)
    for markdown in candidates:
        years = _parse_london_fees_by_year(markdown)
        if years:
            return years, markdown
    return _intl_london_fees_from_richtext(soup), ""


def _fee_bullets_from_soup(soup: BeautifulSoup) -> list[str]:
    intl_years, _intl_md = _intl_london_fee_data_from_soup(soup)
    return _fee_summary_bullets(intl_years)


def _fee_bullets_from_fees_body(fees_body: str) -> list[str]:
    tables = _split_fee_tables(fees_body)
    if tables:
        intl_table = next((t for t in tables if _is_international_fee_table(t)), "")
        if not intl_table and len(tables) > 1:
            intl_table = tables[1]
        intl_years = _parse_london_fees_by_year(intl_table) if intl_table else []
        if not intl_years:
            intl_years = _parse_london_fees_by_year(tables[0])
        return _fee_summary_bullets(intl_years)
    year_rows: list[tuple[str, str, str]] = []
    current_year = ""
    for line in fees_body.splitlines():
        year_match = re.match(r"^-\s*(\d{4}/\d{2})\s*\(London\)", line.strip(), re.I)
        if year_match:
            current_year = year_match.group(1)
            continue
        amount_match = re.match(r"^-\s*£([\d,]+)", line.strip())
        if amount_match and current_year:
            year_rows.append(
                (current_year, amount_match.group(1).replace(",", ""), line.strip())
            )
            current_year = ""
    if year_rows:
        return _fee_summary_bullets(year_rows)
    annual = re.search(r"Annual tuition fees:\s*\|\s*£([\d,]+)", fees_body, re.I)
    year = re.search(r"-\s*(\d{4}/\d{2})\s*\(London\)", fees_body)
    if annual and year:
        amount = annual.group(1).replace(",", "")
        return [
            _bullet(f"International fee ({year.group(1)}, London)", f"£{int(amount):,}")
        ]
    return []


def _fee_summary_bullets(
    intl_years: list[tuple[str, str, str]],
) -> list[str]:
    bullets: list[str] = []
    for year_label, amount, _raw in intl_years:
        bullets.append(
            _bullet(f"International fee ({year_label}, London)", f"£{int(amount):,}")
        )
    return bullets


def _normalize_fees_section(markdown: str) -> tuple[str, list[str]]:
    idx = markdown.find(_FEES_SECTION)
    if idx < 0:
        return markdown, []

    tail = markdown[idx + len(_FEES_SECTION) :]
    end_match = re.search(r"\r?\n## ", tail)
    fees_body = tail[: end_match.start()] if end_match else tail

    tables = _split_fee_tables(fees_body)
    if not tables:
        fee_bullets = _fee_bullets_from_fees_body(fees_body)
        return markdown, fee_bullets

    intl_table = next((t for t in tables if _is_international_fee_table(t)), "")
    if not intl_table and len(tables) > 1:
        intl_table = tables[1]
    intl_years = _parse_london_fees_by_year(intl_table) if intl_table else []
    if not intl_years:
        intl_years = _parse_london_fees_by_year(tables[0])

    primary_fee = intl_years[-1][1] if intl_years else ""
    fee_bullets = _fee_summary_bullets(intl_years)

    parts: list[str] = [_FEES_SECTION, ""]

    if intl_years:
        parts.append(_format_international_block(intl_years, primary_amount=primary_fee))
        parts.append("")

    scholarship = _scholarship_lines(intl_table)
    if scholarship:
        parts.append("#### Scholarships and bursaries")
        parts.extend(scholarship)
        parts.append("")

    new_section = "\n".join(parts).rstrip() + "\n"
    suffix = tail[end_match.start() :] if end_match else ""
    return markdown[:idx] + new_section + suffix.lstrip("\n"), fee_bullets


def _key_facts_chunk(markdown: str) -> str:
    start = markdown.find("## Key facts\n")
    if start < 0:
        start = markdown.find("## Key facts\r\n")
    if start < 0:
        return ""
    chunk = markdown[start:]
    end = re.search(r"\n## (?!#)", chunk[12:])
    return chunk[: 12 + end.start()] if end else chunk


def _section_after_h4(chunk: str, heading: str) -> str:
    pattern = rf"####\s*{re.escape(heading)}\s*\n+([\s\S]*?)(?=\n#### |\n## |\Z)"
    match = re.search(pattern, chunk, re.I)
    if not match:
        return ""
    text = match.group(1).strip()
    text = re.split(r"Course requirements", text, maxsplit=1, flags=re.I)[0]
    text = re.sub(r"\n(?:See all Start Dates|Entry requirements)\s*$", "", text, flags=re.I)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _promo_bullets_from_text(text: str) -> list[str]:
    bullets: list[str] = []
    for match in re.finditer(
        r"\b([A-Z]\d{3})\b\s*[-–:]\s*([^\n]+)",
        text,
        re.I,
    ):
        bullets.append(
            _bullet(
                "UCAS code",
                f"{match.group(1).upper()} — {match.group(2).strip()}",
            )
        )
    inst = re.search(r"Institution code:\s*([A-Z0-9]+)", text, re.I)
    if inst:
        bullets.append(_bullet("Institution code", inst.group(1).upper()))
    short = re.search(r"Short name:\s*([^\n]+)", text, re.I)
    if short:
        bullets.append(_bullet("Short name", short.group(1).strip()))
    return bullets


def _merge_bullet(bullets: list[str], line: str) -> None:
    label = _bullet_label(line)
    if not label:
        return
    if any(_bullet_label(existing) == label for existing in bullets):
        return
    bullets.append(line)


def _details_grid_bullets_from_soup(soup: BeautifulSoup) -> list[str]:
    """PG layout: #courseKeyFactsBlock / .details-grid with span + div.content."""
    root = soup.select_one("#courseKeyFactsBlock")
    if root is None:
        root = soup.select_one(".details-grid")
    if root is None:
        return []
    bullets: list[str] = []
    for block in root.select(".p-4"):
        label_node = block.find("span", recursive=False)
        content = block.select_one("div.content")
        if label_node is None or content is None:
            continue
        label_key = label_node.get_text(" ", strip=True).casefold()
        value = content.get_text(" ", strip=True)
        if not value:
            continue
        mapped = _DETAILS_GRID_LABELS.get(label_key)
        if not mapped:
            continue
        if mapped == "Start date":
            match = _MONTH_YEAR_RE.search(value)
            if match:
                value = f"{match.group(1).title()} {match.group(2)}"
        bullets.append(_bullet(mapped, value))
    return bullets


def _h4_value(h4: Tag) -> str:
    parts: list[str] = []
    for sib in h4.next_siblings:
        if isinstance(sib, Tag) and sib.name == "h4":
            break
        if isinstance(sib, Tag):
            if sib.name == "a" and re.search(
                r"see all start dates|entry requirements",
                sib.get_text(" ", strip=True),
                re.I,
            ):
                continue
            parts.append(sib.get_text("; ", strip=True))
        elif isinstance(sib, NavigableString):
            parts.append(str(sib).strip())
    text = re.sub(r"\s+", " ", " ".join(parts)).strip(" ;")
    text = re.split(r"Course requirements", text, maxsplit=1, flags=re.I)[0].strip()
    return text


def _collect_key_fact_bullets(markdown: str, soup: BeautifulSoup | None = None) -> list[str]:
    bullets: list[str] = []
    for line in _bullets_from_normalized_section(markdown):
        _merge_bullet(bullets, line)
    chunk = _key_facts_chunk(markdown)

    if soup is not None:
        for line in _details_grid_bullets_from_soup(soup):
            _merge_bullet(bullets, line)
        for h4 in soup.select(".key-facts__details h4"):
            label = h4.get_text(" ", strip=True)
            label_l = label.casefold()
            value = _h4_value(h4)
            if not value or re.search(r"see all start dates", value, re.I):
                continue
            if "entry requirements" in label_l:
                _merge_bullet(bullets, _bullet("Entry requirements", value[:500]))
            elif label_l.startswith("locations"):
                _merge_bullet(bullets, _bullet("Locations", value))
            elif "study mode" in label_l:
                _merge_bullet(bullets, _bullet("Study mode", value))
            elif "next start date" in label_l:
                match = _MONTH_YEAR_RE.search(value)
                if match:
                    _merge_bullet(
                        bullets,
                        _bullet(
                            "Start date",
                            f"{match.group(1).title()} {match.group(2)}",
                        ),
                    )
        promo = soup.select_one(".key-facts__promo-content") or soup.select_one(
            ".key-facts__promo"
        )
        if promo is not None:
            bullets.extend(_promo_bullets_from_text(promo.get_text("\n", strip=True)))
        elif soup.select_one(".key-facts"):
            bullets.extend(
                _promo_bullets_from_text(
                    soup.select_one(".key-facts").get_text("\n", strip=True)
                )
            )

    if chunk:
        entry = _section_after_h4(chunk, "Entry requirements")
        if entry and not any("**Entry requirements:**" in b for b in bullets):
            bullets.append(_bullet("Entry requirements", entry[:500]))
        locations = _section_after_h4(chunk, "Locations")
        if locations and not any("**Locations:**" in b for b in bullets):
            bullets.append(_bullet("Locations", locations))
        mode = _section_after_h4(chunk, "Study mode options")
        if mode and not any("**Study mode:**" in b for b in bullets):
            bullets.append(_bullet("Study mode", mode))
        if not any("**Start date:**" in b for b in bullets):
            next_start = _section_after_h4(chunk, "Next start date")
            match = _MONTH_YEAR_RE.search(next_start)
            if match:
                bullets.append(
                    _bullet(
                        "Start date",
                        f"{match.group(1).title()} {match.group(2)}",
                    )
                )
        if not any("**UCAS code:**" in b for b in bullets):
            bullets.extend(_promo_bullets_from_text(chunk))

    intakes = _intakes_from_markdown(markdown)
    if intakes:
        intake_line = Stage1MarkdownParser.normalize_intake_text(", ".join(intakes))
        bullets = [b for b in bullets if not b.lower().startswith("- **start date:**")]
        bullets.insert(0, _bullet("Start date", intake_line))

    degree_line = _degree_bullet_from_markdown(markdown)
    if degree_line:
        _merge_bullet(bullets, degree_line)

    return _order_normalized_bullets(bullets)


def _intakes_from_start_date_accordion(soup: BeautifulSoup) -> list[str]:
    seen: list[str] = []
    root = soup.select_one(".coursestartdateaccordionblock") or soup.select_one(
        "#course-start-dates"
    )
    if root is None:
        return seen
    for h4 in root.select("h4"):
        match = _MONTH_YEAR_RE.search(h4.get_text(" ", strip=True))
        if match:
            _append_unique(seen, f"{match.group(1).title()} {match.group(2)}")
    return seen


def _intakes_from_key_facts(soup: BeautifulSoup) -> list[str]:
    seen: list[str] = []
    for h4 in soup.select(".key-facts__details h4"):
        if not re.search(r"next start date", h4.get_text(" ", strip=True), re.I):
            continue
        sibling = h4.find_next_sibling()
        while sibling is not None and getattr(sibling, "name", None) not in {"p", "div"}:
            sibling = sibling.find_next_sibling()
        if sibling is None:
            continue
        match = _MONTH_YEAR_RE.search(sibling.get_text(" ", strip=True))
        if match:
            _append_unique(seen, f"{match.group(1).title()} {match.group(2)}")
    return seen


def _intakes_from_fee_text(text: str) -> list[str]:
    seen: list[str] = []
    for match in _ACADEMIC_YEAR_FEE_RE.finditer(text or ""):
        year = int(match.group(1))
        _append_unique(seen, f"September {year}")
    return seen


def _collect_intakes_from_soup(soup: BeautifulSoup) -> list[str]:
    seen: list[str] = []
    for batch in (
        _intakes_from_start_date_accordion(soup),
        _intakes_from_key_facts(soup),
    ):
        for item in batch:
            _append_unique(seen, item)
    if seen:
        return _sort_intakes(seen)
    fees = soup.select_one("#fees-and-applying")
    if fees:
        for item in _intakes_from_fee_text(fees.get_text("\n", strip=True)):
            _append_unique(seen, item)
    return _sort_intakes(seen)


def _expand_start_date_panels(soup: BeautifulSoup) -> None:
    for panel in soup.select(".coursestartdateaccordionblock .collapse"):
        classes = list(panel.get("class") or [])
        if "show" not in classes:
            classes.append("show")
        panel["class"] = classes
        if panel.has_attr("style"):
            del panel["style"]


def _append_fees_markup(node: Tag, soup: BeautifulSoup, text: str) -> None:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("### "):
            heading = soup.new_tag("h3")
            heading.string = stripped[4:].strip()
            node.append(heading)
        elif stripped.startswith("#### "):
            heading = soup.new_tag("h4")
            heading.string = stripped[5:].strip()
            node.append(heading)
        elif stripped.startswith("- "):
            para = soup.new_tag("p")
            para.string = stripped
            node.append(para)
        else:
            para = soup.new_tag("p")
            para.string = stripped
            node.append(para)


def _inject_fees_block(soup: BeautifulSoup) -> None:
    intl_years, intl_md = _intl_london_fee_data_from_soup(soup)
    if not intl_years:
        return
    node = soup.select_one(f".{_FEES_INJECTED_CLASS}")
    if node is None:
        node = soup.new_tag("div")
        node["class"] = _FEES_INJECTED_CLASS
        anchor = soup.select_one(f".{_INJECTED_CLASS}") or soup.select_one("h1")
        if anchor is not None:
            anchor.insert_after(node)
        else:
            host = soup.body or soup
            host.insert(0, node)
    node.clear()
    heading = soup.new_tag("h2")
    heading.string = "Fees and applying"
    node.append(heading)
    primary = intl_years[-1][1]
    body = _format_international_block(intl_years, primary_amount=primary)
    scholarship = _scholarship_lines(intl_md)
    if scholarship:
        body += "\n\n#### Scholarships and bursaries\n" + "\n".join(scholarship)
    _append_fees_markup(node, soup, body)


def _ensure_injected_facts_node(soup: BeautifulSoup) -> Tag:
    existing = soup.select_one(f".{_INJECTED_CLASS}")
    if existing is not None:
        return existing
    node = soup.new_tag("div")
    node["class"] = _INJECTED_CLASS
    anchor = (
        soup.select_one("#course-details-header-intro")
        or soup.select_one(".course-details-header")
        or soup.select_one("h1")
    )
    if anchor is not None:
        anchor.insert_after(node)
    else:
        host = soup.body or soup
        host.insert(0, node)
    return node


def preprocess_course_html_uni(soup: BeautifulSoup) -> None:
    """Expose start dates and inject Stage 1 key facts before HTML→markdown."""
    _expand_start_date_panels(soup)
    bullets = _collect_key_fact_bullets("", soup=soup)
    bullets.extend(_fee_bullets_from_soup(soup))
    intakes = _collect_intakes_from_soup(soup)
    if intakes:
        intake_line = Stage1MarkdownParser.normalize_intake_text(", ".join(intakes))
        bullets = [b for b in bullets if not b.lower().startswith("- **start date:**")]
        bullets.insert(0, _bullet("Start date", intake_line))
    h1 = soup.select_one("h1")
    if h1 is not None:
        degree_line = _degree_bullet_from_markdown("# " + h1.get_text(" ", strip=True))
        if degree_line:
            _merge_bullet(bullets, degree_line)
    bullets = _order_normalized_bullets(bullets)
    if not bullets:
        return
    facts = _ensure_injected_facts_node(soup)
    facts.clear()
    heading = soup.new_tag("h2")
    heading.string = "Key facts (normalized)"
    facts.append(heading)
    ul = soup.new_tag("ul")
    for bullet in bullets:
        li = soup.new_tag("li")
        text = bullet.lstrip("- ").strip()
        if text.startswith("**") and ":**" in text:
            label, value = text.split(":**", 1)
            strong = soup.new_tag("strong")
            strong.string = label.strip("*") + ":"
            li.append(strong)
            li.append(" " + value.strip())
        else:
            li.string = text
        ul.append(li)
    facts.append(ul)
    _inject_fees_block(soup)


def _intakes_from_markdown(markdown: str) -> list[str]:
    seen: list[str] = []
    if _NORMALIZED_SECTION in markdown:
        section = markdown.split(_NORMALIZED_SECTION, 1)[1]
        for match in _MONTH_YEAR_RE.finditer(section[:800]):
            _append_unique(seen, f"{match.group(1).title()} {match.group(2)}")

    start_dates_idx = markdown.find("## Course Start Dates")
    if start_dates_idx >= 0:
        chunk = markdown[start_dates_idx : start_dates_idx + 4000]
        for match in _MONTH_YEAR_RE.finditer(chunk):
            _append_unique(seen, f"{match.group(1).title()} {match.group(2)}")

    key_facts_idx = markdown.find("## Key facts")
    if key_facts_idx >= 0:
        chunk = markdown[key_facts_idx : key_facts_idx + 1200]
        if re.search(r"next start date", chunk, re.I):
            after = re.split(r"next start date", chunk, maxsplit=1, flags=re.I)[-1]
            match = _MONTH_YEAR_RE.search(after[:200])
            if match:
                _append_unique(seen, f"{match.group(1).title()} {match.group(2)}")

    if seen:
        return _sort_intakes(seen)

    fees_idx = markdown.find(_FEES_SECTION)
    if fees_idx >= 0:
        for item in _intakes_from_fee_text(markdown[fees_idx:]):
            _append_unique(seen, item)

    return _sort_intakes(seen)


def _bullets_from_normalized_section(markdown: str) -> list[str]:
    if _NORMALIZED_SECTION not in markdown:
        return []
    tail = markdown.split(_NORMALIZED_SECTION, 1)[1]
    chunk = re.split(r"\r?\n##\s", tail, maxsplit=1)[0]
    return [
        line.strip()
        for line in chunk.splitlines()
        if line.strip().startswith("- **") and ":**" in line
    ]


def _replace_normalized_section(markdown: str, bullets: list[str]) -> str:
    body = "\n".join(bullets) + "\n"
    section = f"{_NORMALIZED_SECTION}\n\n{body}"
    if _NORMALIZED_SECTION in markdown:
        return re.sub(
            rf"{_NORMALIZED_SECTION}\r?\n\r?\n[\s\S]*?(?=\r?\n## |\Z)",
            section.rstrip() + "\n",
            markdown,
            count=1,
        )
    title_end = markdown.find("\n## ")
    if title_end < 0:
        return markdown.rstrip() + "\n\n" + section
    return markdown[:title_end] + "\n\n" + section + markdown[title_end:]


def _remove_placement_year_start_date_lines(markdown: str) -> str:
    if _START_DATES_SECTION not in markdown:
        return markdown
    head, rest = markdown.split(_START_DATES_SECTION, 1)
    end = re.search(r"\r?\n##\s", rest)
    if end:
        section, tail = rest[: end.start()], rest[end.start() :]
    else:
        section, tail = rest, ""
    kept: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") and _PLACEMENT_YEAR_START_LINE.search(stripped):
            continue
        kept.append(line)
    body = "\n".join(kept)
    if body and not body.endswith("\n"):
        body += "\n"
    return head + _START_DATES_SECTION + body + tail


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Normalize ULaw fees and inject Stage 1 key facts / international fee shapes."""
    markdown, fee_bullets = _normalize_fees_section(markdown)
    if not fee_bullets:
        fees_idx = markdown.find(_FEES_SECTION)
        if fees_idx >= 0:
            tail = markdown[fees_idx + len(_FEES_SECTION) :]
            end_match = re.search(r"\r?\n## ", tail)
            fees_body = tail[: end_match.start()] if end_match else tail
            fee_bullets = _fee_bullets_from_fees_body(fees_body)
    bullets = _collect_key_fact_bullets(markdown)
    bullets.extend(fee_bullets)
    bullets = _order_normalized_bullets(bullets)
    if bullets:
        markdown = _replace_normalized_section(markdown, bullets)
    return _remove_placement_year_start_date_lines(markdown)


if __name__ == "__main__":
    import importlib.util

    _spec = importlib.util.spec_from_file_location(
        "shared_course_markdown_cleanup", _SHARED / "course_markdown_cleanup.py"
    )
    _shared = importlib.util.module_from_spec(_spec)
    assert _spec.loader is not None
    _spec.loader.exec_module(_shared)
    raise SystemExit(_shared.main())
