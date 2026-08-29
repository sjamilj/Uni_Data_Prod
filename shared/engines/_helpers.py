"""Shared helpers for course HTML clean engines."""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from markdown_converter import MarkdownConverter


def strip_within_block(node: Tag, selectors: list[str]) -> None:
    for selector in selectors:
        for child in node.select(selector):
            child.decompose()


def derive_heading_from_block(node: Tag) -> str | None:
    for tag_name in ("h2", "h3"):
        heading = node.find(tag_name)
        if heading:
            text = heading.get_text(" ", strip=True)
            if text:
                return text
    return None


def block_has_tabs(node: Tag) -> bool:
    return bool(node.select(".tab-content, .r-tabs-panel, .utopian-tabs-container"))


def section_body_without_duplicate_heading(node: Tag, heading: str) -> str:
    clone = BeautifulSoup(str(node), "html.parser")
    root = clone.find(True) or clone
    heading_lower = heading.lower()
    for h2 in root.find_all("h2", limit=3):
        if h2.get_text(" ", strip=True).lower() == heading_lower:
            h2.decompose()
            break
    return MarkdownConverter.tag_to_markdown(root)


def overseas_fee_from_napier_table(fees_section: Tag) -> str:
    for row in fees_section.select("table tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        region = cells[0].get_text(" ", strip=True).lower()
        if "overseas" in region or "international" in region:
            fee = cells[1].get_text(" ", strip=True)
            if fee and "£" in fee:
                return fee
    return ""
