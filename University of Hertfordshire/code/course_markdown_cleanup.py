"""University of Hertfordshire — course HTML preprocess + markdown cleanup."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, Comment

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

import importlib.util

_SHARED_CMD = _SHARED / "course_markdown_cleanup.py"
_spec = importlib.util.spec_from_file_location("_shared_course_markdown_cleanup", _SHARED_CMD)
assert _spec and _spec.loader
_shared_cmd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_shared_cmd)
MarkdownSectionRemover = _shared_cmd.MarkdownSectionRemover
main = _shared_cmd.main


def _expand_hidden_course_sections(soup: BeautifulSoup) -> None:
    for pane in soup.select(".tab-pane"):
        if pane.get("style"):
            style = pane["style"]
            if "display" in style.lower() and "none" in style.lower():
                pane["style"] = re.sub(
                    r"display\s*:\s*none\s*;?",
                    "",
                    style,
                    flags=re.I,
                )
        classes = list(pane.get("class", []))
        for extra in ("show", "active"):
            if extra not in classes:
                classes.append(extra)
        pane["class"] = classes

    for collapse in soup.select(".accordion-collapse"):
        classes = list(collapse.get("class", []))
        if "show" not in classes:
            classes.append("show")
        collapse["class"] = classes


def _prune_inactive_tab_panes(soup: BeautifulSoup, tabs_root: str) -> None:
    root = soup.select_one(tabs_root)
    if not root:
        return
    tab_content = root.select_one(".tab-content")
    if not tab_content:
        return
    panes = tab_content.select(".tab-pane")
    if len(panes) <= 1:
        return
    active = tab_content.select_one(".tab-pane.active")
    active_nav = root.select_one(".nav-tabs .nav-link.active")
    if active_nav and not active:
        target = (active_nav.get("data-bs-target") or "").lstrip("#")
        if target:
            active = tab_content.select_one(f"#{target}")
    if not active:
        visible = [
            pane
            for pane in panes
            if "display: none" not in (pane.get("style") or "").lower()
            and "display:none" not in (pane.get("style") or "").lower()
        ]
        active = visible[-1] if visible else panes[-1]
    for pane in panes:
        if pane is not active:
            pane.decompose()


def _international_fee_line(soup: BeautifulSoup) -> str:
    scope = soup.select_one("#fees-And-Funding-Tabs .tab-pane.active")
    if not scope:
        scope = soup.select_one("#fees") or soup
    for row in scope.select("table tr"):
        header = row.select_one("th")
        if not header:
            continue
        if "international" not in header.get_text(" ", strip=True).casefold():
            continue
        cells = row.select("td")
        if not cells:
            continue
        fee = cells[-1].get_text(" ", strip=True)
        if "£" in fee:
            return fee
    return ""


def _uses_description_list_layout(soup: BeautifulSoup) -> bool:
    """Taught PG and research pages use ul.description-list slides instead of #fees / #entryRequirements."""
    if soup.select_one("#entryRequirements"):
        return False
    return bool(soup.select_one("ul.description-list li.slidedown"))


def _description_list_slidedown(
    soup: BeautifulSoup,
    heading_prefix: str,
):
    prefix = heading_prefix.casefold()
    for li in soup.select("ul.description-list li.slidedown"):
        head = li.get_text("\n", strip=True).split("\n", 1)[0].strip().casefold()
        if head.startswith(prefix):
            return li
    return None


def _entry_requirements_slidedown(soup: BeautifulSoup):
    return _description_list_slidedown(soup, "entry requirements")


def _ielts_from_research_description_list(soup: BeautifulSoup) -> str:
    for li in soup.select("ul.description-list li.slidedown"):
        text = li.get_text(" ", strip=True)
        if "entry requirements" not in text.casefold():
            continue
        match = re.search(
            r"IELTS\s+entry\s+requirement\s+is\s+normally\s+([\d.]+)",
            text,
            re.I,
        )
        if match:
            return f"IELTS {match.group(1)} overall"
        match = re.search(
            r"IELTS\s+score\s+of\s+([\d.]+)\s+with\s+a\s+minimum\s+of\s+([\d.]+)\s+in\s+each\s+band",
            text,
            re.I,
        )
        if match:
            return (
                f"IELTS {match.group(1)} overall with no less than {match.group(2)} in each band"
            )
    return ""


def _clone_tag_tree(soup: BeautifulSoup, node) -> BeautifulSoup:
    return BeautifulSoup(str(node), "html.parser")


def _inject_description_list_sections(soup: BeautifulSoup) -> None:
    """Map description-list slides to #entryRequirements and #fees for COURSE_CLEAN_BLOCKS."""
    if not _uses_description_list_layout(soup):
        return

    anchor = (
        soup.select_one("h1.course-hero-heading")
        or soup.select_one("main h1")
        or soup.select_one("main")
    )
    if not anchor:
        return

    if not soup.select_one("#entryRequirements"):
        entry_li = _entry_requirements_slidedown(soup)
        contents = entry_li.select_one(".slide-contents") if entry_li else None
        if contents:
            root = soup.new_tag("div", id="entryRequirements")
            h2 = soup.new_tag("h2")
            h2.string = "Entry requirements"
            root.append(h2)
            body = soup.new_tag("div")
            cloned = _clone_tag_tree(soup, contents)
            for child in cloned.children:
                if getattr(child, "name", None):
                    body.append(child)
            root.append(body)
            anchor.insert_after(root)

    if not soup.select_one("#fees"):
        fees_li = _description_list_slidedown(soup, "funding")
        contents = fees_li.select_one(".slide-contents") if fees_li else None
        if contents:
            root = soup.new_tag("div", id="fees")
            h2 = soup.new_tag("h2")
            h2.string = "Fees and funding"
            root.append(h2)
            body = soup.new_tag("div")
            cloned = _clone_tag_tree(soup, contents)
            for child in cloned.children:
                if getattr(child, "name", None):
                    body.append(child)
            root.append(body)
            if soup.select_one("#entryRequirements"):
                soup.select_one("#entryRequirements").insert_after(root)
            else:
                anchor.insert_after(root)


def _ielts_from_entry(soup: BeautifulSoup) -> str:
    for table in soup.select("#entryRequirements table"):
        text = table.get_text(" ", strip=True)
        match = re.search(
            r"IELTS\s+score\s+of\s+([\d.]+)\s+with\s+a\s+minimum\s+of\s+([\d.]+)\s+in\s+each\s+band",
            text,
            re.I,
        )
        if match:
            return (
                f"IELTS {match.group(1)} overall with no less than {match.group(2)} in each band"
            )
    for block in soup.select("#entryRequirements p"):
        text = block.get_text(" ", strip=True)
        match = re.search(
            r"IELTS\s+entry\s+requirement\s+is\s+normally\s+([\d.]+)",
            text,
            re.I,
        )
        if match:
            return f"IELTS {match.group(1)} overall"
        match = re.search(
            r"IELTS\s+score\s+of\s+([\d.]+)\s+with\s+a\s+minimum\s+of\s+([\d.]+)\s+in\s+each\s+band",
            text,
            re.I,
        )
        if match:
            return (
                f"IELTS {match.group(1)} overall with no less than {match.group(2)} in each band"
            )
    return _ielts_from_research_description_list(soup)


def _intake_start_dates(soup: BeautifulSoup) -> str:
    dates: list[str] = []
    for cell in soup.select("#apply table td"):
        text = cell.get_text(" ", strip=True)
        if re.fullmatch(
            r"(January|February|March|April|May|June|July|August|September|"
            r"October|November|December)\s+\d{4}",
            text,
            re.I,
        ):
            dates.append(text)
    return ", ".join(dict.fromkeys(dates))


def _duration_from_description_list(soup: BeautifulSoup) -> str:
    entry_li = _entry_requirements_slidedown(soup)
    contents = entry_li.select_one(".slide-contents") if entry_li else None
    if not contents:
        return ""
    for row in contents.select("table tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        label = cells[0].get_text(" ", strip=True).casefold()
        if "course length" not in label:
            continue
        for line in cells[1].get_text("\n", strip=True).split("\n"):
            line = line.strip()
            if re.match(r"Full\s*Time\b", line, re.I):
                return line
    return ""


def _duration_from_course_length(soup: BeautifulSoup) -> str:
    """Course length from description-list table or fees accordion td.course-length-data."""
    from_list = _duration_from_description_list(soup)
    if from_list:
        return from_list
    cell = soup.select_one("td.course-length-data")
    if not cell:
        return ""
    raw = re.sub(r"<br\s*/?>", "\n", cell.decode_contents(), flags=re.I)
    lines: list[str] = []
    for chunk in raw.split("\n"):
        line = BeautifulSoup(chunk, "html.parser").get_text(" ", strip=True)
        if line:
            lines.append(line)
    full_time = [ln for ln in lines if re.match(r"Full\s*Time\b", ln, re.I)]
    if full_time:
        return full_time[0]
    return ""


def _filter_tuition_fee_tables(soup: BeautifulSoup) -> None:
    """Keep only International students / Full time in tuition fee tables."""
    fees_root = soup.select_one("#fees")
    if not fees_root:
        return
    for table in fees_root.select("table"):
        if not any(
            "study type" in th.get_text(" ", strip=True).lower()
            for th in table.select("th")
        ):
            continue
        tbody = table.find("tbody")
        if not tbody:
            continue
        fee_text = ""
        for tr in tbody.find_all("tr", recursive=False):
            th = tr.find("th")
            tds = tr.find_all("td")
            if not th or not tds:
                continue
            if "international" not in th.get_text(" ", strip=True).casefold():
                continue
            if "full time" not in tds[0].get_text(" ", strip=True).casefold():
                continue
            fee_text = tds[-1].get_text(" ", strip=True)
            break
        if not fee_text:
            continue
        for tr in tbody.find_all("tr"):
            tr.decompose()
        row = soup.new_tag("tr")
        for cell_text in ("International students", "Full time", fee_text):
            cell = soup.new_tag("td")
            cell.string = cell_text
            row.append(cell)
        tbody.append(row)


def _remove_non_international_fee_headings(soup: BeautifulSoup) -> None:
    """Drop UK/EU fee subsections under #fees (keep International Students)."""
    fees_root = soup.select_one("#fees")
    if not fees_root:
        return
    for tag in fees_root.find_all(re.compile(r"^h[3-6]$", re.I)):
        label = tag.get_text(" ", strip=True).casefold()
        if label not in {"uk students", "eu students"}:
            continue
        level = int(tag.name[1])
        to_remove = [tag]
        for sibling in tag.find_next_siblings():
            if getattr(sibling, "name", None) and re.match(r"^h[1-6]$", sibling.name, re.I):
                sib_level = int(sibling.name[1])
                if sib_level <= level:
                    break
            to_remove.append(sibling)
        for node in to_remove:
            node.decompose()


def _trim_fees_boilerplate(soup: BeautifulSoup) -> None:
    """Drop annual-fee disclaimer and additional-funding tables from #fees."""
    fees_root = soup.select_one("#fees")
    if not fees_root:
        return
    for paragraph in fees_root.find_all("p"):
        if "Tuition fees are charged annually" in paragraph.get_text(" ", strip=True):
            paragraph.decompose()
    for accordion in fees_root.select(".accordion-item"):
        button = accordion.select_one(".accordion-button")
        if not button:
            continue
        if "additional information" in button.get_text(" ", strip=True).casefold():
            accordion.decompose()
    for table in fees_root.select("table"):
        if any(
            "study type" in th.get_text(" ", strip=True).lower()
            for th in table.select("th")
        ):
            continue
        table.decompose()


def _inject_stage1_facts(
    soup: BeautifulSoup,
    catalog_listing_intake_months: list[str] | None = None,
    *,
    duration: str | None = None,
) -> None:
    if duration is None:
        duration = _duration_from_course_length(soup)
    int_fee = _international_fee_line(soup)
    ielts = _ielts_from_entry(soup)
    intake = _intake_start_dates(soup)
    if catalog_listing_intake_months:
        from listing_intake_merge import merge_catalog_months_with_page_intakes

        intake = merge_catalog_months_with_page_intakes(
            intake,
            catalog_listing_intake_months,
        )

    if not any((duration, int_fee, ielts, intake)):
        return

    facts = soup.new_tag("div", id="herts-stage1-facts")

    if intake:
        p = soup.new_tag("p")
        strong = soup.new_tag("strong")
        strong.string = "Start dates:"
        p.append(strong)
        p.append(f" {intake}")
        facts.append(p)

    if duration:
        p = soup.new_tag("p")
        strong = soup.new_tag("strong")
        strong.string = "Duration:"
        p.append(strong)
        p.append(f" {duration}")
        facts.append(p)

    if int_fee:
        p = soup.new_tag("p")
        strong = soup.new_tag("strong")
        strong.string = "International tuition fee:"
        p.append(strong)
        p.append(f" {int_fee}")
        facts.append(p)

    if ielts:
        p = soup.new_tag("p")
        p.string = ielts
        facts.append(p)

    anchor = soup.select_one("#courseInfo") or soup.select_one("main")
    if anchor:
        anchor.insert_before(facts)


def preprocess_course_html_uni(
    soup: BeautifulSoup,
    *,
    catalog_listing_intake_months: list[str] | None = None,
) -> None:
    """Unhide Bootstrap tabs/accordions; inject Stage 1 fact block."""
    for noisy in soup.select(
        "#course-sticky-nav, .videoWrapper, #CybotCookiebotDialog"
    ):
        noisy.decompose()

    for overview in soup.select("#course-overview > h2"):
        overview.decompose()

    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    for clearing in soup.select(
        ".clearing-btn-3, .clearing-entry-req-text, #apply h2.link-decoration"
    ):
        clearing.decompose()

    _prune_inactive_tab_panes(soup, "#entry-Requirements-Tabs")
    _prune_inactive_tab_panes(soup, "#fees-And-Funding-Tabs")
    _expand_hidden_course_sections(soup)
    _inject_description_list_sections(soup)
    duration_for_facts = _duration_from_course_length(soup)
    _filter_tuition_fee_tables(soup)
    _remove_non_international_fee_headings(soup)
    _trim_fees_boilerplate(soup)
    _inject_stage1_facts(
        soup,
        catalog_listing_intake_months,
        duration=duration_for_facts,
    )


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Drop empty accordion placeholders and tab chrome."""
    lines_out: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped in {"[", "]"}:
            continue
        if re.match(r"^UK applicants\s*$", stripped, re.I):
            continue
        if re.match(r"^Tab \d+ content\b", stripped, re.I):
            continue
        if stripped.lower() in {"how-to-apply-table", "ready to apply?"}:
            continue
        if re.match(r"^##\s+Ready to apply\?\s*$", stripped, re.I):
            continue
        if stripped.startswith("Ready to apply – CLEARING"):
            continue
        if re.search(r"financial support available to UK and EU students", stripped, re.I):
            continue
        lines_out.append(line.rstrip())
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines_out)).strip() + "\n"
    for heading in ("UK Students", "EU Students", "UK students", "EU students"):
        text = MarkdownSectionRemover.remove_heading_section(
            text,
            heading=heading,
            level=4,
            until_level=4,
        )
    return text


if __name__ == "__main__":
    raise SystemExit(main())
