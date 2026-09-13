"""Default course HTML → markdown engine (most universities)."""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from clean_config import CleanConfig
from engines._helpers import (
    block_has_tabs,
    derive_heading_from_block,
    overseas_fee_from_napier_table,
    section_body_without_duplicate_heading,
    strip_within_block,
)
from markdown_converter import MarkdownConverter


class GenericCourseHtmlEngine:
    """CSS block extraction with optional r-tabs expansion."""

    @staticmethod
    def napier_course_title(soup: BeautifulSoup) -> str:
        h1 = soup.select_one("h1.courseHeaderText")
        if not h1:
            h1 = soup.select_one("h1")
        if not h1:
            return ""

        award = h1.select_one(".course-award")
        title = h1.select_one(".course-title")
        if award and title:
            text = f"{award.get_text(' ', strip=True)} {title.get_text(' ', strip=True)}"
        else:
            text = h1.get_text(" ", strip=True)

        subtitle = soup.select_one(".pageSubtitle")
        if subtitle:
            sub = subtitle.get_text(" ", strip=True)
            if sub:
                text = f"{text} — {sub}"
        return text.strip()

    @classmethod
    def course_title_from_soup(cls, soup: BeautifulSoup, clean_config: CleanConfig) -> str:
        selector = clean_config.title_selector
        if selector:
            h1 = soup.select_one(selector)
            if h1:
                award = h1.select_one(".course-award")
                title = h1.select_one(".course-title")
                if award and title:
                    text = f"{award.get_text(' ', strip=True)} {title.get_text(' ', strip=True)}"
                else:
                    text = h1.get_text(" ", strip=True)
                subtitle = soup.select_one(".pageSubtitle")
                if subtitle:
                    sub = subtitle.get_text(" ", strip=True)
                    if sub:
                        text = f"{text} — {sub}"
                return text.strip()
        return cls.napier_course_title(soup) or MarkdownConverter.page_title_from_soup(soup)

    @classmethod
    def find_block(
        cls,
        soup: BeautifulSoup,
        heading: str | None,
        primary_selector: str,
    ) -> tuple[Tag | None, str]:
        del heading
        selectors = [part.strip() for part in primary_selector.split(",") if part.strip()]
        if not selectors:
            return None, primary_selector.strip()
        for selector in selectors:
            node = soup.select_one(selector)
            if node and len(node.get_text(strip=True)) >= 20:
                return node, selector
        return None, primary_selector.strip()

    @classmethod
    def entry_tabs_to_markdown(cls, entry_section: Tag) -> str:
        lines: list[str] = []
        panels = entry_section.select(".tab-content, .r-tabs-panel")
        for panel in panels:
            panel_id = panel.get("id", "")
            title = ""
            if panel_id:
                nav = entry_section.select_one(f'a.r-tabs-anchor[href="#{panel_id}"]')
                if nav:
                    title = nav.get_text(" ", strip=True)
            if not title:
                accordion = panel.find_previous(class_="r-tabs-accordion-title")
                if accordion:
                    title = accordion.get_text(" ", strip=True)
            body = MarkdownConverter.tag_to_markdown(panel)
            if not body:
                continue
            if title:
                lines.extend([f"### {title}", "", body, ""])
            else:
                lines.extend([body, ""])
        return "\n".join(lines).strip()

    @classmethod
    def block_body(
        cls,
        soup: BeautifulSoup,
        block_root: Tag,
        resolved_selector: str,
        env_heading: str | None,
        clean_config: CleanConfig,
    ) -> str:
        del soup, resolved_selector
        if clean_config.expand_tabs and block_has_tabs(block_root):
            return cls.entry_tabs_to_markdown(block_root)
        heading = env_heading or derive_heading_from_block(block_root)
        if heading:
            return section_body_without_duplicate_heading(block_root, heading)
        return MarkdownConverter.tag_to_markdown(block_root)

    @classmethod
    def append_block_extras(
        cls,
        block_root: Tag,
        selector: str,
        block: str,
    ) -> str:
        if selector.strip() == "#courseFees" or "courseFees" in selector:
            overseas = overseas_fee_from_napier_table(block_root)
            if overseas:
                return f"{block}\n\n**Overseas fee:** {overseas}"
        return block

    strip_within_block = staticmethod(strip_within_block)
    derive_heading_from_block = staticmethod(derive_heading_from_block)
