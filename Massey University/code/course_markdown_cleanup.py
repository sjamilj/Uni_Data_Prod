"""Massey University course HTML and markdown cleanup."""

from __future__ import annotations

import sys
import re
from pathlib import Path

from bs4 import BeautifulSoup

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import main


def preprocess_course_html_uni(soup: BeautifulSoup) -> None:
    """Convert Massey's definition-list key facts into readable labelled blocks."""
    # The generic list converter flattens nested intake closing-date lists,
    # joining each intake and its student deadlines into one bullet. Convert
    # them to headings and paragraphs so the pairing stays clear in markdown.
    for heading in soup.find_all("h3"):
        if " ".join(heading.stripped_strings).rstrip(" .:").casefold() != "application closing dates":
            continue
        dates = heading.find_next_sibling("ul")
        if not dates:
            continue
        replacement = soup.new_tag("div")
        replacement["class"] = ["massey-application-closing-dates"]
        for intake in dates.find_all("li", recursive=False):
            nested = intake.find("ul", recursive=False)
            intake_label = " ".join(
                str(item).strip()
                for item in intake.contents
                if isinstance(item, str) and str(item).strip()
            ).strip()
            if intake_label:
                subheading = soup.new_tag("h4")
                subheading.string = intake_label
                replacement.append(subheading)
            if nested:
                for deadline in nested.find_all("li", recursive=False):
                    paragraph = soup.new_tag("p")
                    paragraph.string = " ".join(deadline.stripped_strings)
                    replacement.append(paragraph)
        if replacement.contents:
            dates.replace_with(replacement)

    for definition_list in list(soup.select(".key-facts dl")):
        replacement = soup.new_tag("div")
        replacement["class"] = ["massey-key-facts"]
        for item in definition_list.select(":scope > .key-facts__item"):
            label_node = item.select_one("dt .key-facts__heading") or item.select_one("dt")
            value_node = item.select_one("dd")
            label = " ".join(label_node.stripped_strings) if label_node else ""
            if not label or not value_node:
                continue
            value = BeautifulSoup(str(value_node), "html.parser")
            for noisy in value.select(".tooltip__btn, .tooltip__popover, button, svg"):
                noisy.decompose()
            value_text = " ".join(value.stripped_strings)
            if label.casefold().rstrip(":") == "note":
                value_text = value_text.removeprefix("Note:").strip()
            if not value_text:
                continue
            block = soup.new_tag("div")
            heading = soup.new_tag("h3")
            heading.string = label
            paragraph = soup.new_tag("p")
            paragraph.string = value_text
            block.append(heading)
            block.append(paragraph)
            replacement.append(block)
        if replacement.contents:
            definition_list.replace_with(replacement)


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Remove the Future Food page sections requested for Massey cleanup."""
    if not any(
        heading.strip().casefold() == "# future food – master of impact and innovation"
        for heading in markdown.splitlines()
    ):
        return markdown

    # This specialization page repeats generic postgraduate marketing and
    # navigation copy. Drop the requested Course overview and Key facts blocks,
    # plus their generic promo subsections under Fees and scholarships.
    headings_to_remove = {
        (2, "course overview"),
        (2, "specialise in future food for your master of impact and innovation at massey"),
        (2, "key facts"),
        (3, "course fees"),
        (3, "student loans (studylink)"),
        (3, "scholarships and awards"),
    }
    lines = markdown.splitlines()
    cleaned: list[str] = []
    skip_level: int | None = None
    for line in lines:
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip().casefold()
            if skip_level is not None and level <= skip_level:
                skip_level = None
            if (level, title) in headings_to_remove:
                skip_level = level
                continue
        if skip_level is None:
            cleaned.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(cleaned)).strip() + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
