"""MMU Nuxt course pages — section IDs from course_detail/course-details.html."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from clean_config import CleanConfig
from engines.generic import GenericCourseHtmlEngine

MMU_ENTRY_SELECTOR = "#mmu-entry-requirements"
MMU_FEES_SELECTOR = "#fees"
FACT_FILE_SELECTOR = 'section[aria-labelledby="fact-file-title"]'
INTERNATIONAL_FEES_HEADING = "EU and non-EU international students"


class CourseHtmlEngine(GenericCourseHtmlEngine):
    @classmethod
    def find_block(
        cls,
        soup: BeautifulSoup,
        heading: str | None,
        primary_selector: str,
    ) -> tuple[Tag | None, str]:
        selector = primary_selector.strip()
        if selector == FACT_FILE_SELECTOR:
            node = soup.select_one(selector)
            if node and len(node.get_text(strip=True)) >= 20:
                return node, selector
            return None, selector
        if selector == MMU_ENTRY_SELECTOR:
            fees = soup.select_one("#fees")
            if not fees:
                return None, selector
            for div in fees.find_all_previous("div", class_=lambda c: c and "page-section" in c):
                text = div.get_text(" ", strip=True)
                if len(text) < 200 or "Fees and funding" in text:
                    continue
                if div.find("h2", string=lambda t: t and "Entry requirements" in (t or "")):
                    return div, selector
                if any(
                    marker in text
                    for marker in ("Typical offer", "IELTS", "Country-specific entry", "UCAS tariff")
                ):
                    return div, selector
            return None, selector
        if selector == MMU_FEES_SELECTOR:
            node = soup.select_one(MMU_FEES_SELECTOR)
            if node and node.get_text(strip=True):
                return node, MMU_FEES_SELECTOR
            return None, selector
        return super().find_block(soup, heading, primary_selector)

    @staticmethod
    def _fact_file_list_items(ul: Tag, label: str) -> list[str]:
        items = [li.get_text(" ", strip=True) for li in ul.find_all("li") if li.get_text(strip=True)]
        label_lower = label.strip().lower()
        if label_lower == "typical annual fees":
            return [t for t in items if t.lower().startswith("overseas") and not t.lower().startswith("home")]
        if label_lower == "course length":
            return [t for t in items if "part-time" not in t.lower() and "part time" not in t.lower()]
        return items

    @staticmethod
    def _fact_file_scalar_text(label: str, body: str) -> str:
        label_lower = label.strip().lower()
        text = body.strip()
        if label_lower == "course length":
            text = re.sub(r"\s*\d+\s*years?\s*part[- ]time.*", "", text, flags=re.I).strip()
        return text

    @staticmethod
    def fact_file_to_markdown(section: Tag) -> str:
        lines: list[str] = []
        for item in section.select(".divided-item"):
            h3 = item.find("h3")
            if not h3:
                continue
            label = h3.get_text(" ", strip=True)
            select = item.find("select")
            if select:
                option = select.find("option", selected=True) or select.find("option")
                value = option.get_text(strip=True) if option else ""
                if value:
                    lines.append(f"- **{label}:** {value}")
                continue
            ul = item.find("ul")
            if ul:
                parts = CourseHtmlEngine._fact_file_list_items(ul, label)
                if parts:
                    if len(parts) == 1:
                        lines.append(f"- **{label}:** {parts[0]}")
                    else:
                        lines.append(f"- **{label}:** " + "; ".join(parts))
                continue
            offer = item.select_one(".u-text-h6")
            if offer:
                label_lower = label.strip().lower()
                if label_lower == "course length":
                    parts = [
                        p.get_text(" ", strip=True)
                        for p in offer.find_all("p")
                        if p.get_text(strip=True)
                        and "part-time" not in p.get_text(" ", strip=True).lower()
                        and "part time" not in p.get_text(" ", strip=True).lower()
                    ]
                    if parts:
                        lines.append(f"- **{label}:** {'; '.join(parts)}")
                else:
                    lines.append(f"- **{label}:** {offer.get_text(' ', strip=True)}")
                continue
            body = item.get_text(" ", strip=True)
            if label and body.lower().startswith(label.lower()):
                body = body[len(label) :].strip()
            body = CourseHtmlEngine._fact_file_scalar_text(label, body)
            if body:
                lines.append(f"- **{label}:** {body}")
        return "\n".join(lines).strip()

    @staticmethod
    def _is_mmu_fee_boilerplate(text: str) -> bool:
        lower = text.lower()
        return (
            "subject to change" in lower
            or "tuition fees section" in lower
            or "part-time" in lower
            or "part time" in lower
        )

    @classmethod
    def fees_funding_to_markdown(cls, section: Tag) -> str:
        """International fee lines under EU and non-EU international students (h2 added by pipeline)."""
        lines: list[str] = []
        international_h3: Tag | None = None
        for h3 in section.find_all("h3"):
            title = h3.get_text(" ", strip=True)
            if title.casefold() == INTERNATIONAL_FEES_HEADING.casefold():
                international_h3 = h3
                break
        if international_h3 is None:
            return ""

        lines.append(f"### {INTERNATIONAL_FEES_HEADING}")
        lines.append("")
        sibling = international_h3.find_next_sibling()
        while sibling is not None and getattr(sibling, "name", None) not in ("h2", "h3"):
            if sibling.name == "p":
                text = sibling.get_text(" ", strip=True)
                if text and not cls._is_mmu_fee_boilerplate(text):
                    lines.append(text)
            sibling = sibling.find_next_sibling()
        if len(lines) <= 2:
            return ""
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
        if resolved_selector.strip() == FACT_FILE_SELECTOR or env_heading == "Fact file":
            return cls.fact_file_to_markdown(block_root)
        if resolved_selector.strip() == MMU_FEES_SELECTOR or env_heading == "Fees and funding":
            fees_md = cls.fees_funding_to_markdown(block_root)
            if fees_md:
                return fees_md
        return super().block_body(soup, block_root, resolved_selector, env_heading, clean_config)


course_html_engine = CourseHtmlEngine()
