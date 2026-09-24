"""University of Hull course markdown cleanup.

Heading removal is configured in COURSE_MARKDOWN_REMOVE_SECTIONS (ENV.MD / .env).
This module handles Hull-specific noise that is not a clean heading section.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, Tag

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import CourseMarkdownCleaner
from study_level import PRESETUP_CLEAN_SUBDIR, iter_course_markdown
from uni_paths import resolve_code_dir, resolve_output_dir

HULL_KEY_FACTS_ID = "hull-course-key-facts"
_HERO_TAG_LABELS = frozenset({"Code", "Duration", "Mode"})
_KEY_FACTS_LABELS = ("Code", "Duration", "Mode", "Course option", "Start date")
_ENTRY_QUAL_LABELS = (
    "UCAS tariff",
    "A levels",
    "BTEC",
    "T levels",
    "Access to HE",
    "International Baccalaureate",
    "IB",
    "Scottish Highers",
)
_KEY_FACTS_SECTION_RE = re.compile(
    r"(?m)^## Key facts\s*\n\n(.*?)(?=\n## )",
    re.S,
)

_H1_RE = re.compile(r"^#\s+(.+?)\s*$")
_MODULE_FILTER_RE = re.compile(
    r"^(?:No filters selected|Years of study Module types Number of credits)\s*$",
    re.I | re.M,
)
_MODULE_AVAILABILITY_RE = re.compile(
    r"All modules on this course page are subject to availability[^\n#]*",
    re.I,
)
_PANORAMA_UI_RE = re.compile(
    r"^(?:Loading\.\.\.|Click to|Load\s*$|Panorama\s*$|Look around\s*$)\s*\n?",
    re.M | re.I,
)
_COURSE_OPTION_START_RE = re.compile(r"^Course option Start date\b.*$", re.M | re.I)
_ENTRY_REQUIREMENTS_H2_RE = re.compile(r"^##\s+Entry Requirements\s*$", re.M | re.I)
_UK_FEES_PAYMENT_RE = re.compile(
    r"^###\s+How do I pay for it\?\s*\n.*?(?=^###\s+|\Z)",
    re.M | re.S | re.I,
)
_UK_STANDARD_FEE_WIDGET_RE = re.compile(
    r"^Standard Tuition Fee\s*\n+£[\d,]+ / year\s*\n+.*?(?=\n*$|\Z)",
    re.M | re.S | re.I,
)
def _hull_fees_how_much_section(markdown: str) -> str:
    fees_match = re.search(
        r"## Fees[^\n]*\n(.*?)(?=\n## |\Z)",
        markdown,
        re.S | re.I,
    )
    if not fees_match:
        return ""
    body = fees_match.group(1)
    how_match = re.search(
        r"### How much is it\?\s*(.*?)(?=\n### |\n## |\Z)",
        body,
        re.S | re.I,
    )
    return how_match.group(1) if how_match else body


def _hull_fees_section_has_amount(markdown: str) -> bool:
    return bool(re.search(r"£\s*[\d,]+", _hull_fees_how_much_section(markdown)))


def _combobox_value(main: Tag, label_prefix: str) -> str:
    for lab in main.find_all("label"):
        text = lab.get_text(" ", strip=True)
        if not text.startswith(label_prefix):
            continue
        col = lab.find_parent("div", class_=lambda c: c and "flex-col" in str(c))
        if not col:
            continue
        span = col.select_one('button[role="combobox"] span')
        if span:
            return span.get_text(strip=True)
    return ""


def _hero_tag_facts(main: Tag) -> dict[str, str]:
    facts: dict[str, str] = {}
    for tag in main.select("p.tag"):
        label = tag.get_text(strip=True)
        if label not in _HERO_TAG_LABELS:
            continue
        value = tag.find_next_sibling("p")
        if value is None:
            continue
        facts[label] = value.get_text(" ", strip=True)
    course_option = _combobox_value(main, "Course option")
    start_date = _combobox_value(main, "Start date")
    if course_option:
        facts["Course option"] = course_option
    if start_date:
        facts["Start date"] = start_date
    return facts


def _inject_key_facts(soup: BeautifulSoup) -> None:
    main = soup.select_one("main")
    if main is None:
        return
    existing = main.select_one(f"#{HULL_KEY_FACTS_ID}")
    if existing:
        existing.decompose()
    facts = _hero_tag_facts(main)
    if not facts:
        return
    wrapper = soup.new_tag("div", id=HULL_KEY_FACTS_ID)
    ul = soup.new_tag("ul")
    for label in _KEY_FACTS_LABELS:
        value = facts.get(label)
        if not value:
            continue
        display = "UCAS code" if label == "Code" else label
        li = soup.new_tag("li")
        strong = soup.new_tag("strong")
        strong.string = f"{display}:"
        li.append(strong)
        li.append(f" {value}")
        ul.append(li)
    wrapper.append(ul)
    main.insert(0, wrapper)


def _strip_uk_tab_panels(soup: BeautifulSoup) -> None:
    for section in soup.select("section[aria-label]"):
        if not isinstance(section, Tag):
            continue
        aria = (section.attrs or {}).get("aria-label", "") or ""
        if "Entry" not in aria and "Fees" not in aria:
            continue
        panels = section.select('[role="tabpanel"]')
        international = [
            p
            for p in panels
            if "international" in (p.get("id") or "").lower()
        ]
        has_international = any(len(p.get_text(strip=True)) >= 40 for p in international)
        if not has_international:
            continue
        for panel in panels:
            panel_id = (panel.get("id") or "").lower()
            if "international" in panel_id:
                continue
            panel.decompose()
        for tablist in section.select('[role="tablist"]'):
            tablist.decompose()


def settle_course_page_after_download(page, url: str) -> None:
    """Activate International entry/fees tabs so panel HTML is present in the snapshot."""
    if "/courses/" not in url:
        return
    try:
        page.wait_for_selector(
            'section[aria-label="Entry Requirements"]',
            timeout=20000,
        )
    except Exception:
        return
    for section_label in ("Entry Requirements", "Fees & Funding"):
        section = page.locator(f'section[aria-label="{section_label}"]')
        if section.count() == 0:
            continue
        tab = section.get_by_role("tab", name=re.compile(r"international", re.I))
        if tab.count() == 0:
            continue
        try:
            tab.first.click(timeout=5000)
            page.wait_for_timeout(600)
        except Exception:
            continue
    page.wait_for_timeout(400)


def preprocess_course_html_uni(soup: BeautifulSoup) -> None:
    """Keep international entry/fees tabs and inject course option / start date key facts."""
    _strip_uk_tab_panels(soup)
    _inject_key_facts(soup)


def _resolve_hull_course_html(code_dir: Path, source_html: str) -> Path | None:
    if not source_html.strip():
        return None
    uni = code_dir.parent
    rel = Path(source_html)
    name = rel.name
    for candidate in (
        uni / "output" / rel,
        uni / rel,
        uni / "course_detail" / name,
        uni / "output" / "course_pages" / name,
    ):
        if candidate.is_file():
            return candidate
    return None


def _html_supports_hull_blocks(html: str) -> bool:
    return 'aria-label="Entry Requirements"' in html


def _rebuild_body_from_html(html_path: Path, code_dir: Path) -> str | None:
    from clean_config import CleanConfigLoader
    from download_and_clean_course_pages import CourseMarkdownBuilder

    html = html_path.read_text(encoding="utf-8", errors="replace")
    if not _html_supports_hull_blocks(html):
        return None
    cfg = CleanConfigLoader.load(code_dir)
    rebuilt = CourseMarkdownBuilder.from_config(html, cfg, code_dir)
    if "## Entry Requirements" not in rebuilt:
        return None
    return rebuilt


def _strip_marketing_before_entry(markdown: str) -> str:
    """Drop NSS tiles, accreditations blurb, and promo H2s before Entry Requirements."""
    start = _COURSE_OPTION_START_RE.search(markdown)
    if not start:
        return markdown
    entry = _ENTRY_REQUIREMENTS_H2_RE.search(markdown, start.start())
    if not entry:
        return markdown
    before = markdown[: start.start()].rstrip()
    after = markdown[entry.start() :].lstrip("\n")
    return f"{before}\n\n{after}"


def _display_fact_label(label: str) -> str:
    return "UCAS code" if label.strip().lower() == "code" else label.strip()


def _label_value_pairs_to_bullets(
    body: str,
    labels: tuple[str, ...],
) -> str:
    bullets: list[str] = []
    for label in labels:
        match = re.search(
            rf"^{re.escape(label)}\s*\n\n([^\n#]+?)\s*(?:\n\n|\Z)",
            body,
            flags=re.M | re.I,
        )
        if not match:
            continue
        value = match.group(1).strip()
        if value:
            bullets.append(f"- **{_display_fact_label(label)}:** {value}")
    return "\n".join(bullets)


def _format_key_facts_bullets(markdown: str) -> str:
    def replace_section(match: re.Match[str]) -> str:
        body = match.group(1)
        if body.lstrip().startswith("- **"):
            return match.group(0)
        bullets = _label_value_pairs_to_bullets(body, _KEY_FACTS_LABELS)
        if not bullets:
            return match.group(0)
        return "## Key facts\n\n" + bullets + "\n"

    return _KEY_FACTS_SECTION_RE.sub(replace_section, markdown)


def _format_entry_qualification_bullets(markdown: str) -> str:
    marker = "## Entry Requirements"
    if marker not in markdown:
        return markdown
    head, tail = markdown.split(marker, 1)
    next_h2 = re.search(r"\n## ", tail)
    if next_h2:
        entry_body, after = tail[: next_h2.start()], tail[next_h2.start() :]
    else:
        entry_body, after = tail, ""

    qual_bullets = _label_value_pairs_to_bullets(entry_body, _ENTRY_QUAL_LABELS)
    if not qual_bullets:
        return markdown

    for label in _ENTRY_QUAL_LABELS:
        entry_body = re.sub(
            rf"^{re.escape(label)}\s*\n\n[^\n#]+?\s*\n+",
            "",
            entry_body,
            flags=re.M | re.I,
        )

    insert_at = re.search(r"\nUse UCAS", entry_body, flags=re.I)
    if insert_at:
        pos = insert_at.start()
        entry_body = (
            entry_body[:pos].rstrip()
            + "\n\n"
            + qual_bullets
            + "\n\n"
            + entry_body[pos:].lstrip("\n")
        )
    else:
        entry_body = entry_body.rstrip() + "\n\n" + qual_bullets + "\n"

    return head + marker + entry_body + after


def _remove_duplicate_h1(markdown: str) -> str:
    """Hull course markdown often repeats the course title H1 after a stray Course content block."""
    lines = markdown.splitlines()
    first_title: str | None = None
    kept: list[str] = []
    for line in lines:
        match = _H1_RE.match(line)
        if match:
            title = match.group(1).strip()
            if first_title is None:
                first_title = title
                kept.append(line)
                continue
            if title == first_title:
                continue
        kept.append(line)
    return "\n".join(kept)


def _normalize_hull_html_for_fee_scan(html: str) -> str:
    text = html.replace("\\u0026pound;", "£").replace("&pound;", "£")
    text = text.replace("\\u003c", "<").replace("\\u003e", ">")
    return text


def _extract_hull_fees_from_html(html: str) -> dict[str, str]:
    text = _normalize_hull_html_for_fee_scan(html)
    fees: dict[str, str] = {}
    patterns = {
        "standard": r"For International students.*?standard course fee.*?£\s*([\d,]+)",
        "accelerated": r"accelerated learning course is.*?£\s*([\d,]+)",
        "foundation": r"foundation year as part of your course.*?the fee is.*?£\s*([\d,]+)",
        "masters": r"Masters Fee.*?£\s*([\d,]+)",
        "pg_overall": r"The overall fee for this course is £\s*([\d,]+)",
        "pgt_intl": r"£\s*([\d,]+)\s*\(PGT[^)]*International",
        "pgr_full_time": r"(?:Our\s+)?standard course fee is £\s*([\d,]+)\s*a year for full-time",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.I)
        if match:
            fees[key] = match.group(1).replace(",", "").strip()
    return fees


def _format_gbp_amount(amount: str) -> str:
    digits = amount.replace(",", "").strip()
    if not digits.isdigit():
        return amount
    return f"£{int(digits):,}"


def _study_level_from_markdown(markdown: str) -> str:
    pipeline = re.search(r"study_level=(\w+)", markdown, re.I)
    if pipeline:
        return pipeline.group(1).strip().lower()
    front = re.search(r"^study_level:\s*(\S+)\s*$", markdown, re.I | re.M)
    if front:
        return front.group(1).strip().lower()
    return ""


def _pick_hull_fee_amount(
    fees: dict[str, str],
    *,
    study_level: str,
    want_foundation: bool,
) -> str:
    if want_foundation:
        return (
            fees.get("foundation")
            or fees.get("standard")
            or fees.get("accelerated")
            or fees.get("masters")
            or fees.get("pg_overall")
            or fees.get("pgt_intl")
            or fees.get("pgr_full_time")
            or ""
        )
    if study_level in ("postgraduate", "postgraduate_research"):
        return (
            fees.get("masters")
            or fees.get("pg_overall")
            or fees.get("pgt_intl")
            or fees.get("pgr_full_time")
            or fees.get("standard")
            or fees.get("accelerated")
            or ""
        )
    return (
        fees.get("accelerated")
        or fees.get("standard")
        or fees.get("masters")
        or fees.get("pg_overall")
        or ""
    )


def _inject_hull_fees_into_markdown(
    markdown: str,
    fees: dict[str, str],
    *,
    study_level: str = "",
) -> str:
    if not fees or _hull_fees_section_has_amount(markdown):
        return markdown

    level = (study_level or _study_level_from_markdown(markdown)).strip().lower()
    option_match = re.search(r"-\s*\*\*Course option:\*\*\s*([^\n]+)", markdown, re.I)
    course_option = (option_match.group(1) if option_match else "").casefold()
    want_foundation = level == "foundation" or "foundation year" in course_option

    amount = _pick_hull_fee_amount(fees, study_level=level, want_foundation=want_foundation)
    if not amount:
        return markdown

    lines: list[str] = []
    if fees.get("accelerated") and amount == fees.get("accelerated"):
        lines.append(
            "The fee for our accelerated learning course is "
            f"{_format_gbp_amount(amount)} per year."
        )
    elif level == "postgraduate_research" and fees.get("pgr_full_time"):
        lines.append(
            f"Our standard course fee is {_format_gbp_amount(amount)} a year for full-time study."
        )
    else:
        lines.append(
            "For International students, the standard course fee is "
            f"{_format_gbp_amount(amount)} per year."
        )
    if fees.get("foundation") and fees["foundation"] != amount:
        lines.append(
            "If you choose to study a foundation year as part of your course, "
            f"the fee is {_format_gbp_amount(fees['foundation'])}."
        )
    block = "\n".join(lines) + "\n"

    marker = "### How much is it?"
    if marker in markdown:
        if markdown.rstrip().endswith(marker):
            return markdown.rstrip() + "\n\n" + block
        patched, count = re.subn(
            r"(### How much is it\?\s*)",
            r"\1\n\n" + block,
            markdown,
            count=1,
            flags=re.I,
        )
        if count:
            return patched
    if "## Fees" in markdown:
        return re.sub(
            r"(## Fees[^\n]*\n)",
            r"\1\n" + block,
            markdown,
            count=1,
            flags=re.I,
        )
    return markdown + "\n\n## Fees & Funding\n\n### How much is it?\n\n" + block


def supplement_course_markdown_from_source_html(
    markdown: str,
    *,
    code_dir: Path,
    source_html: str = "",
    study_level: str = "",
) -> str:
    html_path = _resolve_hull_course_html(code_dir, source_html)
    if not html_path:
        return markdown
    fees = _extract_hull_fees_from_html(
        html_path.read_text(encoding="utf-8", errors="replace")
    )
    return _inject_hull_fees_into_markdown(
        markdown,
        fees,
        study_level=study_level,
    )


def _apply_foundation_scope_duration(markdown: str, study_level: str) -> str:
    """Foundation listing scope includes a foundation year — show total length (typically +1 year)."""
    if study_level.strip().lower() != "foundation":
        return markdown

    def bump_years(match: re.Match[str]) -> str:
        years = int(match.group(1))
        if years >= 4:
            return match.group(0)
        return f"- **Duration:** {years + 1} years"

    return re.sub(
        r"- \*\*Duration:\*\* (\d+)\s*years?",
        bump_years,
        markdown,
        count=1,
        flags=re.I,
    )


def cleanup_course_markdown_uni(markdown: str) -> str:
    markdown = _remove_duplicate_h1(markdown)
    markdown = _strip_marketing_before_entry(markdown)
    markdown = _format_key_facts_bullets(markdown)
    markdown = _format_entry_qualification_bullets(markdown)
    markdown = _MODULE_FILTER_RE.sub("", markdown)
    markdown = _MODULE_AVAILABILITY_RE.sub("", markdown)
    markdown = _PANORAMA_UI_RE.sub("", markdown)
    markdown = re.sub(r"##\s*Future prospects\s*", "", markdown, flags=re.I)
    markdown = _UK_FEES_PAYMENT_RE.sub("", markdown)
    markdown = _UK_STANDARD_FEE_WIDGET_RE.sub("", markdown)
    markdown = re.sub(r"£(\d[\d,]*)(?=[a-zA-Z])", r"£\1 ", markdown)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown.strip())
    if re.search(r"study_level=foundation\b", markdown):
        markdown = _apply_foundation_scope_duration(markdown, "foundation")
    elif re.search(r"- \*\*Course option:\*\* Foundation year", markdown, re.I):
        markdown = _apply_foundation_scope_duration(markdown, "foundation")
    return markdown + "\n"


def _course_markdown_dirs(code_dir: Path) -> list[Path]:
    clean_root = resolve_output_dir(code_dir) / "clean"
    dirs: list[Path] = []
    for name in (PRESETUP_CLEAN_SUBDIR, "courses"):
        path = clean_root / name
        if path.is_dir():
            dirs.append(path)
    return dirs


def main(argv: list[str] | None = None) -> int:
    code_dir = resolve_code_dir(Path(__file__).resolve().parent)
    cleaner = CourseMarkdownCleaner()
    targets = _course_markdown_dirs(code_dir)
    if not targets:
        raise SystemExit("No course markdown directories found under output/clean/.")

    updated_total = 0
    file_total = 0
    for courses_dir in targets:
        print(f"Cleaning course markdown in {courses_dir}...")
        for path in iter_course_markdown(courses_dir):
            file_total += 1
            raw = path.read_text(encoding="utf-8")
            meta, body = cleaner.parse_frontmatter(raw)
            html_path = _resolve_hull_course_html(code_dir, meta.get("source_html", ""))
            if html_path is not None:
                rebuilt = _rebuild_body_from_html(html_path, code_dir)
                if rebuilt:
                    body = rebuilt
                body = supplement_course_markdown_from_source_html(
                    body,
                    code_dir=code_dir,
                    source_html=meta.get("source_html", ""),
                    study_level=str(meta.get("study_level", "")),
                )
            cleaned_body = cleaner.cleanup_course_markdown(
                body.rstrip("\n"),
                code_dir=code_dir,
                source_html=str(meta.get("source_html", "")),
            )
            cleaned_body = _apply_foundation_scope_duration(
                cleaned_body.rstrip("\n"),
                meta.get("study_level", ""),
            )
            if not cleaned_body.endswith("\n"):
                cleaned_body += "\n"
            output = cleaner.format_frontmatter(meta) + cleaned_body
            if output != raw:
                path.write_text(output, encoding="utf-8")
                updated_total += 1
                print(f"  updated {path.name}")
            else:
                print(f"  unchanged {path.name}")
    print(f"Done: {updated_total}/{file_total} file(s) updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
