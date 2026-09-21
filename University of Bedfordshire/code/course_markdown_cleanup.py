"""University of Bedfordshire — course HTML/markdown cleanup."""

from __future__ import annotations

import importlib.util
import io
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None  # type: ignore[misc, assignment]

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

_shared_cleanup_spec = importlib.util.spec_from_file_location(
    "shared_course_markdown_cleanup",
    _SHARED / "course_markdown_cleanup.py",
)
assert _shared_cleanup_spec and _shared_cleanup_spec.loader
_shared_cleanup = importlib.util.module_from_spec(_shared_cleanup_spec)
_shared_cleanup_spec.loader.exec_module(_shared_cleanup)
main = _shared_cleanup.main

_INTERNATIONAL_STUDY_TYPE = "International"
_COURSE_DATA_LIST_RE = re.compile(
    r"const\s+courseDataList\s*=\s*(\[.*?\])\s*;",
    re.DOTALL,
)
_CODE_ENV = Path(__file__).resolve().parent / ".env"
_UNI_ROOT = Path(__file__).resolve().parents[1]
_LEGACY_SPEC_CACHE_DIR = _UNI_ROOT / "output" / "course_specs"

# Playwright + preprocess share these (.env keys COURSE_DOWNLOAD_*)
_SELECTOR_ENV_KEYS = {
    "study_type": "COURSE_DOWNLOAD_STUDY_TYPE",
    "study_mode": "COURSE_DOWNLOAD_STUDY_MODE",
    "intake_month": "COURSE_DOWNLOAD_INTAKE_MONTH",
    "location": "COURSE_DOWNLOAD_LOCATION",
    "intake_year": "COURSE_DOWNLOAD_INTAKE_YEAR",
}
_SELECTOR_DEFAULTS = {
    "study_type": "International",
    "study_mode": "Full-time",
    "intake_month": "September",
    "location": "",
    "intake_year": "2026",
}


def _read_code_env() -> dict[str, str]:
    if not _CODE_ENV.exists():
        return {}
    values: dict[str, str] = {}
    for raw in _CODE_ENV.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def course_selector_preferences() -> dict[str, str]:
    env = _read_code_env()
    prefs = dict(_SELECTOR_DEFAULTS)
    for field, env_key in _SELECTOR_ENV_KEYS.items():
        if env.get(env_key):
            prefs[field] = env[env_key].strip()
    return prefs


def _decompose(node: Tag | None) -> None:
    if node is not None:
        node.decompose()


def _activate_international_fee_panels(fees_root: Tag) -> None:
    """Mirror selecting Home/International → International on the live course page."""
    for admission in fees_root.find_all(
        "div",
        attrs={"data-course-admission": True},
        recursive=False,
    ):
        classes = admission.get("class") or []
        if isinstance(classes, str):
            classes = classes.split()
        if "d-none" in classes:
            _decompose(admission)
            continue

        for uk_panel in admission.select(
            '.accordion-tabs__tab-panel[data-study-type="The UK"]'
        ):
            _decompose(uk_panel)
        for uk_tab in admission.select(
            '.accordion-tabs__tab button[data-study-type="The UK"]'
        ):
            _decompose(uk_tab.parent if uk_tab.parent else uk_tab)

        for intl_panel in admission.select(
            '.accordion-tabs__tab-panel[data-study-type="International"]'
        ):
            panel_classes = intl_panel.get("class") or []
            if isinstance(panel_classes, str):
                panel_classes = panel_classes.split()
            if "d-none" in panel_classes:
                panel_classes = [c for c in panel_classes if c != "d-none"]
            if "is-active" not in panel_classes:
                panel_classes.append("is-active")
            intl_panel["class"] = panel_classes
            intl_panel["aria-hidden"] = "false"
            content_btn = intl_panel.select_one(".accordion-tabs__content-btn")
            if content_btn:
                content_btn["aria-expanded"] = "true"

        for intl_tab in admission.select(
            '.accordion-tabs__tab button[data-study-type="International"]'
        ):
            intl_tab["aria-selected"] = "true"
        for uk_tab in admission.select(
            '.accordion-tabs__tab button[data-study-type="The UK"]'
        ):
            uk_tab["aria-selected"] = "false"


def _parse_course_data_list(soup: BeautifulSoup) -> list[dict[str, Any]]:
    for script in soup.find_all("script"):
        text = script.string or script.get_text() or ""
        match = _COURSE_DATA_LIST_RE.search(text)
        if match:
            try:
                data = json.loads(match.group(1))
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                continue
    return []


def _variant_mode_value(variant: dict[str, Any]) -> str:
    modes = variant.get("studyModes") or []
    if not modes:
        return ""
    first = modes[0]
    if isinstance(first, dict):
        return str(first.get("value") or "")
    return str(first)


def _variant_intake_value(variant: dict[str, Any]) -> str:
    months = variant.get("intakeMonths") or []
    if not months:
        return ""
    first = months[0]
    if isinstance(first, dict):
        return str(first.get("value") or "")
    return str(first)


def _variant_location_value(variant: dict[str, Any]) -> str:
    location = variant.get("location") or {}
    if isinstance(location, dict):
        return str(location.get("value") or "")
    return str(location)


def _matches_study_mode(variant: dict[str, Any], study_mode: str) -> bool:
    mode_value = _variant_mode_value(variant)
    if not study_mode:
        return True
    if study_mode == "Full-time":
        return mode_value == "Full-time"
    return study_mode in mode_value


def pick_course_admission_key(
    variants: list[dict[str, Any]],
    prefs: dict[str, str],
) -> str | None:
    if not variants:
        return None
    intake_month = prefs.get("intake_month") or ""
    location = prefs.get("location") or ""
    study_mode = prefs.get("study_mode") or "Full-time"

    candidates = [
        variant
        for variant in variants
        if _matches_study_mode(variant, study_mode)
        and (not intake_month or _variant_intake_value(variant) == intake_month)
        and (not location or _variant_location_value(variant) == location)
    ]
    if not candidates:
        candidates = [
            variant
            for variant in variants
            if _matches_study_mode(variant, study_mode)
            and (not intake_month or _variant_intake_value(variant) == intake_month)
        ]
    if not candidates:
        candidates = [v for v in variants if _matches_study_mode(v, study_mode)]
    if not candidates:
        candidates = list(variants)
    if not location:
        luton = [
            v
            for v in candidates
            if "luton" in _variant_location_value(v).casefold()
        ]
        if luton:
            candidates = luton
    key = candidates[0].get("key")
    return str(key) if key else None


def _set_select_value(select: Tag | None, value: str) -> None:
    if not select or not value:
        return
    for option in select.select("option"):
        if option.get("value") == value:
            option["selected"] = "selected"
        elif option.has_attr("selected"):
            del option["selected"]


def _unhide_tag(tag: Tag) -> None:
    classes = tag.get("class") or []
    if isinstance(classes, str):
        classes = classes.split()
    if "d-none" in classes:
        tag["class"] = [c for c in classes if c != "d-none"]


def _keep_admission_variant(soup: BeautifulSoup, admission_key: str) -> None:
    entry = soup.select_one("#entryRequirements")
    if entry is not None:
        for row in entry.select(".header-row[data-course-admission]"):
            if row.get("data-course-admission") != admission_key:
                _decompose(row)
            else:
                _unhide_tag(row)

    fees = soup.select_one("#feesFunding")
    if fees is not None:
        for admission in fees.find_all(
            "div",
            attrs={"data-course-admission": True},
            recursive=False,
        ):
            if admission.get("data-course-admission") != admission_key:
                _decompose(admission)
            else:
                _unhide_tag(admission)
        _activate_international_fee_panels(fees)


def find_course_specification_pdf_url(soup: BeautifulSoup, base_url: str) -> str | None:
    for anchor in soup.select('a[href*=".pdf"]'):
        href = (anchor.get("href") or "").strip()
        if not href:
            continue
        title = (anchor.get("title") or "").casefold()
        text = anchor.get_text(" ", strip=True).casefold()
        if (
            "course specification" in title
            or "course specification" in text
            or "_ucif" in href.casefold()
        ):
            return urljoin(base_url, href)
    return None


def extract_first_page_text(pdf_bytes: bytes) -> str:
    if not pdf_bytes or PdfReader is None:
        return ""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        if not reader.pages:
            return ""
        return reader.pages[0].extract_text() or ""
    except Exception:
        return ""


def _clean_duration_phrase(raw: str) -> str:
    phrase = re.sub(r"\s+", " ", raw).strip(" .;:")
    if len(phrase) < 3:
        return ""
    return phrase


def parse_duration_from_spec_text(text: str) -> str:
    """Parse UCIF / course specification page 1 for a duration phrase."""
    if not text:
        return ""
    flat = re.sub(r"\s+", " ", text)
    patterns = (
        r"(?:Course\s+)?duration\s*(?:\(months?\))?\s*:?\s*([0-9]+\s*(?:years?|months?)(?:\s+full[-\s]?time)?)",
        r"Length\s+of\s+course\s*:?\s*([^:]+?)(?:\s{2,}|$)",
        r"Normal\s+duration\s*:?\s*([^:]+?)(?:\s{2,}|$)",
        r"Mode\s+and\s+duration\s*:?\s*([^:]+?)(?:\s{2,}|$)",
        r"((?:One|Two|Three|Four|\d+)\s+years?(?:\s+full[-\s]?time)?)",
        r"(\d+\s+months?(?:\s+full[-\s]?time)?)",
    )
    for pattern in patterns:
        match = re.search(pattern, flat, re.I)
        if match:
            cleaned = _clean_duration_phrase(match.group(1))
            if cleaned and cleaned.casefold() not in {"none", "n/a", "not applicable"}:
                return cleaned
    return ""


_AWARD_TOKEN_RE = re.compile(
    r"\b(BSc|BA|BBA|BEng|LLB|MSc|MA|MBA|MFA|PhD|MRes|PGDip|PGCert|FdSc|CertHE|MEng|LLM|BM BS)\b",
    re.I,
)

_MONTH_BY_TOKEN: dict[str, str] = {
    "jan": "January",
    "january": "January",
    "feb": "February",
    "february": "February",
    "mar": "March",
    "march": "March",
    "apr": "April",
    "april": "April",
    "may": "May",
    "jun": "June",
    "june": "June",
    "jul": "July",
    "july": "July",
    "aug": "August",
    "august": "August",
    "sep": "September",
    "sept": "September",
    "september": "September",
    "oct": "October",
    "october": "October",
    "nov": "November",
    "november": "November",
    "dec": "December",
    "december": "December",
}


def _normalize_award_from_spec(raw: str) -> str:
    text = re.sub(r"\s+", " ", (raw or "").strip(" .;:"))
    if not text:
        return ""
    match = _AWARD_TOKEN_RE.search(text)
    if match:
        return match.group(1)
    return text.split()[0] if text.split() else ""


def parse_final_award_from_spec_text(text: str) -> str:
    """Parse UCIF page 1 field *Final award* (e.g. MSc)."""
    if not text:
        return ""
    flat = re.sub(r"\s+", " ", text)
    patterns = (
        r"Final\s+award\s*:?\s*([A-Za-z][A-Za-z+. /&()-]{0,60}?)(?=\s+Standard\s+intake|\s+Course\s+|\s+Length\s+|\s+UCAS|\s+Credit|\s+Mode\s+|$)",
        r"Qualification\s+aim\s*:?\s*([^:]+?)(?:\s{2,}|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, flat, re.I)
        if match:
            award = _normalize_award_from_spec(match.group(1))
            if award and award.casefold() not in {"none", "n/a", "not applicable"}:
                return award
    return ""


def _expand_intake_month_token(token: str) -> str:
    cleaned = re.sub(r"[^A-Za-z]", "", (token or "").strip())
    if not cleaned:
        return ""
    return _MONTH_BY_TOKEN.get(cleaned.casefold(), "")


def parse_standard_intake_months_from_spec_text(text: str) -> list[str]:
    """Parse *Standard intake points (months)* from UCIF (e.g. Feb, Sep)."""
    if not text:
        return []
    flat = re.sub(r"\s+", " ", text)
    match = re.search(
        r"Standard\s+intake\s+points?\s*(?:\([^)]*\))?\s*:?\s*"
        r"([A-Za-z][A-Za-z0-9,./;&\s-]{1,120}?)"
        r"(?=\s{2,}|\.|Course\s|Final\s+award|Length\s+of|UCAS|Credit\s+level|$)",
        flat,
        re.I,
    )
    if not match:
        match = re.search(
            r"Standard\s+intake\s+point\s*:?\s*"
            r"([A-Za-z][A-Za-z0-9,./;&\s-]{1,120}?)"
            r"(?=\s{2,}|\.|Course\s|Final\s+award|$)",
            flat,
            re.I,
        )
    if not match:
        return []
    raw = match.group(1).strip(" .;:")
    months: list[str] = []
    seen: set[str] = set()
    for part in re.split(r"[,/&;]+|\s+and\s+", raw, flags=re.I):
        month = _expand_intake_month_token(part)
        if month and month not in seen:
            seen.add(month)
            months.append(month)
    return months


def _course_slug_from_url(course_url: str) -> str:
    path = urlparse(course_url).path.strip("/")
    if path.startswith("courses/"):
        path = path[len("courses/") :]
    return path.replace("/", "-") or "course"


def _remove_legacy_spec_pdf_cache(course_url: str) -> None:
    path = _LEGACY_SPEC_CACHE_DIR / f"{_course_slug_from_url(course_url)}.pdf"
    if path.is_file():
        try:
            path.unlink()
        except OSError:
            pass


def _ensure_spec_pdf_marker(soup: BeautifulSoup) -> Tag:
    marker = soup.select_one("#bedsSpecFromPdf") or soup.select_one("#bedsSpecDuration")
    if marker is None:
        marker = soup.new_tag("div", id="bedsSpecFromPdf", attrs={"hidden": "hidden"})
        anchor = soup.select_one("h1.title") or soup.find("h1")
        if anchor is not None:
            anchor.insert_before(marker)
        elif soup.body:
            soup.body.insert(0, marker)
    return marker


def _set_spec_pdf_marker(
    soup: BeautifulSoup,
    *,
    duration: str = "",
    final_award: str = "",
    intake_months: list[str] | None = None,
) -> None:
    marker = _ensure_spec_pdf_marker(soup)
    if duration:
        marker["data-duration"] = duration
    if final_award:
        marker["data-final-award"] = final_award
    if intake_months:
        marker["data-intake-months"] = ",".join(intake_months)


def _fetch_spec_pdf_bytes(page, pdf_url: str, course_url: str) -> bytes | None:
    if page is None:
        return None
    locator = page.locator(
        'a[href*=".pdf"][title*="course specification" i], a[href*="_ucif" i]'
    ).first
    try:
        if locator.count() > 0:
            with page.expect_download(timeout=45000) as download_info:
                locator.click(timeout=15000)
            download = download_info.value
            path = download.path()
            if path:
                data = Path(path).read_bytes()
                try:
                    download.delete()
                except Exception:
                    try:
                        Path(path).unlink(missing_ok=True)
                    except OSError:
                        pass
                if data[:4] == b"%PDF":
                    return data
    except Exception:
        pass
    try:
        response = page.context.request.get(
            pdf_url,
            headers={"Referer": course_url},
            timeout=60000,
        )
        if response.ok and response.body()[:4] == b"%PDF":
            return response.body()
    except Exception:
        pass
    return None


def _spec_pdf_marker(soup: BeautifulSoup) -> Tag | None:
    return soup.select_one("#bedsSpecFromPdf") or soup.select_one("#bedsSpecDuration")


def _resolve_spec_duration(soup: BeautifulSoup, course_url: str = "") -> str:
    marker = _spec_pdf_marker(soup)
    if marker is not None:
        embedded = (marker.get("data-duration") or "").strip()
        if embedded:
            return embedded
    return ""


def _resolve_spec_final_award(soup: BeautifulSoup) -> str:
    marker = _spec_pdf_marker(soup)
    if marker is None:
        return ""
    return (marker.get("data-final-award") or "").strip()


def _resolve_spec_intake_months(soup: BeautifulSoup) -> list[str]:
    marker = _spec_pdf_marker(soup)
    if marker is None:
        return []
    raw = (marker.get("data-intake-months") or "").strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def enrich_downloaded_course_html(html: str, page, course_url: str) -> str:
    """Download UCIF PDF in-browser and embed duration for preprocess (needs CDP/CF session)."""
    env = _read_code_env()
    flag = (env.get("COURSE_DOWNLOAD_FETCH_SPEC_PDF") or "true").strip().lower()
    if flag in {"0", "false", "no"}:
        return html
    soup = BeautifulSoup(html, "html.parser")
    base = f"{urlparse(course_url).scheme}://{urlparse(course_url).netloc}"
    pdf_url = find_course_specification_pdf_url(soup, base)
    if not pdf_url:
        return html
    pdf_bytes = _fetch_spec_pdf_bytes(page, pdf_url, course_url)
    if not pdf_bytes:
        print(f"    UCIF PDF not fetched (bot block?): {pdf_url}")
        return html
    page_text = extract_first_page_text(pdf_bytes)
    duration = parse_duration_from_spec_text(page_text)
    final_award = parse_final_award_from_spec_text(page_text)
    intake_months = parse_standard_intake_months_from_spec_text(page_text)
    del pdf_bytes
    _remove_legacy_spec_pdf_cache(course_url)
    if duration or final_award or intake_months:
        _set_spec_pdf_marker(
            soup,
            duration=duration,
            final_award=final_award,
            intake_months=intake_months,
        )
        parts = []
        if final_award:
            parts.append(f"award={final_award}")
        if intake_months:
            parts.append(f"intake={','.join(intake_months)}")
        if duration:
            parts.append(f"duration={duration}")
        print(f"    UCIF: {'; '.join(parts)} (PDF discarded)")
    return str(soup)


def _infer_academic_year(soup: BeautifulSoup, fallback: str) -> str:
    fees = soup.select_one("#feesFunding")
    if fees is None:
        return fallback
    text = fees.get_text(" ", strip=True)
    match = re.search(r"20(\d{2})/(\d{2})", text)
    if match:
        return f"20{match.group(1)}"
    return fallback


def _inject_key_facts(
    soup: BeautifulSoup,
    variant: dict[str, Any],
    prefs: dict[str, str],
) -> None:
    existing = soup.select_one("#bedsKeyFacts")
    if existing is not None:
        _decompose(existing)
    pdf_intake_months = _resolve_spec_intake_months(soup)
    variant_intake = _variant_intake_value(variant)
    intake_month = variant_intake or prefs.get("intake_month") or ""
    year = _infer_academic_year(soup, prefs.get("intake_year") or "2026")
    final_award = _resolve_spec_final_award(soup)
    location = _variant_location_value(variant)
    ucas = ""
    ucas_obj = variant.get("ucasCode") or {}
    if isinstance(ucas_obj, dict):
        ucas = str(ucas_obj.get("displayText") or ucas_obj.get("value") or "").strip()
    duration = ""
    dur_obj = variant.get("duration") or {}
    if isinstance(dur_obj, dict):
        duration = str(dur_obj.get("displayText") or dur_obj.get("value") or "").strip()
    if duration.casefold() in {"", "none specified"}:
        duration = ""
    if not duration:
        canonical = ""
        link = soup.select_one('link[rel="canonical"]')
        if link and link.get("href"):
            canonical = link["href"].strip()
        duration = _resolve_spec_duration(soup, canonical)

    root = soup.new_tag("div", id="bedsKeyFacts")
    if pdf_intake_months:
        start_dates = ", ".join(f"{month} {year}" for month in pdf_intake_months)
        line = soup.new_tag("p")
        line.string = f"- **Start date:** {start_dates}"
        root.append(line)
    elif intake_month:
        line = soup.new_tag("p")
        line.string = f"- **Start date:** {intake_month} {year}"
        root.append(line)
    if final_award:
        line = soup.new_tag("p")
        line.string = f"- Award {final_award}"
        root.append(line)
    if duration:
        line = soup.new_tag("p")
        line.string = f"**Duration:** {duration}"
        root.append(line)
    if location:
        line = soup.new_tag("p")
        line.string = f"- **Location:** {location}"
        root.append(line)
    if ucas:
        line = soup.new_tag("p")
        line.string = f"- **UCAS code:** {ucas}"
        root.append(line)
    if not root.contents:
        return
    anchor = soup.select_one("h1.title") or soup.find("h1")
    if anchor is not None:
        anchor.insert_after(root)
    else:
        soup.body.insert(0, root) if soup.body else None


def preprocess_course_html_uni(soup: BeautifulSoup) -> None:
    """Apply course-selector choices: International + preferred intake/mode/location."""
    prefs = course_selector_preferences()
    variants = _parse_course_data_list(soup)
    admission_key = pick_course_admission_key(variants, prefs)
    chosen = next((v for v in variants if v.get("key") == admission_key), None)

    _set_select_value(soup.select_one("#studyType"), prefs.get("study_type") or _INTERNATIONAL_STUDY_TYPE)
    _set_select_value(soup.select_one("#studyMode"), prefs.get("study_mode") or "Full-time")
    _set_select_value(soup.select_one("#intakeMonth"), prefs.get("intake_month") or "")
    _set_select_value(soup.select_one("#location"), prefs.get("location") or "")

    if admission_key:
        _keep_admission_variant(soup, admission_key)
    else:
        fees = soup.select_one("#feesFunding")
        if fees is not None:
            _activate_international_fee_panels(fees)

    if chosen:
        _inject_key_facts(soup, chosen, prefs)

    for selector in (".course-selector", ".apply-now"):
        for node in soup.select(selector):
            _decompose(node)


_OVERVIEW_H2 = frozenset({"course overview", "about the course"})


def _strip_overview_sections(markdown: str) -> str:
    """Drop #course-section marketing copy (About the course + accreditation accordions)."""
    lines = markdown.splitlines()
    out: list[str] = []
    skipping = False
    for line in lines:
        if re.match(r"^##\s+", line):
            title = re.sub(r"^##\s+", "", line).strip().casefold()
            if title in _OVERVIEW_H2:
                skipping = True
                continue
            skipping = False
        if not skipping:
            out.append(line)
    return "\n".join(out).strip() + "\n"


def cleanup_course_markdown_uni(markdown: str) -> str:
    markdown = _strip_overview_sections(markdown)
    lines = markdown.splitlines()
    out: list[str] = []
    skip = False
    for line in lines:
        if re.match(r"^###\s+UK\s*$", line, re.I):
            skip = True
            continue
        if skip and line.startswith("### "):
            skip = False
        if not skip:
            out.append(line)
    return "\n".join(out).strip() + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
