"""University of Birmingham course markdown cleanup.

Postgraduate course pages use a hero country dropdown (`#countryDropdownHero`).
Download selects Bangladesh (see ``settle_course_page_after_download``) so
international fees and country entry copy are in the saved HTML.

Heading removal: ``COURSE_MARKDOWN_REMOVE_SECTIONS`` in code/.env.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import (
    EnvFileLoader,
    remove_markdown_heading_section,
)
from course_markdown_cleanup import main  # noqa: F401 — CLI entry

BIRMINGHAM_KEY_FACTS_ID = "birmingham-course-key-facts"
BIRMINGHAM_HERO_FEES_ID = "birmingham-hero-international-fees"
BIRMINGHAM_SCHOLARSHIPS_ID = "birmingham-course-scholarships"
_HERO_FACT_LABELS = ("Start date", "Duration", "Award")
_CODE_DIR = Path(__file__).resolve().parent
_UK_FEE_TILE_RE = re.compile(r"fees\s*\(\s*uk", re.I)
_INTL_FEE_TILE_RE = re.compile(r"fees\s*\(\s*international", re.I)
_GBP_AMOUNT_RE = re.compile(r"£\s*([\d,]+)")
_PARSER_AWARD_RE = re.compile(r"(?m)^- Award\s+\S+")
_DEGREE_TOKEN_RE = re.compile(
    r"\b(PGCE|PGDip|PGCert|MPhil|MRes|MBA|MSc|LLM|LLB|PhD|MEng|BEng|BSc|BA|MA)\b",
    re.I,
)
_DEGREE_CANONICAL = {
    "pgce": "PGCE",
    "pgdip": "PGDip",
    "pgcert": "PGCert",
    "mphil": "MPhil",
    "mres": "MRes",
    "mba": "MBA",
    "msc": "MSc",
    "llm": "LLM",
    "llb": "LLB",
    "phd": "PhD",
    "meng": "MEng",
    "beng": "BEng",
    "bsc": "BSc",
    "ba": "BA",
    "ma": "MA",
}
# Longest phrases first so "master of arts by research" wins over "master of arts".
_AWARD_PHRASE_TO_DEGREE = (
    ("master of business administration", "MBA"),
    ("postgraduate certificate in education", "PGCE"),
    ("master of arts by research", "MA"),
    ("master of science", "MSc"),
    ("master of research", "MRes"),
    ("postgraduate diploma", "PGDip"),
    ("postgraduate certificate", "PGCert"),
    ("doctor of philosophy", "PhD"),
    ("master of laws", "LLM"),
    ("master of law", "LLM"),
    ("master of arts", "MA"),
    ("master of engineering", "MEng"),
    ("bachelor of science", "BSc"),
    ("bachelor of arts", "BA"),
    ("bachelor of engineering", "BEng"),
    ("doctorate", "PhD"),
)
_MONTH_ONLY_RE = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|November|December)$",
    re.I,
)
_ORPHAN_ADDITIONAL_REQ_RE = re.compile(
    r"(?m)^### International entry requirements\s*\n+Additional requirements for\s*\n+",
    re.I,
)
_KEY_FACTS_BULLET_RE = re.compile(
    r"(?m)^- \*\*(Start date|Duration|Award):\*\* .+\n",
)
_IELTS_NORMALIZE_RE = re.compile(
    r"For this course we require\s+IELTS\s+([\d.]+)\s+with no less than\s+([\d.]+)\s+in (?:any|each) band",
    re.I,
)
_FEES_SECTION_RE = re.compile(r"(?m)^## Fees and funding\s*\n", re.I)


def _env_for_code_dir(code_dir: Path | None) -> dict[str, str]:
    return EnvFileLoader.load_from_code_dir(code_dir or _CODE_DIR)


def _course_page_country(code_dir: Path) -> str:
    env = _env_for_code_dir(code_dir)
    return (env.get("COURSE_PAGE_COUNTRY") or "Bangladesh").strip() or "Bangladesh"


def _default_intake_year(code_dir: Path | None = None) -> str:
    env = _env_for_code_dir(code_dir)
    return (env.get("COURSE_DEFAULT_INTAKE_YEAR") or "2026").strip() or "2026"


def _expand_start_date(value: str, code_dir: Path | None = None) -> str:
    text = (value or "").strip()
    if not text or re.search(r"\b(19|20)\d{2}\b", text):
        return text
    if _MONTH_ONLY_RE.match(text):
        return f"{text.title()} {_default_intake_year(code_dir)}"
    return text


def _hero_course_tiles(soup: BeautifulSoup) -> dict[str, str]:
    tiles: dict[str, str] = {}
    for tile in soup.select("article.course-tile"):
        title_el = tile.select_one(".course-tile__title")
        value_el = tile.select_one(".course-tile__value")
        if not title_el or not value_el:
            continue
        label = title_el.get_text(" ", strip=True)
        value = value_el.get_text(" ", strip=True)
        if label and value:
            tiles[label] = value
    return tiles


def _full_time_duration(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return "1 year full-time"
    if re.search(r"full[\s-]*time", text, re.I):
        for part in re.split(r"[,;.]", text):
            part = part.strip()
            if (
                part
                and re.search(r"full[\s-]*time", part, re.I)
                and not re.search(r"part[\s-]*time", part, re.I)
            ):
                return part
    return text


def _degree_from_award_phrase(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return ""
    primary = re.split(r"\s*/\s*", cleaned, maxsplit=1)[0].strip()
    lower = primary.casefold()
    for phrase, degree in _AWARD_PHRASE_TO_DEGREE:
        if lower == phrase or lower.startswith(f"{phrase} "):
            return degree
    match = _DEGREE_TOKEN_RE.search(primary)
    if match:
        return _DEGREE_CANONICAL.get(match.group(1).casefold(), match.group(1))
    return ""


def _degree_name_from_hero(soup: BeautifulSoup, tiles: dict[str, str]) -> str:
    span = soup.select_one(".hero-courses__title-award")
    if span:
        degree = _degree_from_award_phrase(span.get_text(" ", strip=True))
        if degree:
            return degree
    return _degree_from_award_phrase(tiles.get("Award", ""))


def _hero_tile_facts(soup: BeautifulSoup, code_dir: Path | None = None) -> dict[str, str]:
    facts: dict[str, str] = {}
    tiles = _hero_course_tiles(soup)
    start = tiles.get("Start date", "")
    if start:
        facts["Start date"] = _expand_start_date(start, code_dir)
    duration = tiles.get("Duration", "")
    if duration:
        facts["Duration"] = _full_time_duration(duration)
    award = tiles.get("Award", "")
    if award:
        facts["Award"] = re.split(r"\s*/\s*", award, maxsplit=1)[0].strip()
    degree = _degree_name_from_hero(soup, tiles)
    if degree:
        facts["Degree name"] = degree
    return facts


def _hero_international_fee_line(soup: BeautifulSoup) -> tuple[str, str] | None:
    """Return (fee display e.g. £32,580, duration line) from hero fee tile."""
    tiles = _hero_course_tiles(soup)
    duration = _full_time_duration(tiles.get("Duration", ""))
    for label, value in tiles.items():
        if not _INTL_FEE_TILE_RE.search(label):
            continue
        amount = _GBP_AMOUNT_RE.search(value)
        if not amount:
            continue
        digits = amount.group(1)
        fee_display = f"£{digits}" if "," in digits else f"£{int(digits):,}"
        return fee_display, duration
    return None


def _inject_international_fees_from_hero(soup: BeautifulSoup) -> None:
    hero_fee = _hero_international_fee_line(soup)
    if hero_fee is None:
        return
    fee_display, duration = hero_fee
    fees_root = soup.select_one("#fees-and-funding")
    if fees_root is None:
        host = _content_host(soup)
        if host is None:
            return
        fees_root = soup.new_tag("section", id="fees-and-funding")
        host.append(fees_root)
    existing = fees_root.select_one(f"#{BIRMINGHAM_HERO_FEES_ID}")
    if existing:
        existing.decompose()
    wrapper = soup.new_tag("div", id=BIRMINGHAM_HERO_FEES_ID)
    h3 = soup.new_tag("h3")
    h3.string = "International students"
    wrapper.append(h3)
    ul = soup.new_tag("ul")
    for line in ("Full Time", duration, fee_display):
        li = soup.new_tag("li")
        li.string = line
        ul.append(li)
    wrapper.append(ul)
    fees_root.insert(0, wrapper)


def _content_host(soup: BeautifulSoup):
    return soup.select_one("main") or soup.select_one("#main") or soup.body


def _inject_key_facts(soup: BeautifulSoup, code_dir: Path | None = None) -> None:
    host = _content_host(soup)
    if host is None:
        return
    existing = host.select_one(f"#{BIRMINGHAM_KEY_FACTS_ID}")
    if existing:
        existing.decompose()
    facts = _hero_tile_facts(soup, code_dir)
    if not facts:
        return
    wrapper = soup.new_tag("div", id=BIRMINGHAM_KEY_FACTS_ID)
    ul = soup.new_tag("ul")
    for label in _HERO_FACT_LABELS:
        value = facts.get(label)
        if not value:
            continue
        li = soup.new_tag("li")
        strong = soup.new_tag("strong")
        strong.string = f"{label}:"
        li.append(strong)
        li.append(f" {value}")
        ul.append(li)
    degree = facts.get("Degree name")
    if degree:
        li = soup.new_tag("li")
        strong = soup.new_tag("strong")
        strong.string = "Degree name:"
        li.append(strong)
        li.append(f" {degree}")
        ul.append(li)
        parser_award = soup.new_tag("li")
        parser_award.string = f"Award {degree}"
        ul.append(parser_award)
    wrapper.append(ul)
    host.insert(0, wrapper)


def _strip_uk_hero_fee_tiles(soup: BeautifulSoup) -> None:
    for tile in soup.select("article.course-tile"):
        title_el = tile.select_one(".course-tile__title")
        if not title_el:
            continue
        title = title_el.get_text(" ", strip=True)
        if _UK_FEE_TILE_RE.search(title):
            tile.decompose()


def _scholarship_cards(soup: BeautifulSoup) -> list[dict[str, object]]:
    cards: list[dict[str, object]] = []
    seen: set[str] = set()
    for card in soup.select("article.card-scholarship"):
        title_el = card.select_one(".card-scholarship__title")
        title = title_el.get_text(" ", strip=True) if title_el else ""
        if not title or title.casefold() in seen:
            continue
        seen.add(title.casefold())
        copy_el = card.select_one(".card-scholarship__copy")
        details: list[tuple[str, str]] = []
        for wrap in card.select(".card-scholarship__detail-wrapper"):
            label_el = wrap.select_one(".card-scholarship__detail-label")
            value_el = wrap.select_one(".card-scholarship__detail")
            label = (label_el.get_text(" ", strip=True) if label_el else "").rstrip(":")
            value = value_el.get_text(" ", strip=True) if value_el else ""
            if label and value:
                details.append((label, value))
        cards.append(
            {
                "title": title,
                "copy": copy_el.get_text(" ", strip=True) if copy_el else "",
                "details": details,
            }
        )
    return cards


def _scholarship_intro(soup: BeautifulSoup) -> tuple[str, str]:
    fees = soup.select_one("#course-fees")
    if fees is None:
        return "", ""
    for heading in fees.find_all("h3"):
        if heading.find_parent("article", class_="card-scholarship"):
            continue
        title = heading.get_text(" ", strip=True)
        if "scholarship" not in title.casefold():
            continue
        copy = ""
        for sibling in heading.find_next_siblings():
            if sibling.name in {"h2", "h3"}:
                break
            if sibling.name == "p":
                copy = sibling.get_text(" ", strip=True)
                break
        return title, copy
    return "", ""


def _inject_scholarships_from_course(soup: BeautifulSoup, code_dir: Path | None = None) -> None:
    host = _content_host(soup)
    if host is None:
        return
    existing = host.select_one(f"#{BIRMINGHAM_SCHOLARSHIPS_ID}")
    if existing:
        existing.decompose()
    cards = _scholarship_cards(soup)
    intro_title, intro_copy = _scholarship_intro(soup)
    if not cards and not intro_copy:
        return
    wrapper = soup.new_tag("div", id=BIRMINGHAM_SCHOLARSHIPS_ID)
    country = _course_page_country(code_dir or _CODE_DIR)
    country_p = soup.new_tag("p")
    country_p.string = f"Scholarship information for: {country}"
    wrapper.append(country_p)
    if intro_title:
        heading = soup.new_tag("h3")
        heading.string = intro_title
        wrapper.append(heading)
    if intro_copy:
        paragraph = soup.new_tag("p")
        paragraph.string = intro_copy
        wrapper.append(paragraph)
    for card in cards:
        heading = soup.new_tag("h3")
        heading.string = str(card["title"])
        wrapper.append(heading)
        copy = str(card.get("copy") or "")
        if copy:
            paragraph = soup.new_tag("p")
            paragraph.string = copy
            wrapper.append(paragraph)
        details = list(card.get("details") or [])
        if details:
            ul = soup.new_tag("ul")
            for label, value in details:
                li = soup.new_tag("li")
                strong = soup.new_tag("strong")
                strong.string = f"{label}:"
                li.append(strong)
                li.append(f" {value}")
                ul.append(li)
            wrapper.append(ul)
    host.append(wrapper)


def _strip_scholarship_carousels(soup: BeautifulSoup) -> None:
    for node in soup.select(".carousel__list, .scholarship-carousel, article.card-scholarship"):
        node.decompose()


def _promote_international_fees(soup: BeautifulSoup) -> None:
    fees = soup.select_one("#fees-and-funding")
    if fees is None:
        return
    for heading in fees.find_all(["h3", "h4", "h5"]):
        text = heading.get_text(" ", strip=True)
        if re.search(r"^uk\b", text, re.I) or "UK/Ireland" in text:
            section = heading.find_parent(["section", "div"]) or heading
            section.decompose()


def _keep_bangladesh_entry_only(soup: BeautifulSoup) -> None:
    entry = soup.select_one("#entry-requirements")
    if entry is None:
        return
    bangladesh_heading = None
    for h in entry.find_all(["h3", "h4"]):
        if "bangladesh" in h.get_text(" ", strip=True).casefold():
            bangladesh_heading = h
            break
    if bangladesh_heading is None:
        return
    intl = entry.select_one(".rich-text__container, [class*='international']")
    if intl is None:
        return
    for sibling in list(intl.find_all(["h3", "h4"])):
        if sibling is bangladesh_heading:
            continue
        if "bangladesh" not in sibling.get_text(" ", strip=True).casefold():
            block = sibling.find_parent("div") or sibling
            block.decompose()


def preprocess_course_html_uni(soup: BeautifulSoup) -> None:
    _strip_uk_hero_fee_tiles(soup)
    _inject_scholarships_from_course(soup)
    _strip_scholarship_carousels(soup)
    _promote_international_fees(soup)
    _inject_international_fees_from_hero(soup)
    _keep_bangladesh_entry_only(soup)
    _inject_key_facts(soup)


def _wait_for_hero_tiles(page) -> None:
    try:
        page.wait_for_selector(
            "ul.hero-courses__grid article.course-tile .course-tile__value",
            timeout=8000,
        )
    except Exception:
        pass
    page.wait_for_timeout(1200)


def _select_country_option(locator, country: str) -> bool:
    try:
        locator.select_option(label=country, timeout=8000)
        return True
    except Exception:
        try:
            locator.select_option(value=country, timeout=8000)
            return True
        except Exception:
            return False


def settle_course_page_after_download(
    page,
    url: str,
    code_dir: Path | None = None,
) -> None:
    """Select hero and scholarship country dropdowns before HTML snapshot."""
    if "birmingham.ac.uk" not in (url or "").casefold():
        return
    if "/study/postgraduate/" not in url and "/study/undergraduate/" not in url:
        return
    country = _course_page_country(code_dir) if code_dir is not None else "Bangladesh"
    selectors = (
        "#countryDropdownHero",
        "#countryDropdownScholarship",
        "select[name='countryDropdownHero']",
        "select[name='countryDropdownScholarship']",
    )
    selected = False
    for selector in selectors:
        loc = page.locator(selector)
        count = loc.count()
        for index in range(count):
            if _select_country_option(loc.nth(index), country):
                selected = True
    if not selected:
        return
    _wait_for_hero_tiles(page)
    try:
        page.wait_for_selector(
            "article.card-scholarship .card-scholarship__title",
            timeout=5000,
        )
    except Exception:
        pass
    page.wait_for_timeout(800)


def _inject_key_fact_bullets(markdown: str) -> str:
    facts: list[str] = []
    present = set(_KEY_FACTS_BULLET_RE.findall(markdown))
    for label in _HERO_FACT_LABELS:
        if label in present:
            continue
        match = re.search(
            rf"^(?:- )?(\*\*)?{re.escape(label)}:(\*\*)?\s*(.+?)\s*$",
            markdown,
            flags=re.M,
        )
        if match:
            value = match.group(3).strip()
            if label == "Start date":
                value = _expand_start_date(value)
            elif label == "Duration":
                value = _full_time_duration(value)
            facts.append(f"- **{label}:** {value}")
    if facts:
        h1 = re.search(r"^#\s+.+\n", markdown, flags=re.M)
        if h1:
            insert_at = h1.end()
            block = "\n".join(facts) + "\n\n"
            markdown = markdown[:insert_at] + "\n" + block + markdown[insert_at:].lstrip("\n")
    return _ensure_parser_award_line(markdown)


def _degree_from_markdown(markdown: str) -> str:
    named = re.search(
        r"(?m)^- \*\*Degree name:\*\*\s*(.+?)\s*$",
        markdown,
    )
    if named:
        degree = _degree_from_award_phrase(named.group(1))
        if degree:
            return degree
    award = re.search(
        r"(?m)^- \*\*Award:\*\*\s*(.+?)\s*$",
        markdown,
    )
    if award:
        degree = _degree_from_award_phrase(award.group(1))
        if degree:
            return degree
    h1 = re.search(r"(?m)^#\s+(.+)$", markdown)
    if h1:
        return _degree_from_award_phrase(h1.group(1))
    return ""


def _ensure_parser_award_line(markdown: str) -> str:
    if _PARSER_AWARD_RE.search(markdown):
        return markdown
    degree = _degree_from_markdown(markdown)
    if not degree:
        return markdown
    line = f"- Award {degree}\n"
    named = re.search(r"(?m)^- \*\*Degree name:\*\*\s*.+$", markdown)
    if named:
        insert_at = named.end()
        return markdown[:insert_at] + "\n" + line + markdown[insert_at:].lstrip("\n")
    duration = re.search(r"(?m)^- \*\*Duration:\*\*\s*.+$", markdown)
    if duration:
        insert_at = duration.end()
        return markdown[:insert_at] + "\n" + line + markdown[insert_at:].lstrip("\n")
    h1 = re.search(r"^#\s+.+\n", markdown, flags=re.M)
    if not h1:
        return markdown
    return markdown[: h1.end()] + "\n" + line + "\n" + markdown[h1.end():].lstrip("\n")


def _normalize_ielts_line(markdown: str) -> str:
    def repl(match: re.Match[str]) -> str:
        overall = match.group(1)
        section = match.group(2)
        return (
            f"For this course we require IELTS {overall} overall "
            f"with no less than {section} in each band"
        )

    return _IELTS_NORMALIZE_RE.sub(repl, markdown)


def _drop_course_summary_noise(markdown: str) -> str:
    return remove_markdown_heading_section(
        markdown,
        heading="Course summary",
        level=2,
        until_level=2,
    )


def _trim_entry_noise(markdown: str) -> str:
    text = _ORPHAN_ADDITIONAL_REQ_RE.sub(
        "### International entry requirements\n\n",
        markdown,
    )
    text = re.sub(
        r"(?m)^Contact the admissions department\s*\n+",
        "",
        text,
    )
    return text


def _inject_fees_block_if_missing(markdown: str) -> str:
    if _FEES_SECTION_RE.search(markdown):
        return markdown
    fee_match = re.search(
        r"Fees\s*\(international\)\s*\n+£([\d,]+)",
        markdown,
        re.I,
    )
    if not fee_match:
        fee_match = re.search(
            r"- \*\*Fees \(international\):\*\*\s*£([\d,]+)",
            markdown,
            re.I,
        )
    if not fee_match:
        return markdown
    fee = fee_match.group(1)
    fee_display = f"£{fee}" if "," in fee else f"£{int(fee):,}"
    duration = "1 year full-time"
    dur_match = re.search(r"- \*\*Duration:\*\*\s*([^\n]+)", markdown, re.I)
    if dur_match:
        duration = _full_time_duration(dur_match.group(1))
    block = (
        "## Fees and funding\n\n"
        "### International students\n\n"
        f"- Full Time\n- {duration}\n- {fee_display}\n\n"
    )
    entry = re.search(r"(?m)^## Entry requirements\s*$", markdown)
    if entry:
        return markdown[: entry.start()] + block + markdown[entry.start() :]
    h1 = re.search(r"(?m)^#\s+.+\n", markdown)
    insert = h1.end() if h1 else 0
    return markdown[:insert] + "\n" + block + markdown[insert:].lstrip("\n")


def cleanup_course_markdown_uni(markdown: str) -> str:
    text = _drop_course_summary_noise(markdown)
    text = _inject_key_fact_bullets(text)
    text = _inject_fees_block_if_missing(text)
    text = _trim_entry_noise(text)
    text = _normalize_ielts_line(text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    return text


if __name__ == "__main__":
    raise SystemExit(main())
