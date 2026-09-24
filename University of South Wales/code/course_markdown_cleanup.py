"""University of South Wales — course markdown cleanup.

Course pages (Terminal Four): masthead snapshot (duration, start, fees), entry/fee tabs,
international fee card. preprocess_course_html_uni injects #usw-stage1-facts for Stage 1 parser shapes.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import main

_IELTS_RE = re.compile(
    r"IELTS\s+([\d.]+)\s+.*?minimum\s+of\s+([\d.]+)\s+in\s+each\s+component",
    re.I | re.S,
)
_FEE_RE = re.compile(r"£([\d,]+)")
_DURATION_BUTTON_RE = re.compile(r"full-time", re.I)


def _text(el) -> str:
    if el is None:
        return ""
    return " ".join(el.get_text(" ", strip=True).split())


def _normalize_duration_label(label: str) -> str:
    text = label.strip()
    text = re.sub(r"\bYears\b", "years", text)
    text = re.sub(r"\bYear\b", "year", text)
    text = re.sub(r"\bFull-time\b", "full-time", text, flags=re.I)
    text = re.sub(r"\bPart-time\b", "part-time", text, flags=re.I)
    return text


def _normalize_duration(button_label: str) -> str:
    return _normalize_duration_label(button_label)


def _int_fee_amount_from_el(int_fee_el) -> str | None:
    h3 = int_fee_el.select_one("h3.display-3, h3")
    if h3 is None:
        return None
    match = _FEE_RE.search(_text(h3))
    return match.group(1) if match else None


def _pick_latest_year_int_fee_node(tab_content) -> object | None:
    pane_b = tab_content.select_one("#year-b-content")
    if pane_b is not None:
        for el in pane_b.select(".int-fee"):
            if _int_fee_amount_from_el(el):
                return el
    pane_a = tab_content.select_one("#year-a-content")
    if pane_a is not None:
        for el in pane_a.select(".int-fee"):
            if _int_fee_amount_from_el(el):
                return el
    return None


def _narrow_legacy_international_fees(soup: BeautifulSoup) -> None:
    span = soup.select_one("span#course-fees-anchor")
    if span is None:
        return
    outer = span.find_parent("div", id="course-fees-anchor")
    if outer is None:
        outer = span.find_parent(
            "div", class_=lambda c: c and "overflow-hidden" in str(c)
        )
    if outer is None:
        return

    tab_content = outer.select_one("#course-fees-tab-content")
    int_node = None
    if tab_content is not None:
        int_node = _pick_latest_year_int_fee_node(tab_content)
    else:
        for el in outer.select(".int-fee"):
            if _int_fee_amount_from_el(el):
                int_node = el
                break
    if int_node is None:
        return

    parsed = BeautifulSoup(str(int_node), "html.parser")
    clone = parsed.select_one(".int-fee") or parsed
    wrapper = soup.new_tag("div", id="usw-fees-section")
    wrapper.append(clone)

    section = outer.select_one("section.course-fees-entry__fees")
    if section is not None:
        for child in list(section.contents):
            if getattr(child, "decompose", None):
                child.decompose()
        section.append(wrapper)
    else:
        for child in list(outer.contents):
            if getattr(child, "decompose", None):
                child.decompose()
        outer.append(wrapper)

    for banner in outer.select(".fees-banner__text"):
        row = banner.find_parent("div", class_="row")
        if row is not None:
            row.decompose()


def _extract_int_fee_from_page(soup: BeautifulSoup) -> str | None:
    fees = soup.select_one("#usw-fees-section")
    if fees is not None:
        node = fees.select_one(".int-fee h3.display-3, .int-fee h3")
        if node is not None:
            match = _FEE_RE.search(_text(node))
            if match:
                return match.group(1)
    tab_content = soup.select_one("#course-fees-tab-content")
    if tab_content is not None:
        picked = _pick_latest_year_int_fee_node(tab_content)
        if picked is not None:
            amount = _int_fee_amount_from_el(picked)
            if amount:
                return amount
    node = soup.select_one("#course-fees-anchor .int-fee h3.display-3")
    if node:
        match = _FEE_RE.search(_text(node))
        if match:
            return match.group(1)
    for item in soup.select(".js-course-details"):
        match = re.search(
            r"International students:\s*£([\d,]+)",
            item.get_text(" ", strip=True),
            re.I,
        )
        if match:
            return match.group(1)
    fund = soup.select_one("span#course-fees-funding-anchor")
    if fund:
        section = fund.find_parent("section")
        if section:
            match = re.search(
                r"International Full-Time Fee\s*£\s*([\d,]+)",
                section.get_text(" ", strip=True),
                re.I,
            )
            if match:
                return match.group(1)
    for li in soup.select(".snapshot .accordion-body li"):
        h4 = li.find("h4")
        if h4 and "international" in _text(h4).lower():
            p = li.find("p")
            if p:
                match = _FEE_RE.search(_text(p))
                if match:
                    return match.group(1)
    return None


def _extract_ielts_line(soup: BeautifulSoup) -> str | None:
    for pane in soup.select(".tab-pane"):
        for h3 in pane.find_all("h3"):
            if "english language" in _text(h3).lower():
                for p in pane.find_all("p"):
                    raw = p.get_text(" ", strip=True)
                    match = _IELTS_RE.search(raw)
                    if match:
                        overall, section = match.group(1), match.group(2)
                        return (
                            f"IELTS {overall} overall with no less than {section} in each band"
                        )
                    if "IELTS" in raw and len(raw) < 400:
                        return raw
    return None


def _full_time_start_month(switcher) -> str:
    for item in switcher.select(".accordion-item"):
        btn = item.select_one(".accordion-button")
        if btn is None or not _DURATION_BUTTON_RE.search(_text(btn)):
            continue
        if re.search(r"part-time", _text(btn), re.I) and not re.search(
            r"full-time", _text(btn), re.I
        ):
            continue
        body = item.select_one(".accordion-body")
        for li in body.select("li") if body else []:
            h4 = li.find("h4")
            if h4 and "start date" in _text(h4).lower():
                p = li.find("p")
                if p:
                    return _text(p)
        break
    return ""


def _snapshot_start_date_lines(soup: BeautifulSoup) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for btn in soup.select(".snapshot__tabs .js-course-selector-button"):
        year_label = _text(btn)
        if not re.fullmatch(r"20\d{2}", year_label):
            continue
        data_type = (btn.get("data-type") or "").strip()
        if not data_type:
            continue
        switcher = soup.select_one(f'.js-course-switcher-content[data-type="{data_type}"]')
        if switcher is None:
            continue
        month = _full_time_start_month(switcher)
        if not month:
            continue
        line = f"- <strong>Start date:</strong> {month} {year_label}"
        if line not in seen:
            seen.add(line)
            lines.append(f"<p>{line}</p>")
    return lines


def _course_details_start_lines(soup: BeautifulSoup) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for item in soup.select(".js-course-details"):
        duration_attr = (item.get("data-duration") or "").strip()
        if not duration_attr or not re.search(r"full-time", duration_attr, re.I):
            continue
        if re.search(r"part-time", duration_attr, re.I) and not re.search(
            r"full-time", duration_attr, re.I
        ):
            continue
        for block in item.select(".course-details__summary-item"):
            labels = block.find_all("p")
            if len(labels) < 2:
                continue
            if "start date" not in _text(labels[0]).lower():
                continue
            start_text = _text(labels[1])
            if not start_text:
                continue
            line = f"- <strong>Start date:</strong> {start_text}"
            if line not in seen:
                seen.add(line)
                lines.append(f"<p>{line}</p>")
            break
    return lines


def _course_details_full_time_duration(soup: BeautifulSoup) -> str | None:
    item = soup.select_one('.js-course-details.active[data-duration*="Full-time"]')
    if item is None:
        for candidate in soup.select(".js-course-details"):
            dur = candidate.get("data-duration") or ""
            if re.search(r"full-time", dur, re.I) and not re.fullmatch(
                r".*part-time.*", dur, re.I
            ):
                item = candidate
                break
    if item is None:
        return None
    return _normalize_duration_label(item.get("data-duration") or "")


def _build_stage1_facts_html_new(soup: BeautifulSoup) -> str | None:
    if not soup.select_one(".course-details[data-switcher-init], .masthead-course-new"):
        return None
    duration = _course_details_full_time_duration(soup)
    int_fee = _extract_int_fee_from_page(soup)
    start_lines = _course_details_start_lines(soup)
    if not duration and not int_fee and not start_lines:
        return None
    duration_line = (
        f"<p><strong>Duration:</strong> {duration}</p>" if duration else ""
    )
    fee_line = f"<p>Annual tuition fees: | £{int_fee}</p>" if int_fee else ""
    ielts = _extract_ielts_line(soup)
    ielts_line = f"<p>{ielts}</p>" if ielts else ""
    return f"{duration_line}{''.join(start_lines)}{fee_line}{ielts_line}"


def _strip_additional_information_block(container) -> None:
    for h3 in container.find_all("h3"):
        if "additional information" not in _text(h3).lower():
            continue
        sibling = h3.find_next_sibling()
        h3.decompose()
        while sibling is not None and getattr(sibling, "name", None) != "h3":
            nxt = sibling.find_next_sibling()
            sibling.decompose()
            sibling = nxt


def _normalize_typical_requirements_headings(container) -> None:
    for h in container.find_all(["h3", "h4"]):
        label = _text(h).strip().rstrip(":").lower()
        if label == "typical requirements":
            h.name = "h3"
            h.clear()
            h.append("Typical qualification requirements:")


def _has_typical_qualification_heading(container) -> bool:
    for h in container.find_all(["h3", "h4"]):
        if "typical qualification" in _text(h).lower():
            return True
    return False


def _page_has_course_ielts_entry(soup: BeautifulSoup) -> bool:
    for p in soup.find_all("p"):
        raw = _text(p).lower()
        if "international applicants" in raw and "ielts" in raw:
            return True
    return False


def _ensure_default_pg_english_entry(soup: BeautifulSoup, entry_wrap) -> None:
    if soup.select_one("#usw-international-entry") or _page_has_course_ielts_entry(soup):
        return
    block = soup.new_tag("div")
    block["id"] = "usw-international-entry"
    h3 = soup.new_tag("h3")
    h3.string = "English language requirements"
    p = soup.new_tag("p")
    p.string = (
        "International applicants will need to have achieved an overall of IELTS 6.0 "
        "with a minimum of 5.5 in each component (or equivalent)."
    )
    block.append(h3)
    block.append(p)
    entry_wrap.append(block)


def _tag_entry_requirements_tab_as_typical(soup: BeautifulSoup, container) -> None:
    if container is None or container.select_one("#usw-typical-entry"):
        return
    tab_content = container.select_one(".tab-content")
    if tab_content is None:
        return
    pane = None
    tablist = container.select_one('[role="tablist"]')
    if tablist is not None:
        for btn in tablist.select("button.nav-link, .nav-link[data-bs-toggle]"):
            if _text(btn).lower() != "entry requirements":
                continue
            tab_id = btn.get("data-bs-target", "").strip().lstrip("#")
            if tab_id:
                pane = tab_content.select_one(f"#{tab_id}")
            break
    if pane is None:
        return
    pane["id"] = "usw-typical-entry"
    _normalize_typical_requirements_headings(pane)
    if not _has_typical_qualification_heading(pane):
        target_p = None
        for p in pane.find_all("p"):
            prev = p.find_previous(["h3", "h4"])
            if prev is not None and "additional requirements" in _text(prev).lower():
                continue
            if len(_text(p)) >= 40:
                target_p = p
                break
        heading = soup.new_tag("h3")
        heading.string = "Typical qualification requirements:"
        if target_p is not None:
            target_p.insert_before(heading)
        else:
            pane.insert(0, heading)
    for nav in pane.select(".nav.nav-pills, a.btn, a.btn-secondary"):
        nav.decompose()
    _strip_additional_information_block(pane)


def _tag_typical_entry_block(soup: BeautifulSoup, container) -> None:
    if container is None:
        return
    for pane in container.select(".tab-pane"):
        _normalize_typical_requirements_headings(pane)
        if _has_typical_qualification_heading(pane):
            pane["id"] = "usw-typical-entry"
            for nav in pane.select(".nav.nav-pills"):
                nav.decompose()
            _strip_additional_information_block(pane)
            return
    for divider in container.select(".course-fees-entry__divider"):
        if "typical qualification" not in divider.get_text(" ", strip=True).lower():
            continue
        divider["id"] = "usw-typical-entry"
        stat = divider.select_one(".entry-stat")
        if stat:
            value_node = stat.select_one(".entry-stat__value")
            points = _text(value_node) if value_node else ""
            if points:
                heading = soup.new_tag("h2")
                heading.string = f"UCAS points: {points} (or above)"
                stat.replace_with(heading)
        for nav in divider.select(".nav.nav-pills, .btn, a.btn"):
            nav.decompose()
        _strip_additional_information_block(divider)
        _normalize_typical_qualification_html(soup, divider)
        return
    _tag_entry_requirements_tab_as_typical(soup, container)


def _normalize_typical_qualification_html(soup: BeautifulSoup, divider) -> None:
    for h4 in divider.find_all("h4"):
        if "typical qualification" in _text(h4).lower():
            h4.name = "h3"
            h4.clear()
            h4.append("Typical qualification requirements:")
    qual_labels = (
        "a level",
        "btec",
        "access to he",
        "t level",
        "welsh baccalaureate",
    )
    for p in list(divider.find_all("p")):
        strong = p.find("strong")
        if strong is None:
            continue
        label = _text(strong).rstrip(":").strip()
        label_key = label.lower()
        if label_key.startswith("additional requirements"):
            h3 = soup.new_tag("h3")
            h3.string = "Additional requirements include:"
            rest = _text(p).split(":", 1)[-1].strip()
            p.replace_with(h3)
            if rest:
                np = soup.new_tag("p")
                np.string = rest
                h3.insert_after(np)
            continue
        if not any(label_key.startswith(q) for q in qual_labels):
            continue
        rest = _text(p).replace(_text(strong), "", 1).strip()
        if not rest:
            continue
        ul = divider.find("ul")
        if ul is None:
            ul = soup.new_tag("ul")
            h3 = divider.find("h3")
            if h3 is not None:
                h3.insert_after(ul)
            else:
                divider.insert(0, ul)
        li = soup.new_tag("li")
        li.string = f"{label}: {rest}"
        ul.append(li)
        p.decompose()


_ENGLISH_ENTRY_BOILERPLATE_PATTERNS = (
    re.compile(r"^Equivalents can be located on our\b", re.I),
    re.compile(r"^If you have previously studied through the medium of English\b", re.I),
    re.compile(r"^If you do not meet the English entry criteria\b", re.I),
    re.compile(r"^- International Students\s*$", re.I),
    re.compile(r"^- Pre-Sessional English\s*$", re.I),
)


def _is_english_entry_boilerplate_line(line: str) -> bool:
    stripped = line.strip()
    return any(p.search(stripped) for p in _ENGLISH_ENTRY_BOILERPLATE_PATTERNS)


_ENGLISH_ENTRY_BOILERPLATE_START_RE = re.compile(
    r"(?:Equivalents can be located|If you have previously studied through the medium of English|If you do not meet the English entry criteria)",
    re.I,
)


def _strip_english_entry_boilerplate_html(pane) -> None:
    for p in list(pane.find_all("p")):
        raw = _text(p)
        raw_lower = raw.lower()
        if _ENGLISH_ENTRY_BOILERPLATE_START_RE.search(raw) and (
            "ielts" in raw_lower or "international applicants" in raw_lower
        ):
            first = _ENGLISH_ENTRY_BOILERPLATE_START_RE.split(raw, maxsplit=1)[0].strip()
            if first:
                p.clear()
                p.string = first
            else:
                p.decompose()
            continue
        if (
            "equivalents can be located" in raw_lower
            or "previously studied through the medium of english" in raw_lower
            or "pre-sessional course pages" in raw_lower
        ):
            p.decompose()
    for nav in pane.select(".nav.nav-pills, ul.nav"):
        nav.decompose()
    for h3 in pane.find_all("h3"):
        if "international applications welcomed" in _text(h3).lower():
            col = h3.find_parent("div", class_="course-fees-entry__text")
            if col is not None:
                col.decompose()


def _tag_entry_and_fee_blocks(soup: BeautifulSoup) -> None:
    for pane in soup.select(".tab-pane"):
        for h3 in pane.find_all("h3"):
            if "english language" in _text(h3).lower():
                pane["id"] = "usw-international-entry"
                _strip_english_entry_boilerplate_html(pane)
                break

    req_anchor = soup.select_one("span#course-requirements-anchor")
    if req_anchor:
        entry_wrap = req_anchor.find_parent("div", class_="course-fees-entry")
        if entry_wrap is not None:
            entry_wrap["id"] = "usw-entry-requirements"
            _tag_typical_entry_block(soup, entry_wrap)
            _ensure_default_pg_english_entry(soup, entry_wrap)

    entry_anchor = soup.select_one("span#course-fees-entry-anchor")
    if entry_anchor:
        entry_section = entry_anchor.find_parent("section")
        if entry_section is not None:
            _tag_typical_entry_block(soup, entry_section)

    funding_anchor = soup.select_one("span#course-fees-funding-anchor")
    if funding_anchor:
        funding_section = funding_anchor.find_parent("section")
        if funding_section is not None:
            int_panes = [
                pane
                for pane in funding_section.select(".tab-pane")
                if "International Full-Time Fee" in pane.get_text(" ", strip=True)
            ]
            pane = int_panes[-1] if int_panes else None
            if pane is None:
                pane_b = funding_section.select_one("#year-b-content")
                if pane_b is not None and "International" in pane_b.get_text(" ", strip=True):
                    pane = pane_b
            if pane is not None:
                pane["id"] = "usw-fees-section"
                for node in pane.select(".accordion, a.btn, a.btn-new, .home-fee, .pt-fee"):
                    node.decompose()


def _inject_stage1_facts(soup: BeautifulSoup) -> None:
    facts_html = _build_stage1_facts_html_new(soup) or _build_stage1_facts_html(soup)
    if not facts_html:
        return
    wrapper = BeautifulSoup(f"<div id='usw-stage1-facts'>{facts_html}</div>", "html.parser")
    facts_node = wrapper.find(id="usw-stage1-facts")
    if facts_node is None:
        return
    masthead = soup.select_one(".masthead-course__text, .masthead-course-new__text")
    if masthead:
        masthead.insert_before(facts_node)


def _build_stage1_facts_html(soup: BeautifulSoup) -> str | None:
    switcher = soup.select_one('.js-course-switcher-content[data-type="course_a"]')
    if switcher is None:
        switcher = soup.select_one(".js-course-switcher-content")

    duration = None
    int_fee = _extract_int_fee_from_page(soup)

    if switcher:
        for item in switcher.select(".accordion-item"):
            btn = item.select_one(".accordion-button")
            if btn is None or not _DURATION_BUTTON_RE.search(_text(btn)):
                continue
            if re.search(r"part-time", _text(btn), re.I) and not re.search(
                r"full-time", _text(btn), re.I
            ):
                continue
            duration = _normalize_duration(_text(btn))
            break

    if not duration and not int_fee:
        return None

    start_lines = _snapshot_start_date_lines(soup)
    if not start_lines and switcher:
        month = _full_time_start_month(switcher)
        if month:
            start_lines = [f"<p>- <strong>Start date:</strong> {month}</p>"]

    start_block = "".join(start_lines)

    duration_line = ""
    if duration:
        duration_line = f"<p><strong>Duration:</strong> {duration}</p>"

    fee_line = ""
    if int_fee:
        fee_line = f"<p>Annual tuition fees: | £{int_fee}</p>"

    ielts = _extract_ielts_line(soup)
    ielts_line = f"<p>{ielts}</p>" if ielts else ""

    return (
        f"{duration_line}{start_block}{fee_line}{ielts_line}"
    )


def preprocess_course_html_uni(soup: BeautifulSoup) -> None:
    """Unhide tabs, strip marketing noise, inject Stage 1 fact block."""
    for selector in (
        ".course-page-nav",
        "#course-highlights-anchor",
        "section.course-design",
        "#course-modules-anchor",
        ".tabs-img-text",
        ".swiper",
        ".make-an-enquiry",
    ):
        for node in soup.select(selector):
            node.decompose()

    for hidden in soup.select('.js-course-switcher-content[style*="display: none"]'):
        hidden["style"] = ""

    _narrow_legacy_international_fees(soup)

    for pane in soup.select(".tab-pane"):
        classes = [c for c in pane.get("class", []) if c != "fade"]
        if "show" not in classes:
            classes.extend(["show", "active"])
        pane["class"] = classes

    for collapse in soup.select(".accordion-collapse"):
        classes = list(collapse.get("class", []))
        if "show" not in classes:
            classes.append("show")
        collapse["class"] = classes

    _tag_entry_and_fee_blocks(soup)
    _inject_stage1_facts(soup)


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Normalize Stage 1 shapes and drop accordion placeholder lines."""
    lines_out: list[str] = []
    for line in markdown.splitlines():
        if re.match(r"^\s*[\[\]]\s*$", line):
            continue
        stripped = line.strip()
        if re.match(r"^Tab\s+\d+\s*$", stripped, re.I):
            continue
        if re.match(r"^eo\s+Tab\s+\d+", stripped, re.I):
            continue
        if re.match(r"^UK Full-time Fee\s*$", stripped, re.I):
            continue
        if re.match(r"^per year\* UK Full-time Fee\s*$", stripped, re.I):
            continue
        if _is_english_entry_boilerplate_line(line):
            continue
        m = re.match(r"^Duration:\s*(.+)$", stripped, re.I)
        if m:
            lines_out.append(f"**Duration:** {m.group(1).strip()}")
            continue
        m = re.match(r"^-\s*Start date:\s*(.+)$", stripped, re.I)
        if m:
            lines_out.append(f"- **Start date:** {m.group(1).strip()}")
            continue
        lines_out.append(line.rstrip())
    text = "\n".join(lines_out)
    text = re.sub(
        r"International applicants will need to have achieved an overall of IELTS\s+([\d.]+)\s+with a minimum of\s+([\d.]+)\s+in each component",
        r"International applicants will need to have achieved an IELTS \1 overall with no less than \2 in each band",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"International applicants will need to have achieved an IELTS\s+([\d.]+)\s+with a minimum of\s+([\d.]+)\s+in each component",
        r"International applicants will need to have achieved an IELTS \1 overall with no less than \2 in each band",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"IELTS\s+([\d.]+)\s+with a minimum of\s+([\d.]+)\s+in each component",
        r"IELTS \1 overall with no less than \2 in each band",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"overall of IELTS\s+([\d.]+)\s+with a minimum of\s+([\d.]+)\s+in each component",
        r"IELTS \1 overall with no less than \2 in each band",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"overall of IELTS\s+([\d.]+)\s+overall with no less than",
        r"IELTS \1 overall with no less than",
        text,
        flags=re.I,
    )
    text = re.sub(r"\banHND/HNCand\b", "an HND/HNC and", text, flags=re.I)
    text = re.sub(r"\ban\s+HND/HNC\s+and\b", "an HND/HNC and", text, flags=re.I)
    text = re.sub(
        r"## Typical entry\n\n(\d+)\nUCAS points or above",
        r"## Typical entry\n\n## UCAS points: \1 (or above)",
        text,
    )
    text = re.sub(
        r"\nTypical qualification requirements:\n",
        r"\n### Typical qualification requirements:\n\n",
        text,
    )
    text = re.sub(
        r"^### Typical requirements:\s*\n+\s*### Typical qualification requirements:",
        "### Typical qualification requirements:",
        text,
        flags=re.I | re.M,
    )
    text = re.sub(
        r"^### Typical requirements:\s*$",
        "### Typical qualification requirements:",
        text,
        flags=re.I | re.M,
    )
    text = re.sub(
        r"^A Level\s*([A-Z]{2,4})\s*$",
        r"- A Level: \1",
        text,
        flags=re.I | re.M,
    )
    text = re.sub(
        r"^AAT\s*(.+)$",
        r"- AAT: \1",
        text,
        flags=re.I | re.M,
    )
    text = re.sub(
        r"^Welsh Baccalaureate:\s*",
        r"- Welsh Baccalaureate: ",
        text,
        flags=re.I | re.M,
    )
    text = re.sub(r"^BTEC:\s*", r"- BTEC: ", text, flags=re.I | re.M)
    text = re.sub(r"^Access to HE:\s*", r"- Access to HE: ", text, flags=re.I | re.M)
    text = re.sub(r"^T Level:\s*", r"- T Level: ", text, flags=re.I | re.M)
    lines = text.splitlines()
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
