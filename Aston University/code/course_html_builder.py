"""Aston University Drupal course page HTML → markdown helpers."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from clean_config import CleanConfig
from engines.generic import GenericCourseHtmlEngine
from markdown_converter import MarkdownConverter


def _strip_entry_requirement_noise(item: Tag) -> None:
    for node in item.select(".col-second, table, a.clearing-btn, .clearing-vacancies-cta"):
        node.decompose()


def _format_entry_requirement_item(item: Tag) -> list[str]:
    _strip_entry_requirement_noise(item)
    lines: list[str] = []
    for paragraph in item.select("p"):
        text = paragraph.get_text(" ", strip=True)
        if not text:
            continue
        strong = paragraph.select_one("strong")
        if strong:
            label = strong.get_text(strip=True).rstrip(":")
            rest = text.replace(strong.get_text(strip=True), "", 1).strip().lstrip(":").strip()
            if rest:
                lines.append(f"- **{label}:** {rest}")
            else:
                lines.append(f"- **{label}**")
        else:
            lines.append(f"- {text}")
    return lines


def _format_key_information(key_info: Tag) -> list[str]:
    lines: list[str] = []
    for field in key_info.select(".field.field--label-above"):
        label_el = field.select_one(".field--label")
        item_el = field.select_one(".field--item")
        if not label_el or not item_el:
            continue
        label = label_el.get_text(strip=True)
        label_key = label.strip().lower()

        if label_key == "entry requirements":
            entry_lines = _format_entry_requirement_item(item_el)
            if entry_lines:
                lines.extend(["### Entry requirements", ""] + entry_lines + [""])
            continue

        value = item_el.get_text(" ", strip=True)
        if value:
            lines.append(f"**{label}:** {value}")
            lines.append("")

    start_date = key_info.select_one(".cr_start_date .select2-selection__rendered")
    if start_date:
        date_text = start_date.get_text(strip=True)
        if date_text:
            lines.extend(["**Start date**", "", date_text, ""])
    elif key_info.select_one(".cr_start_date select option[selected]"):
        date_text = key_info.select_one(".cr_start_date select option[selected]").get_text(strip=True)
        if date_text:
            lines.extend(["**Start date**", "", date_text, ""])

    return lines


def _format_header_intro(block_root: Tag) -> list[str]:
    lines: list[str] = []
    award = block_root.select_one(".field--name-field-course-award .field--item")
    if award:
        text = award.get_text(" ", strip=True)
        if text:
            lines.extend([text, ""])

    body = block_root.select_one(".field--name-body")
    if body:
        for paragraph in body.select("p"):
            text = paragraph.get_text(" ", strip=True)
            if text:
                lines.append(text)
        if lines and lines[-1] != "":
            lines.append("")

    clearing = block_root.select_one(".clearing-vacancies-cta")
    if clearing:
        text = clearing.get_text(" ", strip=True)
        if text:
            lines.append(text)
            lines.append("")

    return lines


def format_aston_course_page_header(block_root: Tag) -> str:
    lines: list[str] = []
    lines.extend(_format_header_intro(block_root))
    key_info = block_root.select_one(".key-information-wrapper")
    if key_info:
        lines.extend(_format_key_information(key_info))
    return "\n".join(line for line in lines if line is not None).strip()


def _strip_aston_marketing_html(root: Tag) -> None:
    """Remove carousels, modals, and Power Skills markup before markdown conversion."""
    for node in root.select(
        ".modal, .slick, .slick-slider, .two-col-left, "
        ".paragraph--type--student-life-at-aston-university, "
        ".paragraph--type--student-life-card"
    ):
        node.decompose()

    for node in list(root.find_all(string=re.compile(r"ASTON POWER SKILLS", re.I))):
        parent = node.find_parent(["div", "section", "article", "p"])
        if parent is not None:
            parent.decompose()


def requirements_grid_to_markdown(root: Tag) -> str:
    parts: list[str] = []
    for grid in root.select(".requirements-grid"):
        for card in grid.select(".requirement-card"):
            heading = card.select_one("h3")
            value = card.select_one("p")
            if not heading or not value:
                continue
            title = heading.get_text(strip=True)
            text = value.get_text(" ", strip=True)
            if title and text:
                parts.extend([f"### {title}", "", text, ""])
    return "\n".join(parts).strip()


class CourseHtmlEngine(GenericCourseHtmlEngine):
    """Aston Drupal bbd-course-page extraction."""

    @classmethod
    def block_body(
        cls,
        soup,
        block_root: Tag,
        resolved_selector: str,
        env_heading: str | None,
        clean_config: CleanConfig,
    ) -> str:
        selector = resolved_selector.strip()
        if selector == ".course-page-header" or "course-page-header" in selector:
            return format_aston_course_page_header(block_root)

        if "field-content-sections" in selector:
            clone_soup = BeautifulSoup(str(block_root), "html.parser")
            clone = clone_soup.find(True) or clone_soup
            _strip_aston_marketing_html(clone)
            grid_markdown = requirements_grid_to_markdown(clone)
            for grid in clone.select(".requirements-grid"):
                grid.decompose()
            body = super().block_body(soup, clone, resolved_selector, env_heading, clean_config)
            if not grid_markdown:
                return body
            if grid_markdown in body:
                return body
            # Insert grid cards after clearing heading / intro when present.
            if "Clearing entry requirements" in body:
                body = re.sub(
                    r"(## Clearing entry requirements\n\n(?:Open to[^\n]+\n\n)?)",
                    r"\1" + grid_markdown + "\n\n",
                    body,
                    count=1,
                )
                return body.strip()
            return f"{grid_markdown}\n\n{body}".strip() if body else grid_markdown

        return super().block_body(soup, block_root, resolved_selector, env_heading, clean_config)


course_html_engine = CourseHtmlEngine()
