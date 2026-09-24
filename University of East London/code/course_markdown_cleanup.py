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
from study_level import folder_for_level

_MONTH_YEAR_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+((?:19|20)\d{2})\b",
    re.I,
)
_FEE_RE = re.compile(r"£\s*([\d,]+)")
_DURATION_RE = re.compile(r"Full time,?\s*([^\n|,]+)", re.I)

_ENTRY_ROUTE_HEADING = re.compile(
    r"^##\s+Entry requirements(?:\s*(?:[—–\-]\s*)(.+?))?\s*$",
    re.I,
)
_ENTRY_SECTION = re.compile(r"^##\s+Entry requirements\s*$", re.I)

_ROUTE_UNDERGRADUATE = "undergraduate"
_ROUTE_FOUNDATION = "foundation"

_ENTRY_SCREEN_IDS = (
    ("entry-req-details-1", "Degree (including contextual offer)", _ROUTE_UNDERGRADUATE),
    ("entry-req-details-2", "Degree with foundation year", _ROUTE_FOUNDATION),
)

_ACADEMIC_HEADING = "Academic requirements"
_ENGLISH_HEADING = "English Language requirements"


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


def _accordion_body(details_root: Tag, heading: str) -> Tag | None:
    target = heading.casefold()
    for node in details_root.select("h3.coh-heading, h3"):
        label = node.get_text(" ", strip=True).casefold()
        if target not in label and label != target:
            continue
        item = node.find_parent(class_=lambda c: c and "accordion-item" in c)
        if not item:
            continue
        body = item.select_one(".accordion-body .rich-txt-custom") or item.select_one(
            ".accordion-body .coh-wysiwyg"
        )
        if body:
            return body
    return None


def _append_cloned(parent: Tag, node: Tag) -> None:
    fragment = BeautifulSoup(str(node), "html.parser")
    cloned = fragment.find(True)
    if cloned:
        parent.append(cloned)


def _build_route_section(
    soup: BeautifulSoup,
    details_screen: Tag,
    route_label: str,
    route_key: str,
) -> Tag | None:
    academic = _accordion_body(details_screen, _ACADEMIC_HEADING)
    english = _accordion_body(details_screen, _ENGLISH_HEADING)
    if not academic and not english:
        return None

    section = soup.new_tag("section")
    section["class"] = "uel-entry-route"
    section["data-uel-route"] = route_key

    heading = soup.new_tag("h2")
    heading.string = f"Entry requirements - {route_label}"
    section.append(heading)

    if academic:
        h3 = soup.new_tag("h3")
        h3.string = _ACADEMIC_HEADING
        section.append(h3)
        _append_cloned(section, academic)

    if english:
        h3 = soup.new_tag("h3")
        h3.string = _ENGLISH_HEADING
        section.append(h3)
        _append_cloned(section, english)

    return section


def _find_entry_dialog(soup: BeautifulSoup) -> Tag | None:
    block = soup.select_one('[data-block-plugin-id="entry_requirements_block"]')
    if block is not None:
        dialog = block.select_one(
            "dialog.entry-requirements-modal, dialog.modal-entry, dialog"
        )
        if dialog is not None:
            return dialog
    return soup.select_one(
        "dialog.modal-entry.entry-requirements-modal, "
        "dialog#entry-requirements-1, dialog.modal-entry"
    )


def _build_flat_modal_entry(soup: BeautifulSoup, dialog: Tag) -> Tag | None:
    """PG (and similar): full entry text is already in the modal — no route picker."""
    if dialog.select_one(".entry-requirements-selection-screen"):
        return None
    if dialog.select_one("[id^='entry-req-details']"):
        return None
    body = (
        dialog.select_one(".modal-content .rich-txt-custom")
        or dialog.select_one(".modal-content .coh-wysiwyg")
        or dialog.select_one(".entry-requirements-details-content .rich-txt-custom")
    )
    if body is None or not body.get_text(strip=True):
        return None

    section = soup.new_tag("section")
    section["class"] = "uel-entry-route"
    section["data-uel-route"] = "postgraduate"

    heading = soup.new_tag("h2")
    heading.string = "Entry requirements"
    section.append(heading)
    _append_cloned(section, body)
    return section


def _build_entry_requirements_block(soup: BeautifulSoup) -> Tag | None:
    dialog = _find_entry_dialog(soup)
    if dialog is None:
        return None

    wrapper = soup.new_tag("div")
    wrapper["id"] = "uel-entry-requirements"

    for screen_id, route_label, _route_key in _ENTRY_SCREEN_IDS:
        screen = dialog.select_one(f"#{screen_id}")
        if screen is None:
            continue
        section = _build_route_section(soup, screen, route_label, _route_key)
        if section:
            wrapper.append(section)

    if not wrapper.contents:
        flat = _build_flat_modal_entry(soup, dialog)
        if flat is not None:
            wrapper.append(flat)

    return wrapper if wrapper.contents else None


def preprocess_course_html_uni(soup: BeautifulSoup) -> None:
    """Keep title, intakes/fees, and full-entry modal (academic + English per route)."""
    items = [
        item
        for item in soup.select(".course-option-details__list-item")
        if _is_international_full_time(item)
    ]
    preferred = [item for item in items if "placement" not in _item_label(item)]
    keep = preferred or items

    intakes = _collect_intakes(soup)
    title_node = soup.select_one("h1")
    title = title_node.get_text(" ", strip=True) if title_node else ""
    duration = _duration_from_item(keep[0]) if keep else ""
    fee_node = keep[0].select_one(".fee-type") if keep else None
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

    entry_block = _build_entry_requirements_block(soup)

    host = soup.select_one("main") or soup.body
    if host is None:
        return
    host.clear()
    if title_node is not None:
        host.append(BeautifulSoup(str(title_node), "html.parser").find(True))
    host.append(facts)
    if entry_block is not None:
        host.append(entry_block)


def _default_entry_route(markdown: str) -> str:
    for line in markdown.splitlines():
        if re.match(r"^# [^#]", line):
            if re.search(r"\bfoundation\s+year\b", line, re.I):
                return _ROUTE_FOUNDATION
            break
    return _ROUTE_UNDERGRADUATE


def _route_label_matches(route_key: str, route_label: str) -> bool:
    label = route_label.casefold()
    if route_key == _ROUTE_FOUNDATION:
        return "foundation year" in label
    return "contextual" in label or (
        "degree" in label and "foundation" not in label
    )


def _extract_entry_routes(markdown: str) -> dict[str, str]:
    lines = markdown.splitlines()
    routes: dict[str, list[str]] = {}
    current_key: str | None = None
    current_label = ""

    for line in lines:
        match = _ENTRY_ROUTE_HEADING.match(line)
        if match:
            current_label = (match.group(1) or "").strip()
            if not current_label:
                current_key = "postgraduate"
            elif _route_label_matches(_ROUTE_FOUNDATION, current_label):
                current_key = _ROUTE_FOUNDATION
            else:
                current_key = _ROUTE_UNDERGRADUATE
            routes[current_key] = [line]
            continue
        if current_key and (
            line.startswith("## ") and not _ENTRY_ROUTE_HEADING.match(line)
        ):
            current_key = None
            continue
        if current_key:
            routes[current_key].append(line)

    return {key: "\n".join(block).strip() for key, block in routes.items() if block}


def _join_entry_blocks(markdown: str) -> str:
    routes = _extract_entry_routes(markdown)
    if routes:
        parts: list[str] = []
        for key in (_ROUTE_UNDERGRADUATE, _ROUTE_FOUNDATION, "postgraduate"):
            block = routes.get(key)
            if block:
                parts.append(block)
        return "\n\n".join(parts)
    legacy = _ENTRY_SECTION.search(markdown)
    if legacy:
        tail = markdown[legacy.start() :].strip()
        next_h2 = re.search(r"\n## ", tail[1:])
        if next_h2:
            return tail[: next_h2.start() + 1].strip()
        return tail
    return ""


def study_levels_for_course_html(
    html: str,
    *,
    course_url: str = "",
    default_levels: list[str] | None = None,
) -> list[str]:
    """One UG URL with both modal routes → undergraduate + foundation markdown files."""
    defaults = list(default_levels or ["undergraduate"])
    soup = BeautifulSoup(html, "html.parser")
    dialog = soup.select_one(
        "dialog.modal-entry.entry-requirements-modal, dialog.modal-entry, #entry-requirements-1"
    )
    if dialog is None:
        return defaults
    has_degree = dialog.select_one("#entry-req-details-1") is not None
    has_foundation = dialog.select_one("#entry-req-details-2") is not None
    if has_degree and has_foundation:
        return [_ROUTE_UNDERGRADUATE, _ROUTE_FOUNDATION]
    if has_foundation and not has_degree:
        return [_ROUTE_FOUNDATION]
    if has_degree:
        return [_ROUTE_UNDERGRADUATE]
    return defaults


def _pick_entry_block(markdown: str, study_level: str | None) -> str:
    routes = _extract_entry_routes(markdown)
    if not routes:
        legacy = _ENTRY_SECTION.search(markdown)
        if legacy:
            tail = markdown[legacy.start() :].strip()
            next_h2 = re.search(r"\n## ", tail[1:])
            if next_h2:
                return tail[: next_h2.start() + 1].strip()
            return tail
        return ""

    if study_level == _ROUTE_FOUNDATION:
        return routes.get(_ROUTE_FOUNDATION, "")
    if study_level == "undergraduate":
        return routes.get(_ROUTE_UNDERGRADUATE, "")
    default = _default_entry_route(markdown)
    return routes.get(default, next(iter(routes.values()), ""))


def _build_key_facts_lines(markdown: str) -> list[str]:
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
    return lines


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Key facts + all entry routes from the modal (per-level route via extra_clean)."""
    lines = _build_key_facts_lines(markdown)
    entry = _join_entry_blocks(markdown)
    if entry:
        lines.extend(["", entry])
    return "\n".join(line for line in lines if line is not None).strip() + "\n"


def extra_clean_course_markdown_uni(markdown: str, *, study_level: str) -> str:
    """Pick foundation vs undergraduate entry route from saved modal HTML."""
    level = folder_for_level(study_level) if study_level else ""
    if level not in {_ROUTE_FOUNDATION, _ROUTE_UNDERGRADUATE}:
        return markdown

    lines = _build_key_facts_lines(markdown)
    entry = _pick_entry_block(markdown, level)
    if entry:
        lines.extend(["", entry])
    return "\n".join(line for line in lines if line is not None).strip() + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
