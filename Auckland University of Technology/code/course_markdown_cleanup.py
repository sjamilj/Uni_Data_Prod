"""University-specific course markdown cleanup (optional).

Configure simple heading removal in code/.env:

  COURSE_MARKDOWN_REMOVE_SECTIONS="
  4 :: With placement
  3 :: UK students
  "

Add conditional rules here via cleanup_course_markdown_uni() when .env is not enough.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from bs4 import Comment

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import main


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Remove AUT's New Zealand-only entry notes from cleaned course markdown."""
    targets = {
        "if you have new zealand qualifications",
        "useful new zealand school subjects",
    }
    kept: list[str] = []
    skip_level: int | None = None

    for line in markdown.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line.strip())
        if match:
            level = len(match.group(1))
            heading = match.group(2).strip().strip("*").strip().casefold()
            if skip_level is not None and level <= skip_level:
                skip_level = None
            if skip_level is None and heading in targets:
                skip_level = level
                continue
        if skip_level is None:
            kept.append(line)

    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()
    return f"{cleaned}\n" if cleaned else ""


def preprocess_course_html_uni(soup) -> None:
    """Keep AUT course content focused on the selected country and international fees."""
    for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()

    country_select = soup.select_one("#countrySelect")
    if country_select:
        wrapper = country_select.find_parent(class_="mb-20")
        if wrapper:
            wrapper.decompose()
        for paragraph in soup.select("p"):
            if "select your country from the dropdown" in paragraph.get_text(" ", strip=True).casefold():
                paragraph.string = "Country-specific entry requirements shown for Bangladesh."

    # AUT repeats the fee card in the right sidebar and lists domestic and
    # international prices together in the main card. Keep one international row.
    for duplicate in soup.select(".mainRight .quickFactsFees"):
        duplicate.decompose()

    for fee_block in soup.select(".quickFactsFees"):
        for fee_row in fee_block.select(".mb-small"):
            heading = fee_row.select_one(".heading")
            if heading and heading.get_text(" ", strip=True).casefold() == "domestic":
                fee_row.decompose()


def prepare_course_page_for_download(page) -> None:
    """Load AUT's country-specific entry requirements before saving a course page."""
    country = "Bangladesh"
    country_select = page.locator("#countrySelect")
    if country_select.count() == 0:
        return

    options = [value.strip().casefold() for value in country_select.locator("option").all_text_contents()]
    if country.casefold() not in options:
        raise RuntimeError("AUT entry requirements country selector has no Bangladesh option")

    entry_requirements = page.locator("#entryReq")
    if entry_requirements.count() == 0:
        raise RuntimeError("AUT course page has a country selector but no #entryReq results container")

    def mark_selected_option() -> None:
        country_select.evaluate(
            """(select, selectedCountry) => {
                for (const option of select.options) {
                    const isSelected = option.value === selectedCountry;
                    option.selected = isSelected;
                    if (isSelected) option.setAttribute('selected', '');
                    else option.removeAttribute('selected');
                }
            }""",
            country,
        )

    previous_text = entry_requirements.inner_text().strip()
    if country_select.input_value().strip().casefold() == country.casefold() and previous_text:
        mark_selected_option()
        return

    try:
        country_select.select_option(value=country, timeout=5000)
        page.wait_for_function(
            """({country, previousText}) => {
                const select = document.querySelector('#countrySelect');
                const result = document.querySelector('#entryReq');
                if (!select || !result || select.value !== country) return false;
                const currentText = (result.innerText || '').trim();
                return Boolean(currentText) && (!previousText || currentText !== previousText);
            }""",
            arg={"country": country, "previousText": previous_text},
            timeout=20000,
        )
        mark_selected_option()
    except Exception as exc:
        raise RuntimeError(
            f"Bangladesh was selected, but AUT did not update #entryReq with new requirements: {exc}"
        ) from exc


if __name__ == "__main__":
    raise SystemExit(main())
