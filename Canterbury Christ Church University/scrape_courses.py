#!/usr/bin/env python3
"""Canterbury Christ Church University course scraper.

CCCU course pages live under /study-here/courses/{slug}.
Listing URLs are configured in .env (COURSE_LISTING_1 / COURSE_LISTING_2).
Run one programme at a time (undergraduate, postgraduate-taught, foundation-year).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

UNIVERSITY_DIR = Path(__file__).resolve().parent
MASTER_SHEET = "Master Sheet.csv"
COURSE_URLS_CSV = "course_urls.csv"
FAILED_URLS_CSV = "failed_urls.csv"
COURSE_PAGE_MAP_CSV = "course_page_map.csv"
COURSE_PAGES_DIR = "course_pages"
PROGRESS_FILE = "scrape_progress.json"
LOG_FILE = "scrape.log"

DOMAIN = "www.canterbury.ac.uk"
BASE_URL = f"https://{DOMAIN}"
COURSE_PATH_RE = re.compile(
    r"^/study-here/courses/[a-z0-9][a-z0-9\-]+(?:/[a-z0-9][a-z0-9\-]+)?$",
    re.I,
)
COURSE_URL_RE = re.compile(
    rf"https?://{re.escape(DOMAIN)}/study-here/courses/[a-z0-9][a-z0-9\-]+(?:/[a-z0-9][a-z0-9\-]+)?",
    re.I,
)
REL_COURSE_PATH_RE = re.compile(
    r"/study-here/courses/[a-z0-9][a-z0-9\-]+(?:/[a-z0-9][a-z0-9\-]+)?",
    re.I,
)

PAGINATION_EMPTY_LIMIT = 5
LISTING_DOWNLOAD_RETRIES = 5
ENV_FILE = ".env"

# Listing URLs come from .env only (COURSE_LISTING_1 / COURSE_LISTING_2).
# Change .env per programme, run --urls-only --fresh, then --append-urls for the next.
SEARCH_PATH_LABELS = {
    "/search/undergraduate-courses": "undergraduate",
    "/search/postgraduate-taught-courses": "postgraduate-taught",
    "/search/foundation-year": "foundation-year",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def log_timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


class ScrapeLogger:
    def __init__(self, university_dir: Path):
        self.log_path = university_dir / LOG_FILE
        self.started_at = time.time()

    def write(self, level: str, message: str) -> None:
        line = f"{log_timestamp()} [{level}] {message}\n"
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(line)

    def start(self, mode: str, **flags: object) -> None:
        flag_text = " ".join(f"{key}={value}" for key, value in flags.items())
        self.write("START", f"mode={mode} {flag_text}".strip())

    def info(self, message: str) -> None:
        self.write("INFO", message)

    def ok(self, message: str) -> None:
        self.write("OK", message)

    def error(self, message: str) -> None:
        self.write("ERROR", message)

    def end(self, status: str, **stats: object) -> None:
        duration = int(time.time() - self.started_at)
        stat_text = " ".join(f"{key}={value}" for key, value in stats.items())
        self.write("END", f"status={status} duration={duration}s {stat_text}".strip())


def normalize_url(url: str, base: str | None = None, keep_query: bool = False) -> str:
    url = url.strip()
    if base:
        url = urljoin(base, url)
    parsed = urlparse(url)
    if keep_query:
        normalized = parsed._replace(fragment="").geturl()
    else:
        normalized = parsed._replace(fragment="", query="").geturl()
    return normalized.rstrip("/")


def is_empty(value: str | None) -> bool:
    return value is None or str(value).strip() == ""


def read_master_sheet(university_dir: Path) -> dict[str, str]:
    sheet_path = university_dir / MASTER_SHEET
    if not sheet_path.exists():
        raise FileNotFoundError(f"Master sheet not found: {sheet_path}")
    with sheet_path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"No data rows in {sheet_path}")
    return rows[0]


def load_env_file(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def infer_listing_programme(url: str) -> str:
    path_key = listing_path_key(url)
    if path_key in SEARCH_PATH_LABELS:
        return SEARCH_PATH_LABELS[path_key]
    slug = path_key.rsplit("/", 1)[-1]
    return slug.replace("-", " ")


def get_listing_config(university_dir: Path) -> dict[str, object]:
    env_path = university_dir / ENV_FILE
    env = load_env_file(env_path)
    seeds: list[str] = []
    seen: set[str] = set()
    for key in ("COURSE_LISTING_1", "COURSE_LISTING_2"):
        value = env.get(key, "").strip()
        if is_empty(value):
            continue
        url = normalize_url(value, keep_query=True)
        if "/search/" not in urlparse(url).path:
            raise ValueError(f"{key} must be a CCCU /search/ listing URL: {value}")
        if url not in seen:
            seen.add(url)
            seeds.append(url)

    if not seeds:
        raise ValueError(
            f"Set COURSE_LISTING_1 in {env_path} before URL extraction.\n"
            "Copy .env.example to .env and set listing URLs for one programme at a time."
        )

    programme = env.get("LISTING_PROGRAMME", "").strip() or infer_listing_programme(seeds[0])
    search_paths = sorted({listing_path_key(url) for url in seeds})
    if len(search_paths) > 1:
        raise ValueError(
            "COURSE_LISTING_1 and COURSE_LISTING_2 must use the same search path "
            f"(found: {', '.join(search_paths)})"
        )

    return {
        "env_path": str(env_path),
        "programme": programme,
        "seeds": seeds,
        "search_path": search_paths[0],
    }


def listing_path_key(url: str) -> str:
    parsed = urlparse(url)
    return parsed.path.rstrip("/").lower()


def get_page_index(url: str) -> int:
    params = parse_qs(urlparse(url).query, keep_blank_values=True)
    values = params.get("pageIndex") or params.get("pageindex") or ["1"]
    try:
        return max(1, int(values[0]))
    except ValueError:
        return 1


def set_page_index(url: str, page_index: int) -> str:
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    params["pageIndex"] = [str(page_index)]
    return urlunparse(parsed._replace(query=urlencode(params, doseq=True)))


def get_listing_result_info(html: str) -> tuple[int | None, int | None, int | None]:
    match = re.search(
        r"Displaying\s+(\d+)\s*-\s*(\d+)\s+of\s+(\d+)\s+results",
        html,
        re.I,
    )
    if not match:
        return None, None, None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def estimated_total_pages(total_results: int, page_size: int) -> int:
    if total_results <= 0 or page_size <= 0:
        return 0
    return (total_results + page_size - 1) // page_size


def build_search_groups(seed_urls: list[str]) -> dict[str, str]:
    groups: dict[str, str] = {}
    for url in seed_urls:
        key = listing_path_key(url)
        if key not in groups or get_page_index(url) < get_page_index(groups[key]):
            groups[key] = set_page_index(url, 1)
    return groups


def is_valid_course_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in {DOMAIN, "canterbury.ac.uk"}:
        return False
    path = parsed.path.rstrip("/")
    if not COURSE_PATH_RE.match(path + ("" if path else "")):
        return False
    slug = path.rsplit("/", 1)[-1].lower()
    excluded = {
        "study-here",
        "courses",
        "search",
        "applying",
        "visit-us",
        "postgraduate",
        "undergraduate",
        "foundation-year",
    }
    return slug not in excluded


def extract_course_urls_from_html(html: str, base_url: str = BASE_URL) -> set[str]:
    urls: set[str] = set()

    for match in COURSE_URL_RE.findall(html):
        absolute = normalize_url(match)
        if is_valid_course_url(absolute):
            urls.add(absolute)

    for match in REL_COURSE_PATH_RE.findall(html):
        absolute = normalize_url(match, base_url)
        if is_valid_course_url(absolute):
            urls.add(absolute)

    soup = BeautifulSoup(html, "html.parser")
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = normalize_url(href, base_url)
        if is_valid_course_url(absolute):
            urls.add(absolute)

    return urls


def merge_course_urls(existing: set[str], new_urls: set[str]) -> list[str]:
    merged = set(existing)
    merged.update(new_urls)
    return sorted(merged)


def write_tab_csv(path: Path, headers: list[str], rows: list[list[str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        handle.write("sep=\t\n")
        writer = csv.writer(handle, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(headers)
        writer.writerows(rows)
    return path


def write_course_urls_csv(university_dir: Path, urls: list[str]) -> Path:
    unique = merge_course_urls(set(), set(urls))
    return write_tab_csv(
        university_dir / COURSE_URLS_CSV,
        ["course_url"],
        [[url] for url in unique],
    )


def read_course_urls_csv(university_dir: Path) -> list[str]:
    csv_path = university_dir / COURSE_URLS_CSV
    if not csv_path.exists():
        raise FileNotFoundError(f"{csv_path} not found. Run URL extraction first.")
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        text = handle.read()
    if text.startswith("sep="):
        text = text.split("\n", 1)[1]
    delimiter = "\t" if text.splitlines() and "\t" in text.splitlines()[0] else ","
    reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
    field = "course_url" if "course_url" in (reader.fieldnames or []) else reader.fieldnames[0]
    return merge_course_urls(set(), {row[field].strip() for row in reader if row.get(field, "").strip()})


def sync_output_csvs(university_dir: Path, progress: dict | None) -> None:
    urls = progress.get("course_urls", []) if progress else read_course_urls_csv(university_dir)
    write_course_urls_csv(university_dir, urls)

    page_map_rows: list[list[str]] = []
    pages_dir = university_dir / COURSE_PAGES_DIR
    if pages_dir.exists():
        for html_path in sorted(pages_dir.glob("*.html")):
            saved = read_saved_url(html_path)
            if saved and is_valid_course_url(saved):
                page_map_rows.append([saved, f"{COURSE_PAGES_DIR}/{html_path.name}"])
    write_tab_csv(
        university_dir / COURSE_PAGE_MAP_CSV,
        ["course_url", "html_file"],
        page_map_rows,
    )

    failed = progress.get("failed_urls", []) if progress else []
    write_tab_csv(
        university_dir / FAILED_URLS_CSV,
        ["course_url"],
        [[url] for url in sorted(set(failed))],
    )


def load_progress(university_dir: Path) -> dict | None:
    path = university_dir / PROGRESS_FILE
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_progress(university_dir: Path, progress: dict) -> None:
    progress["updated_at"] = utc_now()
    (university_dir / PROGRESS_FILE).write_text(json.dumps(progress, indent=2), encoding="utf-8")


def clear_progress(university_dir: Path, *, keep_course_urls: bool = False) -> None:
    progress_path = university_dir / PROGRESS_FILE
    if progress_path.exists():
        progress_path.unlink()
    if not keep_course_urls:
        urls_path = university_dir / COURSE_URLS_CSV
        if urls_path.exists():
            urls_path.unlink()


def new_progress(phase: str, listing_config: dict[str, object] | None = None) -> dict:
    progress: dict = {
        "approach": "cccu_search_pageIndex_env",
        "phase": phase,
        "course_urls": [],
        "listing_programme": "",
        "listing_seeds": [],
        "search_path": "",
        "pages_scraped": 0,
        "pages_total": None,
        "listing_completed": [],
        "listing_pending": [],
        "group_state": {},
        "empty_pages": 0,
        "downloaded_urls": [],
        "failed_urls": [],
        "updated_at": utc_now(),
    }
    if listing_config:
        progress["listing_programme"] = listing_config["programme"]
        progress["listing_seeds"] = listing_config["seeds"]
        progress["search_path"] = listing_config["search_path"]
    return progress


def sanitize_filename(title: str, max_length: int = 180) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", title)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip(" .")
    return cleaned or "course_page"


def read_saved_url(html_path: Path) -> str | None:
    text = html_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"<!-- saved from url=\(([^)]+)\)", text, re.I)
    if match:
        return match.group(1).strip()
    soup = BeautifulSoup(text, "html.parser")
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        return canonical["href"].strip()
    return None


def inject_saved_url_comment(html: str, url: str) -> str:
    if re.search(r"<!-- saved from url=\(", html, re.I):
        return html
    return f"<!-- saved from url=({url}) -->\n{html}"


def dismiss_cookie_banner(page) -> None:
    selectors = [
        "#ccc-notify-accept",
        "button:has-text('Accept all')",
        "button:has-text('Accept')",
        "#onetrust-accept-btn-handler",
    ]
    for selector in selectors:
        try:
            button = page.locator(selector).first
            if button.is_visible(timeout=1500):
                button.click(timeout=3000)
                page.wait_for_timeout(500)
                return
        except (PlaywrightTimeoutError, Exception):
            continue


def wait_for_cccu_listing(page) -> None:
    selectors = [
        'a[href*="/study-here/courses/"]',
        ".course-card",
        "a.sc-eJZSpO",
    ]
    for selector in selectors:
        try:
            page.wait_for_selector(selector, timeout=20000)
            page.wait_for_timeout(1000)
            return
        except PlaywrightTimeoutError:
            continue


def scroll_to_entry_requirements(page) -> None:
    selectors = [
        "#courseEntryRequirements",
        '[id*="courseEntryRequirements" i]',
        'a[href*="#courseEntryRequirements"]',
    ]
    for selector in selectors:
        try:
            target = page.locator(selector).first
            target.wait_for(state="attached", timeout=15000)
            target.scroll_into_view_if_needed(timeout=10000)
            page.wait_for_timeout(1500)
            return
        except (PlaywrightTimeoutError, Exception):
            continue


def wait_for_international_content(page) -> None:
    selectors = [
        'h2:has-text("Choose your country")',
        ".country-picker",
        ".country-selector",
        "text=Choose your country",
    ]
    for selector in selectors:
        try:
            page.wait_for_selector(selector, timeout=15000)
            page.wait_for_timeout(500)
            return
        except PlaywrightTimeoutError:
            continue


def select_international_tab(page) -> bool:
    """Open the International tab on CCCU course entry requirements."""
    scroll_to_entry_requirements(page)

    try:
        open_tab = page.get_by_role("button", name="International", exact=True)
        classes = open_tab.get_attribute("class") or ""
        if "tab-open" in classes and open_tab.is_visible(timeout=2000):
            wait_for_international_content(page)
            return True
    except (PlaywrightTimeoutError, Exception):
        pass

    try:
        button = page.get_by_role("button", name="International", exact=True)
        button.wait_for(state="visible", timeout=10000)
        button.click(timeout=5000)
        page.wait_for_timeout(1500)
        wait_for_international_content(page)
        return page.locator("text=Choose your country").count() > 0
    except (PlaywrightTimeoutError, Exception):
        pass

    for selector in ('button.tab-closed:has-text("International")', 'button:has-text("International")'):
        try:
            button = page.locator(selector).first
            if button.is_visible(timeout=3000):
                button.click(timeout=5000)
                page.wait_for_timeout(1500)
                wait_for_international_content(page)
                return page.locator("text=Choose your country").count() > 0
        except (PlaywrightTimeoutError, Exception):
            continue
    return False


def download_html_with_playwright(
    page,
    url: str,
    *,
    wait_for_results: bool = False,
    click_international: bool = False,
) -> tuple[str, str]:
    last_error: Exception | None = None
    wait_until = "load" if click_international else "domcontentloaded"
    for attempt in range(1, LISTING_DOWNLOAD_RETRIES + 1):
        try:
            page.goto(url, wait_until=wait_until, timeout=60000)
            dismiss_cookie_banner(page)
            if not click_international:
                page.wait_for_load_state("load", timeout=30000)
            page.wait_for_timeout(3000 if click_international else 2000)
            if wait_for_results:
                wait_for_cccu_listing(page)
            if click_international:
                if select_international_tab(page):
                    print("    International tab selected", flush=True)
                else:
                    print("    Warning: International tab not found - saving default view", flush=True)
                # TODO: select Bangladesh in country dropdown before save (deferred)
            title = page.title().strip() or url
            html = page.content()
            if html and html.strip():
                return title, html
            last_error = ValueError("Empty HTML response")
        except Exception as exc:
            last_error = exc
        if attempt < LISTING_DOWNLOAD_RETRIES:
            print(f"    Retry {attempt}/{LISTING_DOWNLOAD_RETRIES - 1} for {url}", flush=True)
            time.sleep(1)
    raise RuntimeError(f"Failed to download HTML after {LISTING_DOWNLOAD_RETRIES} attempts: {url}") from last_error


def extract_urls_from_search_listings(
    university_dir: Path,
    listing_config: dict[str, object],
    progress: dict | None,
    logger: ScrapeLogger | None,
    *,
    append_urls: bool = False,
) -> list[str]:
    seed_urls = listing_config["seeds"]
    search_groups = build_search_groups(seed_urls)
    programme = listing_config["programme"]
    search_path = listing_config["search_path"]
    group_state: dict[str, dict] = {}

    if progress and progress.get("phase") == "extracting_urls":
        saved_seeds = progress.get("listing_seeds", [])
        if saved_seeds and saved_seeds != seed_urls:
            raise ValueError(
                ".env listing URLs changed since the last run. "
                "Use --fresh to restart this programme, or restore the previous .env to resume."
            )
        all_urls = set(progress.get("course_urls", []))
        completed = set(progress.get("listing_completed", []))
        group_state = progress.get("group_state", {})
        page_counter = len(completed)
        print(
            f"  Resuming {programme} ({len(all_urls)} URLs, {page_counter} pages done)",
            flush=True,
        )
    else:
        all_urls: set[str] = set()
        urls_at_start = 0
        if append_urls:
            try:
                existing = read_course_urls_csv(university_dir)
                urls_at_start = len(existing)
                all_urls = set(existing)
                print(f"  Appending to {urls_at_start} existing course URLs", flush=True)
            except FileNotFoundError:
                pass
        completed = set()
        page_counter = 0
        progress = new_progress("extracting_urls", listing_config)
        progress["course_urls"] = sorted(all_urls)
        progress["urls_at_start"] = urls_at_start
        for path_key in search_groups:
            group_state[path_key] = {"page_index": 1, "max_pages": None, "empty_streak": 0}
        save_progress(university_dir, progress)

    print(f"  Programme: {programme}", flush=True)
    print(f"  Search path: {search_path}", flush=True)
    print(f"  Seed URLs: {len(seed_urls)} from {ENV_FILE}", flush=True)

    ordered_paths = sorted(search_groups.keys())

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        for path_key in ordered_paths:
            base_url = search_groups[path_key]
            label = SEARCH_PATH_LABELS.get(path_key, path_key.rsplit("/", 1)[-1])
            state = group_state.setdefault(
                path_key,
                {"page_index": 1, "max_pages": None, "empty_streak": 0},
            )
            page_index = int(state.get("page_index", 1))
            max_pages = state.get("max_pages")
            empty_streak = int(state.get("empty_streak", 0))

            print(f"  Search listing: {label} ({base_url.split('?')[0]})", flush=True)

            while empty_streak < PAGINATION_EMPTY_LIMIT:
                if max_pages is not None and page_index > int(max_pages):
                    print(f"    Reached last page ({max_pages}) for {label}", flush=True)
                    break

                listing_url = set_page_index(base_url, page_index)
                normalized = normalize_url(listing_url, keep_query=True)
                if normalized in completed:
                    page_index += 1
                    continue

                page_counter += 1
                print(f"  Downloading listing page {page_counter}: {listing_url}", flush=True)
                try:
                    _title, html = download_html_with_playwright(
                        page, listing_url, wait_for_results=True
                    )
                except RuntimeError as exc:
                    empty_streak += 1
                    print(
                        f"    No HTML ({empty_streak}/{PAGINATION_EMPTY_LIMIT}): {exc}",
                        flush=True,
                    )
                    if logger:
                        logger.error(f"Listing page failed: {listing_url} — {exc}")
                    page_index += 1
                    continue

                completed.add(normalized)

                start, end, total = get_listing_result_info(html)
                if total is not None and max_pages is None:
                    page_size = (end - start + 1) if start and end else 12
                    max_pages = estimated_total_pages(total, page_size)
                    print(
                        f"    {label}: {total} results, ~{max_pages} pages "
                        f"({page_size} per page)",
                        flush=True,
                    )

                page_urls = extract_course_urls_from_html(html)
                if page_urls:
                    all_urls.update(page_urls)
                    empty_streak = 0
                    print(f"    Found {len(page_urls)} course URLs on page", flush=True)
                    if logger:
                        logger.ok(
                            f"Listing page {page_counter}: {len(page_urls)} URLs "
                            f"from {listing_url} -> {listing_filename}"
                        )
                else:
                    empty_streak += 1
                    print(
                        f"    No course URLs ({empty_streak}/{PAGINATION_EMPTY_LIMIT}): "
                        f"{listing_url}",
                        flush=True,
                    )
                    if logger:
                        logger.error(
                            f"Listing page {page_counter} empty ({empty_streak}/"
                            f"{PAGINATION_EMPTY_LIMIT}): {listing_url}"
                        )

                page_index += 1
                state["page_index"] = page_index
                state["max_pages"] = max_pages
                state["empty_streak"] = empty_streak
                group_state[path_key] = state

                progress["course_urls"] = merge_course_urls(set(), all_urls)
                progress["listing_completed"] = sorted(completed)
                progress["group_state"] = group_state
                progress["pages_scraped"] = len(completed)
                progress["pages_total"] = max_pages
                save_progress(university_dir, progress)
                write_course_urls_csv(university_dir, progress["course_urls"])

        browser.close()

    progress["phase"] = "urls_complete"
    progress["listing_pending"] = []
    progress["group_state"] = group_state
    progress["pages_scraped"] = len(completed)
    progress["course_urls"] = merge_course_urls(set(), all_urls)
    progress["course_urls_count"] = len(progress["course_urls"])
    urls_at_start = int(progress.get("urls_at_start", 0))
    progress["new_urls_this_run"] = len(progress["course_urls"]) - urls_at_start
    save_progress(university_dir, progress)
    sync_output_csvs(university_dir, progress)

    pages_total = progress.get("pages_total")
    pages_scraped = progress.get("pages_scraped", len(completed))
    print(
        f"\nURL extraction complete — {programme}\n"
        f"  Search path: {search_path}\n"
        f"  Pages scraped: {pages_scraped}"
        + (f"/{pages_total}" if pages_total else "")
        + f"\n  Course URLs this run: {progress.get('new_urls_this_run', len(all_urls))}\n"
        f"  Total in course_urls.csv: {len(progress['course_urls'])}\n"
        f"  Phase: urls_complete",
        flush=True,
    )
    return progress["course_urls"]


def build_course_page_index(output_dir: Path, urls: list[str]) -> dict[str, Path]:
    index: dict[str, Path] = {}
    if not output_dir.exists():
        return index
    for html_path in output_dir.glob("*.html"):
        saved = read_saved_url(html_path)
        if saved:
            index[normalize_url(saved)] = html_path
    return index


def save_course_page(
    output_dir: Path,
    title: str,
    html: str,
    url: str,
    page_index: dict[str, Path] | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    html = inject_saved_url_comment(html, url)
    normalized = normalize_url(url)
    if page_index and normalized in page_index:
        output_path = page_index[normalized]
    else:
        output_path = output_dir / f"{sanitize_filename(title)}.html"
        if page_index is not None:
            page_index[normalized] = output_path
    output_path.write_text(html, encoding="utf-8")
    return output_path


def download_course_pages(
    university_dir: Path,
    urls: list[str] | None = None,
    progress: dict | None = None,
    logger: ScrapeLogger | None = None,
    *,
    redownload: bool = False,
) -> dict[str, int]:
    if urls is None:
        urls = read_course_urls_csv(university_dir)

    stats = {"total": len(urls), "downloaded": 0, "failed": 0, "skipped": 0}
    if not urls:
        print("No course URLs to download.")
        sync_output_csvs(university_dir, progress)
        return stats

    output_dir = university_dir / COURSE_PAGES_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    page_index = build_course_page_index(output_dir, urls)

    downloaded = set(progress.get("downloaded_urls", [])) if progress else set()
    if not redownload:
        downloaded |= set(page_index.keys())
    failed = set(progress.get("failed_urls", [])) if progress else set()

    remaining = [url for url in urls if redownload or normalize_url(url) not in downloaded]
    stats["skipped"] = len(urls) - len(remaining)
    stats["downloaded"] = len(downloaded)

    if not remaining:
        print(f"All {len(urls)} course pages already downloaded.")
        if progress:
            progress["phase"] = "complete"
            save_progress(university_dir, progress)
        sync_output_csvs(university_dir, progress)
        stats["failed"] = len(failed)
        return stats

    if progress is None:
        progress = new_progress("downloading_pages")
    else:
        progress["phase"] = "downloading_pages"
    progress["downloaded_urls"] = sorted(downloaded)
    progress["failed_urls"] = sorted(failed)
    save_progress(university_dir, progress)

    print(
        f"Downloading {len(remaining)} course pages to {output_dir} "
        f"({len(downloaded)} already done, {len(urls)} total)"
    )
    print("  Course pages: UK/International tab -> International before save", flush=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        for index, url in enumerate(remaining, start=1):
            print(f"  [{index}/{len(remaining)}] {url}")
            try:
                title, html = download_html_with_playwright(
                    page, url, click_international=True
                )
                saved_path = save_course_page(output_dir, title, html, url, page_index)
                downloaded.add(normalize_url(url))
                failed.discard(normalize_url(url))
                progress["downloaded_urls"] = sorted(downloaded)
                progress["failed_urls"] = sorted(failed)
                save_progress(university_dir, progress)
                sync_output_csvs(university_dir, progress)
                print(f"    Saved: {saved_path.name}")
                if logger:
                    logger.ok(f"Course page [{index}/{len(remaining)}]: {url} -> {saved_path.name}")
            except Exception as exc:
                failed.add(normalize_url(url))
                progress["failed_urls"] = sorted(failed)
                save_progress(university_dir, progress)
                sync_output_csvs(university_dir, progress)
                print(f"    ERROR: {exc}")
                if logger:
                    logger.error(f"Course page [{index}/{len(remaining)}]: {url} — {exc}")
            time.sleep(0.5)

        browser.close()

    progress["phase"] = "complete"
    save_progress(university_dir, progress)
    sync_output_csvs(university_dir, progress)
    stats["downloaded"] = len(downloaded)
    stats["failed"] = len(failed)
    return stats


def scrape(
    university_dir: Path,
    *,
    urls_only: bool = False,
    download_only: bool = False,
    fresh: bool = False,
    append_urls: bool = False,
    redownload_courses: bool = False,
) -> int:
    university_dir = university_dir.resolve()
    logger = ScrapeLogger(university_dir)
    mode = "download-only" if download_only else "urls-only" if urls_only else "full"
    logger.start(mode, fresh=fresh, append_urls=append_urls)
    print(f"University directory: {university_dir}")
    print(f"Listing config: {ENV_FILE} (COURSE_LISTING_1, COURSE_LISTING_2)")

    if fresh:
        clear_progress(university_dir, keep_course_urls=append_urls)
        print("  Cleared scrape progress (starting fresh)")

    read_master_sheet(university_dir)
    listing_config = get_listing_config(university_dir)
    progress = load_progress(university_dir)
    urls: list[str] = []

    try:
        if download_only:
            stats = download_course_pages(
                university_dir,
                progress=progress,
                logger=logger,
                redownload=redownload_courses,
            )
            logger.end(
                "complete" if stats["failed"] == 0 else "partial",
                total=stats["total"],
                downloaded=stats["downloaded"],
                failed=stats["failed"],
                skipped=stats["skipped"],
            )
            return 0

        if progress and progress.get("phase") == "urls_complete" and not fresh:
            if progress.get("listing_seeds") == listing_config["seeds"]:
                urls = progress.get("course_urls") or read_course_urls_csv(university_dir)
                print(
                    f"URL extraction already complete for {listing_config['programme']} "
                    f"({len(urls)} URLs). Use --fresh to re-scrape this programme."
                )
                logger.info(f"URL extraction already complete urls={len(urls)}")
            else:
                print(
                    f".env changed ({listing_config['programme']}). "
                    "Running extraction for new programme..."
                )
                urls = extract_urls_from_search_listings(
                    university_dir,
                    listing_config,
                    None,
                    logger,
                    append_urls=append_urls,
                )
        else:
            urls = extract_urls_from_search_listings(
                university_dir,
                listing_config,
                progress if not fresh else None,
                logger,
                append_urls=append_urls,
            )
            print(f"Found {len(urls)} unique course URLs in course_urls.csv")
            logger.info(f"URL extraction complete urls={len(urls)}")

        if urls_only:
            logger.end("complete", urls=len(urls), phase="urls_only")
            return 0

        stats = download_course_pages(
            university_dir,
            urls,
            progress=load_progress(university_dir),
            logger=logger,
            redownload=redownload_courses,
        )
        logger.end(
            "complete" if stats["failed"] == 0 else "partial",
            urls=len(urls),
            downloaded=stats["downloaded"],
            failed=stats["failed"],
        )
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        logger.error(str(exc))
        logger.end("error", message=str(exc))
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape Canterbury Christ Church University course pages."
    )
    parser.add_argument(
        "university_dir",
        nargs="?",
        default=str(UNIVERSITY_DIR),
        help="University folder (default: this folder)",
    )
    parser.add_argument("--urls-only", action="store_true", help="Extract course URLs only")
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Download course pages from existing course_urls.csv",
    )
    parser.add_argument("--fresh", action="store_true", help="Clear progress and start again")
    parser.add_argument(
        "--append-urls",
        action="store_true",
        help="Keep existing course_urls.csv and add URLs from this programme run",
    )
    parser.add_argument(
        "--redownload-courses",
        action="store_true",
        help="Re-download all course pages (e.g. after International tab support added)",
    )
    args = parser.parse_args()
    return scrape(
        Path(args.university_dir),
        urls_only=args.urls_only,
        download_only=args.download_only,
        fresh=args.fresh,
        append_urls=args.append_urls,
        redownload_courses=args.redownload_courses,
    )


if __name__ == "__main__":
    raise SystemExit(main())
