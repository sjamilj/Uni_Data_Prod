"""University-specific course markdown cleanup (optional).

Configure simple heading removal in code/.env:

  COURSE_MARKDOWN_REMOVE_SECTIONS="
  2 :: Course overview
  2 :: Choose your country
  2 :: *meet these entry requirements*
  4 :: With placement
  3 :: UK students
  "

CCCU presetup/execute markdown omits Course overview marketing prose (see ENV.MD
COURSE_CLEAN_BLOCKS). Key course information is injected from the
`.course-details-banner` block on the source HTML page. Fees tables drop the UK
column and Home (UK) fee prose; international/overseas values are kept.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

_spec = importlib.util.spec_from_file_location(
    "shared_course_markdown_cleanup",
    _SHARED / "course_markdown_cleanup.py",
)
_shared_cleanup = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_shared_cleanup)
CourseMarkdownCleaner = _shared_cleanup.CourseMarkdownCleaner
main = _shared_cleanup.main

_BANNER_LABELS = (
    ("Starting", "Start date"),
    ("Study Mode", "Mode"),
    ("Entry grades", "Entry grades"),
    ("UCAS code", "UCAS code"),
    ("Duration", "Duration"),
    ("Location(s)", "Location"),
)
_FEES_SECTION = "## Fees"
_TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")
_HOME_FEES_MARKER = re.compile(r"^\*?\s*Home\s*\(UK\)\s*Fees", re.I)
_OVERSEAS_FEES_MARKER = re.compile(r"^Overseas/International fees", re.I)
_UK_COLUMN = re.compile(r"^UK\*?$|^UK students?$", re.I)


def _output_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "output"


def _split_table_cells(line: str) -> list[str] | None:
    match = _TABLE_ROW.match(line.strip())
    if not match:
        return None
    return [cell.strip() for cell in match.group(1).split("|")]


def _detail_value(detail) -> str:
    button = detail.select_one(".dropdown-button")
    if button:
        return button.get_text(" ", strip=True)
    option = detail.select_one(".optionText")
    if option:
        return option.get_text(" ", strip=True)
    value = detail.select_one("span.value")
    if value:
        return value.get_text(" ", strip=True)
    heading = detail.select_one(".heading")
    text = detail.get_text(" ", strip=True)
    if heading:
        label = heading.get_text(" ", strip=True)
        if text.startswith(label):
            text = text[len(label) :].strip()
    return text


def extract_key_course_information_from_html(html: str) -> dict[str, str]:
    """Parse CCCU course page banner facts."""
    soup = BeautifulSoup(html, "html.parser")
    banner = soup.select_one(".course-details-banner")
    if not banner:
        return {}

    by_heading = {}
    for detail in banner.select(".detail"):
        heading = detail.select_one(".heading")
        if not heading:
            continue
        key = heading.get_text(" ", strip=True)
        value = _detail_value(detail)
        if key and value:
            by_heading[key] = value

    facts: dict[str, str] = {}
    for source_label, output_label in _BANNER_LABELS:
        value = by_heading.get(source_label, "").strip()
        if value:
            facts[output_label] = value
    return facts


def format_key_course_information_markdown(facts: dict[str, str]) -> str:
    if not facts:
        return ""
    lines = ["## Key course information", ""]
    for label, value in facts.items():
        lines.append(f"- **{label}:** {value}")
    return "\n".join(lines)


def inject_key_course_information(markdown: str, facts_markdown: str) -> str:
    if not facts_markdown.strip():
        return markdown
    marker = "## Entry requirements"
    body = markdown
    if "## Key course information" in body:
        head, tail = body.split("## Key course information", 1)
        tail = re.sub(r"^[\s\S]*?(?=\n## |\Z)", "", tail, count=1)
        body = head.rstrip() + "\n\n" + facts_markdown.rstrip() + tail
    elif marker in body:
        body = body.replace(marker, facts_markdown + "\n\n" + marker, 1)
    else:
        body = body.rstrip() + "\n\n" + facts_markdown + "\n"
    return body


def _inject_key_course_information_from_source(markdown: str) -> str:
    meta, body = CourseMarkdownCleaner.parse_frontmatter(markdown)
    source_html = str(meta.get("source_html", "") or "").strip()
    if not source_html:
        return markdown

    html_path = _output_dir() / Path(source_html.replace("/", "\\"))
    if not html_path.is_file():
        html_path = _output_dir() / Path(source_html)
    if not html_path.is_file():
        return markdown

    facts = extract_key_course_information_from_html(
        html_path.read_text(encoding="utf-8", errors="replace")
    )
    block = format_key_course_information_markdown(facts)
    if not block:
        return markdown

    updated_body = inject_key_course_information(body, block)
    if meta:
        return CourseMarkdownCleaner.format_frontmatter(meta) + updated_body
    return updated_body


def _table_has_uk_overseas_columns(cells: list[str]) -> tuple[int, int] | None:
    uk_index = overseas_index = None
    for index, cell in enumerate(cells):
        if _UK_COLUMN.match(cell):
            uk_index = index
        if re.search(r"overseas|international", cell, re.I):
            overseas_index = index
    if uk_index is None or overseas_index is None:
        return None
    return uk_index, overseas_index


def _drop_table_column(cells: list[str], drop_index: int) -> list[str]:
    return [cell for index, cell in enumerate(cells) if index != drop_index]


def _rewrite_table_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _clean_fee_table_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    index = 0
    while index < len(lines):
        cells = _split_table_cells(lines[index])
        if cells is None:
            cleaned.append(lines[index])
            index += 1
            continue

        columns = _table_has_uk_overseas_columns(cells)
        if columns is None:
            cleaned.append(lines[index])
            index += 1
            continue

        uk_index, _overseas_index = columns
        table_lines = [lines[index]]
        index += 1
        while index < len(lines):
            row_cells = _split_table_cells(lines[index])
            if row_cells is None:
                break
            table_lines.append(lines[index])
            index += 1

        rewritten: list[str] = []
        for row_index, row in enumerate(table_lines):
            row_cells = _split_table_cells(row)
            if row_cells is None:
                continue
            trimmed = _drop_table_column(row_cells, uk_index)
            if row_index == 1 and all(set(cell) <= {"-", " "} for cell in trimmed):
                rewritten.append(_rewrite_table_row(trimmed))
                continue
            rewritten.append(_rewrite_table_row(trimmed))
        cleaned.extend(rewritten)
    return cleaned


def _strip_home_fee_prose(lines: list[str]) -> list[str]:
    output: list[str] = []
    skipping = False
    for line in lines:
        stripped = line.strip()
        if _HOME_FEES_MARKER.match(stripped):
            skipping = True
            continue
        if skipping and _OVERSEAS_FEES_MARKER.match(stripped):
            skipping = False
            output.append(line)
            continue
        if not skipping:
            output.append(line)
    return output


def _clean_fees_section(markdown: str) -> str:
    if _FEES_SECTION not in markdown:
        return markdown

    head, tail = markdown.split(_FEES_SECTION, 1)
    next_section = re.search(r"\n## ", tail)
    if next_section:
        fees_body = tail[: next_section.start()]
        after_fees = tail[next_section.start() :]
    else:
        fees_body = tail
        after_fees = ""

    lines = _strip_home_fee_prose(fees_body.splitlines())
    lines = _clean_fee_table_lines(lines)
    cleaned_body = "\n".join(lines).strip()
    rebuilt = head.rstrip() + "\n\n" + _FEES_SECTION + "\n\n" + cleaned_body
    if after_fees:
        rebuilt += "\n\n" + after_fees.lstrip("\n")
    return rebuilt.rstrip() + "\n"


def preprocess_course_markdown_uni(markdown: str) -> str:
    """Inject banner key facts before shared section removal."""
    return _inject_key_course_information_from_source(markdown)


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Strip UK fee columns/prose after shared section removal."""
    return _clean_fees_section(markdown)


if __name__ == "__main__":
    raise SystemExit(main())
