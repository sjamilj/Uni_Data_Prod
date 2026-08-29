"""ARU Utopian CMS course HTML → markdown engine."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from clean_config import CleanConfig
from engines._helpers import (
    block_has_tabs,
    derive_heading_from_block,
    section_body_without_duplicate_heading,
    strip_within_block,
)
from engines.generic import GenericCourseHtmlEngine
from markdown_converter import MarkdownConverter


class UtopianCourseHtmlEngine(GenericCourseHtmlEngine):
    """ARU course pages: Utopian tabs, accordions, and research-course layouts."""

    BLOCK_SELECTORS: dict[str, list[str]] = {
        "course overview": [
            "#utopian-course-overview",
            "section.course-summary",
            "#overview",
        ],
        "entry requirements": ["#entry_requirements", "#entryrequirements"],
        "fees and funding": ["#fees_and_funding", "#feesfunding"],
        "fees & funding": ["#fees_and_funding", "#feesfunding"],
    }

    @classmethod
    def course_title_from_soup(cls, soup: BeautifulSoup, clean_config: CleanConfig) -> str:
        selector = clean_config.title_selector
        if selector:
            title = super().course_title_from_soup(soup, clean_config)
            if title:
                return title
        research_h1 = soup.select_one(".course-summary__heading")
        if research_h1:
            return re.sub(r"\s+", " ", research_h1.get_text(" ", strip=True)).strip()
        return super().course_title_from_soup(soup, clean_config)

    @classmethod
    def find_block(
        cls,
        soup: BeautifulSoup,
        heading: str | None,
        primary_selector: str,
    ) -> tuple[Tag | None, str]:
        selectors = [primary_selector.strip()]
        if heading:
            alt = cls.BLOCK_SELECTORS.get(heading.lower().strip())
            if alt:
                selectors = alt
        for sel in selectors:
            node = soup.select_one(sel)
            if node and len(node.get_text(strip=True)) >= 20:
                return node, sel
        return None, primary_selector

    @staticmethod
    def _utopian_tab_title(container: Tag, panel: Tag) -> str:
        labelled_by = panel.get("aria-labelledby", "")
        if labelled_by:
            tab_btn = container.select_one(f"#{labelled_by}")
            if tab_btn:
                return tab_btn.get_text(" ", strip=True)
        heading = panel.find_previous_sibling(
            "h3", class_="utopian-tabs-container__accordion-heading"
        )
        if heading:
            btn = heading.select_one("button")
            if btn:
                return btn.get_text(" ", strip=True)
            return heading.get_text(" ", strip=True)
        return ""

    @classmethod
    def _utopian_options_list_to_markdown(cls, options: Tag) -> str:
        lines: list[str] = []
        for dt in options.select("dt"):
            dd = dt.find_next_sibling("dd")
            if not dd:
                continue
            key = dt.get_text(" ", strip=True)
            val = dd.get_text(" ", strip=True)
            if key and val:
                lines.append(f"- **{key}:** {val}")
        return "\n".join(lines)

    @classmethod
    def _utopian_panel_to_markdown(cls, panel: Tag) -> str:
        options = panel.select_one(".utopian-course-options__list")
        if options:
            body = cls._utopian_options_list_to_markdown(options)
            if body:
                return body

        fees = panel.select_one(".utopian-course-fees")
        if fees:
            lines: list[str] = []
            for section in fees.select(".utopian-course-fees__fee-title__section"):
                price = section.select_one(".utopian-course-fees__fee-title-price")
                desc = section.select_one(".utopian-course-fees__fee-title-description")
                if price and desc:
                    lines.append(
                        f"**{price.get_text(strip=True)}** "
                        f"{desc.get_text(' ', strip=True)}"
                    )
            desc = fees.select_one(".utopian-course-fees__fees-description")
            if desc:
                body = MarkdownConverter.tag_to_markdown(desc)
                if body:
                    lines.append(body)
            return "\n\n".join(lines)

        return MarkdownConverter.tag_to_markdown(panel)

    @classmethod
    def utopian_tabs_to_markdown(
        cls, container: Tag, *, options_only: bool = False
    ) -> str:
        lines: list[str] = []
        panels = [
            panel
            for panel in container.select("div.utopian-tabs-container__tab-panel")
            if panel.find_parent("div", class_="utopian-tabs-container") == container
        ]
        for panel in panels:
            if options_only and not panel.select_one(".utopian-course-options__list"):
                continue
            title = cls._utopian_tab_title(container, panel)
            body = cls._utopian_panel_to_markdown(panel)
            if not body:
                continue
            if title:
                lines.extend([f"#### {title}", "", body, ""])
            else:
                lines.extend([body, ""])
        return "\n".join(lines).strip()

    @classmethod
    def utopian_block_to_markdown(cls, node: Tag) -> str:
        clone = BeautifulSoup(str(node), "html.parser")
        root = clone.find(True) or clone
        parts: list[str] = []

        for heading in root.select(".utopian-course-section__heading"):
            heading.decompose()

        for acc_group in root.select(".utopian-accordion-group"):
            for section in acc_group.select(".utopian-accordion-section"):
                title_el = section.select_one(".utopian-accordion--button-title")
                title = title_el.get_text(" ", strip=True) if title_el else ""
                content_el = section.select_one(".utopian-accordion--content")
                if not content_el:
                    continue

                inner_parts: list[str] = []
                for tab_container in content_el.select(".utopian-tabs-container"):
                    tab_md = cls.utopian_tabs_to_markdown(tab_container)
                    if tab_md:
                        inner_parts.append(tab_md)

                content_clone = BeautifulSoup(str(content_el), "html.parser")
                for remove in content_clone.select(
                    ".utopian-tabs-container, .utopian-tabs-container__tabs"
                ):
                    remove.decompose()
                remainder = MarkdownConverter.tag_to_markdown(content_clone).strip()
                if remainder:
                    inner_parts.append(remainder)

                inner = "\n\n".join(part for part in inner_parts if part)
                if not inner:
                    continue
                if title:
                    parts.append(f"### {title}\n\n{inner}")
                else:
                    parts.append(inner)
            acc_group.decompose()

        for tab_container in root.select(".utopian-tabs-container"):
            tab_md = cls.utopian_tabs_to_markdown(tab_container)
            if tab_md:
                parts.append(tab_md)
            tab_container.decompose()

        remainder = MarkdownConverter.tag_to_markdown(root).strip()
        if remainder:
            parts.append(remainder)

        return "\n\n".join(parts).strip()

    @classmethod
    def overview_to_markdown(cls, block_root: Tag, soup: BeautifulSoup) -> str:
        for h1 in block_root.select("#course-page-title"):
            h1.decompose()
        for script in block_root.select("script"):
            script.decompose()

        parts: list[str] = []
        award = block_root.select_one(".hero-award-title")
        placement = block_root.select_one(".hero-award-placement-year")
        if award:
            line = award.get_text(" ", strip=True)
            if placement:
                line = f"{line}\n\n{placement.get_text(' ', strip=True)}"
            parts.append(line)
        elif placement:
            parts.append(placement.get_text(" ", strip=True))

        options_md = ""
        tabs = soup.select_one(".course-content .utopian-tabs-container")
        if tabs:
            options_md = cls.utopian_tabs_to_markdown(tabs, options_only=True)
        if not options_md:
            options_list = soup.select_one(
                ".course-content .utopian-course-options__list"
            )
            if options_list:
                options_md = cls._utopian_options_list_to_markdown(options_list)
        if options_md:
            parts.append(options_md)

        return "\n\n".join(part for part in parts if part).strip()

    @staticmethod
    def _collapse_ws(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def research_summary_to_markdown(cls, summary: Tag) -> str:
        parts: list[str] = []
        heading = summary.select_one(".course-summary__heading")
        if heading:
            parts.append(cls._collapse_ws(heading.get_text(" ", strip=True)))
        for label, sel in (
            ("Type", ".course-summary__type"),
            ("Location", ".course-summary__locations"),
            ("Start", ".course-summary__entry"),
        ):
            el = summary.select_one(sel)
            if el:
                text = cls._collapse_ws(el.get_text(" ", strip=True))
                if text:
                    parts.append(f"- **{label}:** {text}")
        return "\n\n".join(parts)

    @classmethod
    def research_accordion_to_markdown(cls, section: Tag) -> str:
        content = section.select_one(".accordion__content, .accordion__section__inner")
        root = content or section
        clone = BeautifulSoup(str(root), "html.parser")
        for heading in clone.select(".nested-accordion-heading"):
            heading.decompose()
        for nested in clone.select(".nested-accordion__content"):
            nested["style"] = ""
        for feature in clone.select(
            "section.grid-container, .feature-block--purple, "
            ".feature-block--video-double-width, .feature-block--image"
        ):
            feature.decompose()
        return MarkdownConverter.tag_to_markdown(clone.find(True) or clone).strip()

    @classmethod
    def research_overview_to_markdown(cls, soup: BeautifulSoup) -> str:
        summary = soup.select_one("section.course-summary")
        if summary:
            return cls.research_summary_to_markdown(summary)
        return ""

    @classmethod
    def entry_tabs_to_markdown(cls, entry_section: Tag) -> str:
        if entry_section.select(".utopian-tabs-container"):
            return cls.utopian_block_to_markdown(entry_section)
        return super().entry_tabs_to_markdown(entry_section)

    @classmethod
    def block_body(
        cls,
        soup: BeautifulSoup,
        block_root: Tag,
        resolved_selector: str,
        env_heading: str | None,
        clean_config: CleanConfig,
    ) -> str:
        heading_key = (env_heading or "").lower().strip()
        if heading_key == "course overview" and not soup.select_one("#utopian-course-overview"):
            return cls.research_overview_to_markdown(soup)
        if resolved_selector == "#utopian-course-overview":
            return cls.overview_to_markdown(block_root, soup)
        if resolved_selector in ("#overview", "#entryrequirements", "#feesfunding"):
            return cls.research_accordion_to_markdown(block_root)
        if resolved_selector == "section.course-summary":
            return cls.research_summary_to_markdown(block_root)
        if clean_config.expand_tabs and block_has_tabs(block_root):
            return cls.entry_tabs_to_markdown(block_root)
        heading = env_heading or derive_heading_from_block(block_root)
        if heading:
            return section_body_without_duplicate_heading(block_root, heading)
        return MarkdownConverter.tag_to_markdown(block_root)

    strip_within_block = staticmethod(strip_within_block)
    derive_heading_from_block = staticmethod(derive_heading_from_block)
