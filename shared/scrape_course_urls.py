#!/usr/bin/env python3
"""Extract course URLs — Canterbury supports two strategies (set STRATEGY in .env).

This script only extracts course URLs and writes them to course_urls.csv
plus per-study-level CSVs (undergraduate_course_urls.csv, etc.).

This is a class-based refactor of the original procedural script. Behaviour is
kept identical for the URL-extraction phase; the code is organised into small,
single-purpose classes so each concern (env parsing, URL matching, browser
control, progress tracking, extraction strategy) can be read and tested on
its own.

STRATEGY=ALL_COURSE — catalogue HTML or live URL (one or all degree scopes in one run):

  Single catalogue (legacy):
    COURSE_CATALOGUE_URL=https://…
    COURSE_CATALOGUE_HTML=../course_listing/saved.html

  Degree-scoped catalogues (all scopes in one run):
    UNDERGRADUATE_COURSE_CATALOGUE_HTML=…
    POSTGRADUATE_COURSE_CATALOGUE_HTML=…
    POSTGRADUATE_RESEARCH_COURSE_CATALOGUE_HTML=…
    FOUNDATION_COURSE_CATALOGUE_HTML=…
    (optional matching *_COURSE_CATALOGUE_URL= per scope)

STRATEGY=DEGREE_SCOPED_PAGINATED — paginated course search listings:

  All programmes in one run (4 scopes when needed):
    UNDERGRADUATE_COURSE_LISTING_PAGE_1=…
    POSTGRADUATE_COURSE_LISTING_PAGE_1=…
    POSTGRADUATE_RESEARCH_COURSE_LISTING_PAGE_1=…
    FOUNDATION_COURSE_LISTING_PAGE_1=…
    (each scope may also set _PAGE_2, _PAGE_3, …)

  Legacy single-programme keys still work:
    LISTING_PROGRAMME=undergraduate
    COURSE_LISTING_PAGE_1=…  COURSE_LISTING_PAGE_2=…

URL matching (required):
  COURSE_PATH_PATTERNS=   one regex per line (quoted multiline) or ;-separated
  EXCLUDED_COURSE_PATHS=  optional exact paths to skip
  EXCLUDED_PATH_PREFIXES= optional path prefixes to skip
  COURSE_LINK_SELECTOR=   optional CSS selector limiting which <a> tags are scanned

Run from a university code/ folder (uses .env in cwd, or pass --code-dir):

  cd "{University}/code"
  python "../../shared/scrape_course_urls.py" --fresh
  python "../../shared/scrape_course_urls.py" --fresh --presetup
  python "../../shared/scrape_course_urls.py" --fresh --append-urls
  python "../../shared/scrape_course_urls.py" --append-urls --study-level foundation
  python "../../shared/scrape_course_urls.py" --pick-levels
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

_SHARED_DIR = Path(__file__).resolve().parent
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

from uni_paths import resolve_code_dir, resolve_output_dir
from course_type_filter import CourseTypeFilter
from study_level import (
    EXECUTE_LEVEL_ORDER,
    LEVEL_CSV_NAMES,
    PRESETUP_SCRAPE_PROGRESS_JSON,
    PRESETUP_URLS_CSV,
    SCOPE_TO_LEVEL,
    SCRAPE_PRESETUP_PER_LEVEL,
    StudyLevelClassifier,
    UrlLevelMap,
    dedupe_urls_by_latest_intake,
    load_url_levels,
    parse_study_levels,
    presetup_level_counts,
    presetup_should_stop_pagination,
    read_level_csvs,
    save_presetup_scrape_sample,
    sample_urls_per_level,
    scope_to_level,
    unique_urls,
    write_level_csvs,
    write_presetup_urls_csv,
)


def resolve_work_dir(work_dir: Path | None = None) -> Path:
    """University code directory (contains .env). Alias for resolve_code_dir."""
    return resolve_code_dir(work_dir)


def add_code_dir_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--code-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help="University code/ folder with .env (default: current working directory)",
    )


# Back-compat for imports; prefer passing work_dir explicitly to main().
WORK_DIR = resolve_work_dir()
ENV_FILE = ".env"
COURSE_URLS_CSV = "course_urls.csv"
FAILED_URLS_CSV = "failed_urls.csv"
COURSE_PAGE_MAP_CSV = "course_page_map.csv"
COURSE_PAGES_DIR = "course_pages"
PROGRESS_FILE = "scrape_progress.json"
LOG_FILE = "scrape.log"

STRATEGY_ALL_COURSE = "ALL_COURSE"
STRATEGY_DEGREE_SCOPED_PAGINATED = "DEGREE_SCOPED_PAGINATED"
VALID_STRATEGIES = {STRATEGY_ALL_COURSE, STRATEGY_DEGREE_SCOPED_PAGINATED}

DEGREE_SCOPES = (
    "UNDERGRADUATE",
    "POSTGRADUATE",
    "POSTGRADUATE_RESEARCH",
    "FOUNDATION",
)
PAGINATION_PARAM_CANDIDATES = (
    "pageIndex",
    "page",
    "start_rank",
    "skiptoresults",
    "p",
)
SEARCH_PATH_LABELS = {
    "/search/undergraduate-courses": "undergraduate",
    "/search/postgraduate-taught-courses": "postgraduate",
    "/search/foundation-year": "foundation",
}
PAGINATION_EMPTY_LIMIT = 2
LISTING_DOWNLOAD_RETRIES = 2
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

SAVED_URL_COMMENT_RE = re.compile(
    r"<!-- saved from url=\(\d*\)(https?://[^\s>]+)", re.I
)
SAVED_URL_COMMENT_FALLBACK_RE = re.compile(
    r"<!-- saved from url=\(([^)]+)\)", re.I
)
CANONICAL_URL_RE = re.compile(
    r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']',
    re.I,
)
BASE_HREF_RE = re.compile(r'<base[^>]+href=["\']([^"\']+)["\']', re.I)

# Used only when .env omits these optional keys
DEFAULT_EXCLUDED_COURSE_PATHS = (
    "/courses",
    "/courses/a-z",
    "/courses/a-to-z-listing",
    "/courses/search",
    "/courses/choices",
    "/courses/prospectus",
    "/courses/short-courses",
    "/courses/saved",
)
DEFAULT_EXCLUDED_PATH_PREFIXES = (
    "/bookmarked-courses",
    "/clearing/",
    "/international/",
    "/current-students/",
    "/alumni",
    "/information/",
    "/about/",
    "/research/",
    "/news/",
    "/events/",
)


# ============================================================================
# Small, generic helpers grouped as static methods (no state of their own)
# ============================================================================

class Utils:
    """Tiny stateless helpers used all over the script."""

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    @staticmethod
    def log_timestamp() -> str:
        return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")

    @staticmethod
    def is_empty(value: str | None) -> bool:
        return value is None or not str(value).strip()

    @staticmethod
    def sanitize_filename(name: str, max_len: int = 180) -> str:
        cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" ._")
        return (cleaned or "page")[:max_len]


class ScrapeLogger:
    """Appends timestamped run events to scrape.log."""

    def __init__(self, output_dir: Path):
        self.log_path = output_dir / LOG_FILE
        self.started_at = time.time()

    def write(self, level: str, message: str) -> None:
        line = f"{Utils.log_timestamp()} [{level}] {message}\n"
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


# ============================================================================
# .env loading
# ============================================================================

class EnvFile:
    """Loads KEY=VALUE pairs from a .env file (supports quoted multiline values)
    and gives typed access helpers (raw string, list, membership check)."""

    def __init__(self, path: Path):
        self.path = path
        self.values: dict[str, str] = self._load()

    def _load(self) -> dict[str, str]:
        values: dict[str, str] = {}
        if not self.path.exists():
            return values
        lines = self.path.read_text(encoding="utf-8").splitlines()
        index = 0
        while index < len(lines):
            raw = lines[index]
            stripped = raw.strip()
            index += 1
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
                # Single-line quoted value: "..." or '...'
                value = value[1:-1]
            elif value.startswith('"') or value.startswith("'"):
                # Multiline quoted value: keep consuming lines until the closing quote
                quote = value[0]
                chunks = [value[1:]]
                while index < len(lines):
                    next_line = lines[index]
                    index += 1
                    if next_line.rstrip().endswith(quote):
                        chunks.append(next_line.rstrip()[:-1])
                        break
                    chunks.append(next_line)
                value = "\n".join(chunks)
            values[key] = value
        return values

    def get(self, key: str, default: str = "") -> str:
        return self.values.get(key, default)

    def get_list(self, key: str) -> list[str]:
        """Split a value on newlines and/or semicolons into a clean list of items."""
        value = self.values.get(key)
        if Utils.is_empty(value):
            return []
        items: list[str] = []
        for part in re.split(r"[\n;]+", str(value)):
            item = part.strip().strip('"').strip("'")
            if not item or item.startswith("#"):
                continue
            items.append(item)
        return items

    def __contains__(self, key: str) -> bool:
        return key in self.values


# ============================================================================
# URL normalisation / pagination helpers
# ============================================================================

class UrlNormalizer:
    """Static helpers for cleaning URLs and reading/writing pagination params."""

    @staticmethod
    def resolve_redirect_target(href: str, base: str | None = None) -> str:
        """Unwrap search redirect links (e.g. Funnelback ?url=https://…)."""
        url = href.strip()
        if base:
            url = urljoin(base, url)
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        for key in ("url", "redirect", "u"):
            values = params.get(key) or []
            if not values:
                continue
            target = unquote(values[0]).strip()
            if target.startswith(("http://", "https://")):
                return target
        return url

    @staticmethod
    def normalize(url: str, base: str | None = None, keep_query: bool = False) -> str:
        url = url.strip()
        if base:
            url = urljoin(base, url)
        parsed = urlparse(url)
        if keep_query:
            normalized = parsed._replace(fragment="").geturl()
        else:
            normalized = parsed._replace(fragment="", query="").geturl()
        return normalized.rstrip("/")

    @staticmethod
    def listing_path_key(url: str) -> str:
        return urlparse(url).path.rstrip("/").lower()

    @staticmethod
    def infer_listing_programme(url: str) -> str:
        path_key = UrlNormalizer.listing_path_key(url)
        if path_key in SEARCH_PATH_LABELS:
            return SEARCH_PATH_LABELS[path_key]
        slug = path_key.rsplit("/", 1)[-1]
        return slug.replace("-", " ")

    @staticmethod
    def _query_params(url: str) -> dict[str, list[str]]:
        return parse_qs(urlparse(url).query, keep_blank_values=True)

    @staticmethod
    def detect_pagination_param(url: str) -> str:
        params = UrlNormalizer._query_params(url)
        lower_keys = {key.lower(): key for key in params}
        for candidate in PAGINATION_PARAM_CANDIDATES:
            if candidate.lower() in lower_keys:
                return lower_keys[candidate.lower()]
        return "pageIndex"

    @staticmethod
    def get_page_number(url: str, param: str | None = None) -> int:
        param = param or UrlNormalizer.detect_pagination_param(url)
        params = UrlNormalizer._query_params(url)
        values = None
        for key, val in params.items():
            if key.lower() == param.lower():
                values = val
                break
        if not values:
            values = ["1"]
        try:
            return max(1, int(values[0]))
        except ValueError:
            return 1

    @staticmethod
    def set_page_number(url: str, page_number: int, param: str | None = None) -> str:
        param = param or UrlNormalizer.detect_pagination_param(url)
        parsed = urlparse(url)
        params = UrlNormalizer._query_params(url)
        actual_key = param
        for key in params:
            if key.lower() == param.lower():
                actual_key = key
                break
        params[actual_key] = [str(page_number)]
        return urlunparse(parsed._replace(query=urlencode(params, doseq=True)))

    @staticmethod
    def infer_page_step(seed_urls: list[str], param: str | None = None) -> int:
        if not seed_urls:
            return 1
        param = param or UrlNormalizer.detect_pagination_param(seed_urls[0])
        pages = sorted(UrlNormalizer.get_page_number(url, param) for url in seed_urls)
        if len(pages) >= 2:
            return max(1, pages[1] - pages[0])
        return 1

    @staticmethod
    def group_state_key(scope: str, path_key: str) -> str:
        return f"{scope}::{path_key}"

    @staticmethod
    def listing_family_key(url: str) -> str:
        """Listing identity with the page number normalized, so page 1 and page 9 match."""
        param = UrlNormalizer.detect_pagination_param(url)
        return UrlNormalizer.normalize(
            UrlNormalizer.set_page_number(url, 1, param),
            keep_query=True,
        )


# ============================================================================
# Catalogue-URL inference from a saved HTML file
# ============================================================================

class HtmlUrlInference:
    """Guesses the page's original URL from clues left inside saved HTML
    (browser "saved from url" comment, <base href>, canonical link, og:url)."""

    @staticmethod
    def infer(html: str, html_path: Path | None = None) -> str | None:
        head = html[:8000]

        match = SAVED_URL_COMMENT_RE.search(head)
        if match:
            return match.group(1).strip().rstrip("/")

        match = SAVED_URL_COMMENT_FALLBACK_RE.search(head)
        if match:
            raw = match.group(1).strip()
            url_match = re.search(r"(https?://\S+)", raw)
            if url_match:
                return url_match.group(1).strip().rstrip("/")

        match = BASE_HREF_RE.search(head)
        if match:
            href = match.group(1).strip()
            parsed = urlparse(href)
            if parsed.scheme and parsed.netloc:
                return href.rstrip("/")

        match = CANONICAL_URL_RE.search(head)
        if match:
            href = match.group(1).strip()
            parsed = urlparse(href)
            if parsed.scheme and parsed.netloc:
                return href.rstrip("/")

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all("meta", attrs={"property": "og:url"}):
            content = (tag.get("content") or "").strip()
            parsed = urlparse(content)
            if parsed.scheme and parsed.netloc:
                return content.rstrip("/")

        # Last resort: nothing reliable found — caller raises a clear error.
        _ = html_path
        return None


# ============================================================================
# URL matching rules (which links on a page actually count as "a course")
# ============================================================================

@dataclass
class MatchingRules:
    """The rules that decide whether a discovered link is a genuine course page."""

    path_patterns: list[re.Pattern[str]]
    path_pattern_sources: list[str]
    excluded_paths: set[str]
    excluded_prefixes: tuple[str, ...]
    link_selector: str
    base_url: str


class MatchingRulesLoader:
    """Builds a MatchingRules object from the .env file."""

    @staticmethod
    def _compile_path_patterns(raw_patterns: list[str], env_path: Path) -> list[re.Pattern[str]]:
        compiled: list[re.Pattern[str]] = []
        for pattern in raw_patterns:
            try:
                compiled.append(re.compile(pattern, re.I))
            except re.error as exc:
                raise ValueError(
                    f"{env_path}: invalid COURSE_PATH_PATTERNS regex {pattern!r}: {exc}"
                ) from exc
        return compiled

    @staticmethod
    def load(env: EnvFile, env_path: Path) -> MatchingRules:
        path_patterns = env.get_list("COURSE_PATH_PATTERNS")
        if not path_patterns:
            raise ValueError(
                f"{env_path}: set COURSE_PATH_PATTERNS= with one or more path regexes "
                "(quoted multiline, one per line, or ;-separated). "
                "Example: COURSE_PATH_PATTERNS=\"^/study-here/courses/[^/]+$\""
            )
        compiled_patterns = MatchingRulesLoader._compile_path_patterns(path_patterns, env_path)

        if "EXCLUDED_COURSE_PATHS" in env:
            excluded_paths = {
                item.rstrip("/").lower() if item != "/" else item
                for item in env.get_list("EXCLUDED_COURSE_PATHS")
            }
        else:
            excluded_paths = {p.lower() for p in DEFAULT_EXCLUDED_COURSE_PATHS}

        if "EXCLUDED_PATH_PREFIXES" in env:
            excluded_prefixes = tuple(item.lower() for item in env.get_list("EXCLUDED_PATH_PREFIXES"))
        else:
            excluded_prefixes = tuple(p.lower() for p in DEFAULT_EXCLUDED_PATH_PREFIXES)

        link_selector = env.get("COURSE_LINK_SELECTOR", "").strip()
        university_base = env.get("UNIVERSITY_BASE_URL", "").strip()
        base_url = ""
        if university_base:
            base_parsed = urlparse(university_base)
            if base_parsed.scheme and base_parsed.netloc:
                base_url = f"{base_parsed.scheme}://{base_parsed.netloc}"

        return MatchingRules(
            path_patterns=compiled_patterns,
            path_pattern_sources=path_patterns,
            excluded_paths=excluded_paths,
            excluded_prefixes=excluded_prefixes,
            link_selector=link_selector,
            base_url=base_url,
        )


class CourseUrlMatcher:
    """Given a domain + MatchingRules, decides which <a> links on a page are
    real course URLs, and extracts them from HTML."""

    def __init__(self, domain: str, rules: MatchingRules):
        self.domain = domain
        self.rules = rules

    def is_valid(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.netloc.lower() != self.domain:
            return False
        path_lower = parsed.path.lower().rstrip("/") or "/"
        if path_lower in {"/", "/courses", "/courses-atoz", "/study/courses"}:
            return False
        if any(path_lower.startswith(prefix) for prefix in self.rules.excluded_prefixes):
            return False
        if path_lower in self.rules.excluded_paths:
            return False
        return any(pattern.search(parsed.path) for pattern in self.rules.path_patterns)

    def extract_from_html(self, html: str, base_url: str) -> set[str]:
        soup = BeautifulSoup(html, "html.parser")
        urls: set[str] = set()
        anchors = (
            soup.select(self.rules.link_selector)
            if self.rules.link_selector
            else soup.find_all("a", href=True)
        )
        for anchor in anchors:
            href = anchor.get("href") if hasattr(anchor, "get") else None
            if not href:
                continue
            resolved = UrlNormalizer.resolve_redirect_target(href, base_url)
            normalized = UrlNormalizer.normalize(resolved, base_url)
            if self.is_valid(normalized):
                urls.add(normalized)
        return urls

    @staticmethod
    def discover_letter_urls(html: str, base_url: str, catalogue_url: str) -> list[str]:
        """Optional A–Z letter pages linked from the catalogue (same domain)."""
        soup = BeautifulSoup(html, "html.parser")
        letter_urls: set[str] = {UrlNormalizer.normalize(catalogue_url, keep_query=True)}
        for anchor in soup.find_all("a", href=True):
            href = urljoin(base_url, anchor["href"].strip())
            parsed = urlparse(href)
            params = parse_qs(parsed.query)
            path_lower = parsed.path.lower()
            if "letter" not in params:
                continue
            if "a-to-z" in path_lower or "atoz" in path_lower or "a-z" in path_lower:
                letter_urls.add(UrlNormalizer.normalize(href, keep_query=True))
        return sorted(letter_urls)


# ============================================================================
# Catalogue source (STRATEGY=ALL_COURSE) config
# ============================================================================

@dataclass
class CatalogueSource:
    """One catalogue page to scrape — either a saved HTML file or a live URL."""

    scope: str
    catalogue_url: str
    catalogue_html: str  # "" if this source is a live URL, not a saved file
    domain: str
    source: str  # "html" or "url"


class CatalogueSourceResolver:
    """Resolves .env keys into CatalogueSource objects for STRATEGY=ALL_COURSE."""

    @staticmethod
    def _resolve_html_path(work_dir: Path, catalogue_html: str) -> Path:
        from portable_paths import resolve_university_html

        return resolve_university_html(work_dir, catalogue_html)

    @staticmethod
    def resolve(
        work_dir: Path,
        env_path: Path,
        catalogue_url: str,
        catalogue_html: str,
        *,
        scope_label: str = "",
    ) -> CatalogueSource | None:
        html_path = ""
        if catalogue_html:
            resolved = CatalogueSourceResolver._resolve_html_path(work_dir, catalogue_html)
            html_path = str(resolved)
            if Utils.is_empty(catalogue_url):
                html_text = resolved.read_text(encoding="utf-8", errors="replace")
                inferred = HtmlUrlInference.infer(html_text, resolved)
                if not inferred:
                    prefix = f"{scope_label} " if scope_label else ""
                    raise ValueError(
                        f"{env_path}: {prefix}COURSE_CATALOGUE_HTML is set but no catalogue URL "
                        "could be inferred. Add matching *_COURSE_CATALOGUE_URL=, or save the page "
                        "with a <!-- saved from url=(…)https://… --> comment / <base href>."
                    )
                catalogue_url = inferred
                label = f"{scope_label} " if scope_label else ""
                print(f"Inferred {label}COURSE_CATALOGUE_URL from HTML: {catalogue_url}")

        if Utils.is_empty(catalogue_url) and Utils.is_empty(catalogue_html):
            return None

        if Utils.is_empty(catalogue_url):
            raise ValueError(
                f"{env_path}: set {scope_label + '_' if scope_label else ''}COURSE_CATALOGUE_URL= "
                "when only HTML path is unavailable for inference."
            )

        parsed = urlparse(catalogue_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"COURSE_CATALOGUE_URL is not a valid URL: {catalogue_url}")

        return CatalogueSource(
            scope=scope_label,
            catalogue_url=catalogue_url.rstrip("/"),
            catalogue_html=html_path,
            domain=parsed.netloc.lower(),
            source="html" if html_path else "url",
        )

    @staticmethod
    def collect_degree_scopes(work_dir: Path, env: EnvFile, env_path: Path) -> list[CatalogueSource]:
        scopes: list[CatalogueSource] = []
        for scope in DEGREE_SCOPES:
            url = env.get(f"{scope}_COURSE_CATALOGUE_URL", "").strip()
            html = env.get(f"{scope}_COURSE_CATALOGUE_HTML", "").strip()
            if Utils.is_empty(url) and Utils.is_empty(html):
                continue
            source = CatalogueSourceResolver.resolve(work_dir, env_path, url, html, scope_label=scope)
            if source is not None:
                scopes.append(source)
        return scopes


# ============================================================================
# Listing config (STRATEGY=DEGREE_SCOPED_PAGINATED) config
# ============================================================================

@dataclass
class ListingConfig:
    """One paginated search-results listing (e.g. undergraduate courses)."""

    scope: str
    programme: str
    seeds: list[str]
    search_path: str


class ListingConfigLoader:
    """Resolves .env keys into ListingConfig objects for STRATEGY=DEGREE_SCOPED_PAGINATED."""

    @staticmethod
    def collect_seeds(env: EnvFile, scope: str = "") -> list[str]:
        prefix = f"{scope}_" if scope else ""
        seeds: list[str] = []
        seen: set[str] = set()
        index = 1
        while True:
            key = f"{prefix}COURSE_LISTING_PAGE_{index}"
            value = env.get(key, "").strip()
            if Utils.is_empty(value):
                break
            url = UrlNormalizer.normalize(value, keep_query=True)
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f"{key} must be a valid listing URL: {value}")
            if url not in seen:
                seen.add(url)
                seeds.append(url)
            index += 1
        return seeds

    @staticmethod
    def collect_degree_listings(env: EnvFile, env_path: Path) -> list[ListingConfig]:
        configs: list[ListingConfig] = []
        for scope in DEGREE_SCOPES:
            seeds = ListingConfigLoader.collect_seeds(env, scope)
            if not seeds:
                continue
            search_paths = sorted({UrlNormalizer.listing_path_key(url) for url in seeds})
            if len(search_paths) > 1:
                raise ValueError(
                    f"{env_path}: {scope}_COURSE_LISTING_PAGE_* URLs must share one search path "
                    f"(found: {', '.join(search_paths)})"
                )
            configs.append(
                ListingConfig(scope=scope, programme=scope, seeds=seeds, search_path=search_paths[0])
            )
        return configs

    @staticmethod
    def scopes_for_levels(study_levels: list[str]) -> set[str]:
        wanted = set()
        for level in study_levels:
            for scope, mapped in SCOPE_TO_LEVEL.items():
                if mapped == level:
                    wanted.add(scope)
            via_scope = (level or "").strip().replace("-", "_").replace(" ", "_").upper()
            if via_scope in DEGREE_SCOPES:
                wanted.add(via_scope)
        return wanted

    @staticmethod
    def fingerprint(listing_configs: list[ListingConfig]) -> list[dict]:
        return [
            {"scope": item.scope, "seeds": item.seeds, "search_path": item.search_path}
            for item in listing_configs
        ]


# ============================================================================
# Overall run configuration
# ============================================================================

@dataclass
class ScraperConfig:
    """Everything needed to run one of the two extraction strategies."""

    strategy: str
    env_path: str
    matching: MatchingRules
    domain: str = ""
    degree_scopes: list[CatalogueSource] = field(default_factory=list)
    degree_listings: list[ListingConfig] = field(default_factory=list)
    single_catalogue: CatalogueSource | None = None
    level_classifier: StudyLevelClassifier = field(default_factory=StudyLevelClassifier)

    # Convenience passthroughs so extraction code can read config.path_patterns etc.
    @property
    def path_patterns(self) -> list[re.Pattern[str]]:
        return self.matching.path_patterns

    @property
    def path_pattern_sources(self) -> list[str]:
        return self.matching.path_pattern_sources

    @property
    def excluded_paths(self) -> set[str]:
        return self.matching.excluded_paths

    @property
    def excluded_prefixes(self) -> tuple[str, ...]:
        return self.matching.excluded_prefixes

    @property
    def link_selector(self) -> str:
        return self.matching.link_selector

    @property
    def base_url(self) -> str:
        return self.matching.base_url

    @base_url.setter
    def base_url(self, value: str) -> None:
        self.matching.base_url = value


class ConfigLoader:
    """Builds a ScraperConfig by reading and validating the .env file."""

    @staticmethod
    def load(work_dir: Path) -> ScraperConfig:
        env_path = work_dir / ENV_FILE
        env = EnvFile(env_path)

        strategy = env.get("STRATEGY", "").strip()
        if strategy not in VALID_STRATEGIES:
            raise ValueError(
                f"{env_path}: STRATEGY must be one of {sorted(VALID_STRATEGIES)!r} "
                f"(got {strategy!r})."
            )

        matching = MatchingRulesLoader.load(env, env_path)
        config = ScraperConfig(
            strategy=strategy,
            env_path=str(env_path),
            matching=matching,
            level_classifier=StudyLevelClassifier.from_env_file(env, env_path),
        )

        if strategy == STRATEGY_ALL_COURSE:
            return ConfigLoader._load_all_course(work_dir, env, env_path, config)
        return ConfigLoader._load_paginated(env, env_path, config)

    @staticmethod
    def _load_all_course(work_dir: Path, env: EnvFile, env_path: Path, config: ScraperConfig) -> ScraperConfig:
        degree_scopes = CatalogueSourceResolver.collect_degree_scopes(work_dir, env, env_path)
        if degree_scopes:
            config.degree_scopes = degree_scopes
            if not config.base_url:
                config.base_url = f"https://{degree_scopes[0].domain}"
            return config

        catalogue_url = env.get("COURSE_CATALOGUE_URL", "").strip()
        catalogue_html = env.get("COURSE_CATALOGUE_HTML", "").strip()
        if Utils.is_empty(catalogue_url) and Utils.is_empty(catalogue_html):
            raise ValueError(
                f"{env_path}: set COURSE_CATALOGUE_URL= / COURSE_CATALOGUE_HTML= "
                "or degree-scoped UNDERGRADUATE_COURSE_CATALOGUE_HTML= keys."
            )
        source = CatalogueSourceResolver.resolve(work_dir, env_path, catalogue_url, catalogue_html)
        assert source is not None
        if not config.base_url:
            config.base_url = f"https://{source.domain}"
        config.single_catalogue = source
        config.domain = source.domain
        return config

    @staticmethod
    def _load_paginated(env: EnvFile, env_path: Path, config: ScraperConfig) -> ScraperConfig:
        degree_listings = ListingConfigLoader.collect_degree_listings(env, env_path)
        if not degree_listings:
            legacy_scope = env.get("LISTING_PROGRAMME", "").strip()
            legacy_seeds = ListingConfigLoader.collect_seeds(env, "")
            if not legacy_seeds:
                raise ValueError(
                    f"{env_path}: set UNDERGRADUATE_COURSE_LISTING_PAGE_1= (etc.) for one or more of "
                    f"{', '.join(DEGREE_SCOPES)}, or legacy COURSE_LISTING_PAGE_1=."
                )
            search_paths = sorted({UrlNormalizer.listing_path_key(url) for url in legacy_seeds})
            if len(search_paths) > 1:
                raise ValueError(
                    "COURSE_LISTING_PAGE_* URLs must use the same search path "
                    f"(found: {', '.join(search_paths)})"
                )
            programme = legacy_scope or UrlNormalizer.infer_listing_programme(legacy_seeds[0])
            degree_listings = [
                ListingConfig(scope=programme, programme=programme, seeds=legacy_seeds, search_path=search_paths[0])
            ]

        if not config.base_url:
            first_seed = degree_listings[0].seeds[0]
            parsed = urlparse(first_seed)
            config.base_url = f"{parsed.scheme}://{parsed.netloc}"
        config.degree_listings = degree_listings
        config.domain = urlparse(config.base_url).netloc.lower()
        return config


# ============================================================================
# Progress / artifact persistence
# ============================================================================

class ProgressStore:
    """Reads/writes scrape progress JSON so a run can resume after interruption."""

    def __init__(self, output_dir: Path, filename: str = PROGRESS_FILE):
        self.path = output_dir / filename

    def load(self) -> dict | None:
        if not self.path.exists():
            return None
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def save(self, progress: dict) -> None:
        progress["updated_at"] = Utils.utc_now()
        self.path.write_text(json.dumps(progress, indent=2), encoding="utf-8")

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()

    @staticmethod
    def new(phase: str = "extracting_urls", strategy: str = STRATEGY_ALL_COURSE) -> dict:
        return {
            "approach": strategy,
            "phase": phase,
            "course_urls": [],
            "listing_completed": [],
            "group_state": {},
            "listing_configs": [],
            "url_levels": {},
            "started_at": Utils.utc_now(),
            "updated_at": Utils.utc_now(),
        }


class ArtifactStore:
    """Reads/writes the CSV output files (course_urls.csv, failed_urls.csv, page map)."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def write_course_urls(self, urls: list[str]) -> None:
        path = self.output_dir / COURSE_URLS_CSV
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, quoting=csv.QUOTE_ALL)
            writer.writerow(["course_url"])
            for url in urls:
                writer.writerow([url])

    def read_course_urls(self) -> list[str]:
        path = self.output_dir / COURSE_URLS_CSV
        if not path.exists():
            return []
        with path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        urls: list[str] = []
        for row in rows:
            url = (row.get("course_url") or row.get("url") or "").strip()
            if not url:
                for value in row.values():
                    candidate = (value or "").strip()
                    if candidate.startswith("http"):
                        url = candidate
                        break
            if url:
                urls.append(url)
        return urls

    def persist_urls(
        self,
        urls: list[str],
        progress: dict,
        progress_store: ProgressStore,
        url_levels: UrlLevelMap | None = None,
    ) -> None:
        progress["course_urls"] = sorted(set(urls))
        if url_levels is not None:
            progress["url_levels"] = url_levels.to_progress()
            write_level_csvs(self.output_dir, url_levels)
        self.write_course_urls(progress["course_urls"])
        progress_store.save(progress)

    def write_failed(self, failed: list[str]) -> None:
        path = self.output_dir / FAILED_URLS_CSV
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["course_url"])
            for url in failed:
                writer.writerow([url])

    def write_page_map(self, rows: list[list[str]]) -> None:
        path = self.output_dir / COURSE_PAGE_MAP_CSV
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["course_url", "html_path"])
            writer.writerows(rows)


# ============================================================================
# Browser control (Playwright)
# ============================================================================

class BrowserSession:
    """Thin wrapper around a Chromium page, used as a context manager."""

    def __init__(
        self,
        *,
        download_prep: Any | None = None,
        headless: bool = True,
        goto_timeout_ms: int = 60000,
    ):
        self._playwright = None
        self._browser = None
        self.page = None
        self.download_prep = download_prep
        self.headless = headless
        self.goto_timeout_ms = goto_timeout_ms

    def __enter__(self) -> "BrowserSession":
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        context = self._browser.new_context(user_agent=DEFAULT_USER_AGENT)
        self.page = context.new_page()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    @staticmethod
    def dismiss_cookies(page) -> None:
        selectors = [
            "#ccc-notify-accept",
            "button.agree-button.eu-cookie-compliance-default-button",
            "button:has-text('Accept all categories')",
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
            except Exception:
                continue

    @staticmethod
    def wait_for_listing(page) -> None:
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

    def download_html(self, url: str, *, wait_for_results: bool = False) -> tuple[str, str]:
        """Navigate to url and return (page_title, html). Retries transient failures."""
        assert self.page is not None
        use_prep = self.download_prep is not None
        last_error: Exception | None = None
        for attempt in range(1, LISTING_DOWNLOAD_RETRIES + 1):
            try:
                self.page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.goto_timeout_ms,
                )
                self.dismiss_cookies(self.page)
                try:
                    self.page.wait_for_load_state("networkidle", timeout=15000)
                except PlaywrightTimeoutError:
                    self.page.wait_for_load_state("load", timeout=15000)
                if wait_for_results:
                    self.wait_for_listing(self.page)
                elif use_prep:
                    try:
                        self.page.wait_for_selector(
                            "#entryRequirements, #country-requirement",
                            timeout=20000,
                        )
                    except PlaywrightTimeoutError:
                        pass
                    self.page.wait_for_timeout(1500)
                    self.download_prep.prepare(self.page)
                else:
                    self.page.wait_for_timeout(800)
                html = self.page.content()
                if not html or len(html) < 200:
                    raise RuntimeError("Empty or tiny HTML response")
                title = self.page.title() or "catalogue"
                return title, html
            except Exception as exc:
                last_error = exc
                print(f"    Retry {attempt}/{LISTING_DOWNLOAD_RETRIES}: {exc}")
                time.sleep(min(2 * attempt, 8))
        raise RuntimeError(f"Failed to download {url}: {last_error}")


# ============================================================================
# Paginated search-listing helpers
# ============================================================================

class ListingResultParser:
    """Reads the 'Displaying X-Y of Z results' text used to estimate page count."""

    _RESULT_INFO_RE = re.compile(
        r"Displaying\s+(\d+)\s*-\s*(\d+)\s+of\s+(\d+)\s+results", re.I
    )

    @staticmethod
    def get_result_info(html: str) -> tuple[int | None, int | None, int | None]:
        match = ListingResultParser._RESULT_INFO_RE.search(html)
        if not match:
            return None, None, None
        return int(match.group(1)), int(match.group(2)), int(match.group(3))

    @staticmethod
    def estimated_total_pages(total_results: int, page_size: int) -> int:
        if total_results <= 0 or page_size <= 0:
            return 0
        return (total_results + page_size - 1) // page_size


class SearchGroupBuilder:
    """Groups a list of seed listing URLs by their search path, keeping the
    earliest page of each group as the representative starting URL."""

    @staticmethod
    def build(seed_urls: list[str]) -> dict[str, str]:
        groups: dict[str, str] = {}
        for url in seed_urls:
            key = UrlNormalizer.listing_path_key(url)
            param = UrlNormalizer.detect_pagination_param(url)
            page_num = UrlNormalizer.get_page_number(url, param)
            if key not in groups:
                groups[key] = url
                continue
            existing_param = UrlNormalizer.detect_pagination_param(groups[key])
            if UrlNormalizer.get_page_number(groups[key], existing_param) > page_num:
                groups[key] = url

        normalized: dict[str, str] = {}
        for key, url in groups.items():
            matching = [item for item in seed_urls if UrlNormalizer.listing_path_key(item) == key]
            param = UrlNormalizer.detect_pagination_param(url)
            start_page = min(
                UrlNormalizer.get_page_number(item, UrlNormalizer.detect_pagination_param(item))
                for item in matching
            )
            normalized[key] = UrlNormalizer.set_page_number(url, start_page, param)
        return normalized


# ============================================================================
# STRATEGY=ALL_COURSE extraction
# ============================================================================

class CatalogueUrlExtractor:
    """Extracts course URLs from one catalogue source (STRATEGY=ALL_COURSE),
    including any linked A–Z letter pages."""

    def __init__(self, work_dir: Path, config: ScraperConfig, logger: ScrapeLogger):
        self.work_dir = work_dir
        self.config = config
        self.logger = logger

    def extract(
        self,
        source: CatalogueSource,
        *,
        all_urls: set[str],
        completed: set[str],
        browser: BrowserSession | None,
        url_levels: UrlLevelMap,
    ) -> None:
        domain = source.domain
        base_url = self.config.base_url or f"https://{domain}"
        catalogue_url = source.catalogue_url
        scope = source.scope
        scope_prefix = f"[{scope}] " if scope else ""
        matcher = CourseUrlMatcher(domain, self.config.matching)

        # Step 1: get the catalogue page HTML, either from disk or by downloading it.
        if source.catalogue_html:
            html_path = Path(source.catalogue_html)
            print(f"{scope_prefix}COURSE_CATALOGUE_HTML={html_path}")
            html = html_path.read_text(encoding="utf-8", errors="replace")
        else:
            print(f"{scope_prefix}Downloading catalogue page with Playwright…")
            if browser is None:
                raise RuntimeError("Browser session required for live catalogue download")
            _title, html = browser.download_html(catalogue_url)

        # Step 2: pull every course link off the catalogue page.
        page_urls = matcher.extract_from_html(html, base_url)
        before = len(all_urls)
        all_urls.update(page_urls)
        url_levels.tag_urls(
            page_urls,
            scope=scope,
            classifier=self.config.level_classifier,
            source_scope=scope or "ALL_COURSE",
        )
        print(
            f"{scope_prefix}  Extracted {len(page_urls)} course URLs from catalogue "
            f"(+{len(all_urls) - before} new, total {len(all_urls)})"
        )
        self.logger.info(f"{scope_prefix}Catalogue URLs={len(page_urls)} total={len(all_urls)}")

        # Step 3: some catalogues also link out to separate A-Z letter pages — follow those too.
        self._extract_letter_pages(
            matcher,
            html,
            base_url,
            catalogue_url,
            scope,
            scope_prefix,
            all_urls,
            completed,
            browser,
            url_levels,
        )

    def _extract_letter_pages(
        self,
        matcher: CourseUrlMatcher,
        html: str,
        base_url: str,
        catalogue_url: str,
        scope: str,
        scope_prefix: str,
        all_urls: set[str],
        completed: set[str],
        browser: BrowserSession | None,
        url_levels: UrlLevelMap,
    ) -> None:
        letter_urls = matcher.discover_letter_urls(html, base_url, catalogue_url)
        pending_letters = [
            url
            for url in letter_urls
            if UrlNormalizer.normalize(url, keep_query=True)
            != UrlNormalizer.normalize(catalogue_url, keep_query=True)
        ]
        if not pending_letters:
            return

        print(f"{scope_prefix}  Found {len(pending_letters)} extra A–Z letter pages")
        letter_browser = browser
        close_browser = False
        if letter_browser is None:
            letter_browser = BrowserSession().__enter__()
            close_browser = True
        try:
            for index, letter_url in enumerate(pending_letters, start=1):
                print(f"{scope_prefix}  Letter page {index}/{len(pending_letters)}: {letter_url}")
                _title, letter_html = letter_browser.download_html(letter_url)
                found = matcher.extract_from_html(letter_html, base_url)
                all_urls.update(found)
                url_levels.tag_urls(
                    found,
                    scope=scope,
                    classifier=self.config.level_classifier,
                    source_scope=scope or "ALL_COURSE",
                )
                completed.add(UrlNormalizer.normalize(letter_url, keep_query=True))
                print(f"    +{len(found)} URLs")
        finally:
            if close_browser:
                letter_browser.__exit__(None, None, None)


# ============================================================================
# STRATEGY=DEGREE_SCOPED_PAGINATED extraction
# ============================================================================

class PaginatedListingExtractor:
    """Walks through paginated search-results listings for one degree scope,
    extracting course URLs from each page until results run dry."""

    def __init__(
        self,
        work_dir: Path,
        config: ScraperConfig,
        browser: BrowserSession,
        progress: dict,
        progress_store: ProgressStore,
        artifacts: ArtifactStore,
        logger: ScrapeLogger,
        *,
        presetup: bool = False,
        presetup_per_level: int = SCRAPE_PRESETUP_PER_LEVEL,
        presetup_levels: list[str] | None = None,
    ):
        self.work_dir = work_dir
        self.config = config
        self.browser = browser
        self.progress = progress
        self.progress_store = progress_store
        self.artifacts = artifacts
        self.logger = logger
        self.presetup = presetup
        self.presetup_per_level = presetup_per_level
        self.presetup_levels = presetup_levels

    def extract_group(
        self,
        listing_config: ListingConfig,
        *,
        all_urls: set[str],
        completed: set[str],
        group_state: dict[str, dict],
        page_counter: int,
        url_levels: UrlLevelMap,
    ) -> int:
        seed_urls = listing_config.seeds
        search_groups = SearchGroupBuilder.build(seed_urls)
        programme = listing_config.programme
        scope = listing_config.scope or programme
        matcher = CourseUrlMatcher(self.config.domain, self.config.matching)
        base_url = self.config.base_url

        for path_key in sorted(search_groups.keys()):
            page_counter = self._extract_one_search_path(
                path_key=path_key,
                base_listing_url=search_groups[path_key],
                scope=scope,
                seed_urls=seed_urls,
                matcher=matcher,
                base_url=base_url,
                all_urls=all_urls,
                completed=completed,
                group_state=group_state,
                page_counter=page_counter,
                url_levels=url_levels,
            )
        return page_counter

    def _extract_one_search_path(
        self,
        *,
        path_key: str,
        base_listing_url: str,
        scope: str,
        seed_urls: list[str],
        matcher: CourseUrlMatcher,
        base_url: str,
        all_urls: set[str],
        completed: set[str],
        group_state: dict[str, dict],
        page_counter: int,
        url_levels: UrlLevelMap,
    ) -> int:
        label = SEARCH_PATH_LABELS.get(path_key, scope)
        pagination_param = UrlNormalizer.detect_pagination_param(base_listing_url)
        page_step = UrlNormalizer.infer_page_step(seed_urls, pagination_param)
        state_key = UrlNormalizer.group_state_key(scope, path_key)
        state = group_state.setdefault(
            state_key,
            {
                "page_index": UrlNormalizer.get_page_number(base_listing_url, pagination_param),
                "max_pages": None,
                "empty_streak": 0,
                "pagination_param": pagination_param,
                "page_step": page_step,
            },
        )
        page_index = int(state.get("page_index", 1))
        max_pages = state.get("max_pages")
        empty_streak = int(state.get("empty_streak", 0))
        same_page_streak = int(state.get("same_page_streak", 0))
        previous_page_urls = set(state.get("previous_page_urls") or [])
        pagination_param = state.get("pagination_param") or pagination_param
        page_step = int(state.get("page_step") or page_step)

        print(f"  [{scope}] Search listing: {label} ({base_listing_url.split('?')[0]})")

        while (
            empty_streak < PAGINATION_EMPTY_LIMIT
            and same_page_streak < PAGINATION_EMPTY_LIMIT
        ):
            if max_pages is not None and page_index > int(max_pages):
                print(f"    [{scope}] Reached last page ({max_pages}) for {label}")
                break

            listing_url = UrlNormalizer.set_page_number(base_listing_url, page_index, pagination_param)
            normalized = UrlNormalizer.normalize(listing_url, keep_query=True)
            if normalized in completed:
                page_index += page_step
                continue

            page_counter += 1
            print(f"  [{scope}] Downloading listing page {page_counter}: {listing_url}")
            try:
                _title, html = self.browser.download_html(listing_url, wait_for_results=True)
            except RuntimeError as exc:
                empty_streak += 1
                print(f"    [{scope}] No HTML ({empty_streak}/{PAGINATION_EMPTY_LIMIT}): {exc}")
                self.logger.error(f"[{scope}] Listing page failed: {listing_url} — {exc}")
                page_index += page_step
                continue

            completed.add(normalized)

            start, end, total = ListingResultParser.get_result_info(html)
            if total is not None and max_pages is None:
                page_size = (end - start + 1) if start and end else 12
                max_pages = ListingResultParser.estimated_total_pages(total, page_size)
                print(f"    [{scope}] {label}: {total} results, ~{max_pages} pages ({page_size} per page)")

            page_urls = matcher.extract_from_html(html, base_url)
            page_url_set = set(page_urls)
            before_count = len(all_urls)
            if page_urls:
                all_urls.update(page_urls)
                url_levels.tag_urls(
                    page_urls,
                    scope=scope,
                    classifier=self.config.level_classifier,
                    source_scope=scope,
                )
            new_count = len(all_urls) - before_count
            if not page_urls:
                empty_streak += 1
                same_page_streak = 0
                print(
                    f"    [{scope}] no course URLs "
                    f"({empty_streak}/{PAGINATION_EMPTY_LIMIT}): {listing_url}"
                )
                self.logger.error(
                    f"[{scope}] Listing page {page_counter} no course URLs "
                    f"({empty_streak}/{PAGINATION_EMPTY_LIMIT}): {listing_url}"
                )
            else:
                empty_streak = 0
                if previous_page_urls and page_url_set == previous_page_urls:
                    same_page_streak += 1
                    print(
                        f"    [{scope}] same course URLs as previous page "
                        f"({same_page_streak}/{PAGINATION_EMPTY_LIMIT}): {listing_url}"
                    )
                    self.logger.error(
                        f"[{scope}] Listing page {page_counter} repeated listing "
                        f"({same_page_streak}/{PAGINATION_EMPTY_LIMIT}): {listing_url}"
                    )
                else:
                    same_page_streak = 0
                    if new_count > 0:
                        print(
                            f"    [{scope}] Found {new_count} new course URLs on page "
                            f"({len(page_urls)} on page, total {len(all_urls)})"
                        )
                        self.logger.ok(
                            f"[{scope}] Listing page {page_counter}: {new_count} new URLs "
                            f"from {listing_url}"
                        )
                    else:
                        print(
                            f"    [{scope}] {len(page_urls)} course URLs already known "
                            f"(+{new_count} new, total {len(all_urls)}); continuing pagination"
                        )
                        self.logger.ok(
                            f"[{scope}] Listing page {page_counter}: "
                            f"{len(page_urls)} already-known URLs, continuing "
                            f"from {listing_url}"
                        )
                previous_page_urls = page_url_set

            if self.presetup and presetup_should_stop_pagination(
                url_levels,
                self.presetup_per_level,
                self.presetup_levels,
            ):
                counts = presetup_level_counts(url_levels, self.presetup_levels)
                summary = ", ".join(
                    f"{level}={count}"
                    for level, count in counts.items()
                    if count > 0
                )
                print(
                    f"    [{scope}] Presetup scrape: enough URLs per active study level "
                    f"({summary}); stopping pagination"
                )
                break

            page_index += page_step
            state.update(
                page_index=page_index,
                max_pages=max_pages,
                empty_streak=empty_streak,
                same_page_streak=same_page_streak,
                previous_page_urls=sorted(previous_page_urls),
                pagination_param=pagination_param,
                page_step=page_step,
            )
            group_state[state_key] = state

            self.progress["course_urls"] = sorted(all_urls)
            self.progress["listing_completed"] = sorted(completed)
            self.progress["group_state"] = group_state
            if self.presetup:
                if url_levels is not None:
                    self.progress["url_levels"] = url_levels.to_progress()
                self.progress_store.save(self.progress)
            else:
                self.artifacts.persist_urls(
                    self.progress["course_urls"],
                    self.progress,
                    self.progress_store,
                    url_levels=url_levels,
                )

        return page_counter


# ============================================================================
# Top-level orchestrator: URL extraction phase
# ============================================================================

class CourseUrlScraper:
    """Runs the URL-extraction phase for either strategy and writes course_urls.csv."""

    def __init__(self, code_dir: Path, config: ScraperConfig):
        self.code_dir = code_dir.resolve()
        self.output_dir = resolve_output_dir(self.code_dir)
        self.config = config
        self.progress_store = ProgressStore(self.output_dir)
        self.artifacts = ArtifactStore(self.output_dir)
        self.logger = ScrapeLogger(self.output_dir)

    def _filter_to_study_levels(self, study_levels: list[str] | None) -> set[str]:
        if not study_levels:
            return set()
        wanted = ListingConfigLoader.scopes_for_levels(study_levels)
        listings = [
            item
            for item in self.config.degree_listings
            if item.scope in wanted or scope_to_level(item.scope) in study_levels
        ]
        catalogues = [
            item
            for item in self.config.degree_scopes
            if item.scope in wanted or scope_to_level(item.scope) in study_levels
        ]
        if self.config.degree_listings:
            if not listings:
                available = ", ".join(item.scope for item in self.config.degree_listings) or "none"
                raise ValueError(
                    f"No listing URLs for study level(s): {', '.join(study_levels)}. "
                    f"Configured scopes: {available}."
                )
            self.config.degree_listings = listings
        if self.config.degree_scopes:
            if not catalogues:
                available = ", ".join(item.scope or "?" for item in self.config.degree_scopes) or "none"
                raise ValueError(
                    f"No catalogue sources for study level(s): {', '.join(study_levels)}. "
                    f"Configured scopes: {available}."
                )
            self.config.degree_scopes = catalogues
        return wanted

    def _reset_selected_scope_progress(
        self,
        completed: set[str],
        group_state: dict[str, dict],
    ) -> None:
        prefixes = [f"{item.scope}::" for item in self.config.degree_listings]
        prefixes.extend(f"{item.scope}::" for item in self.config.degree_scopes if item.scope)
        for key in list(group_state):
            if any(key.startswith(prefix) for prefix in prefixes):
                del group_state[key]

        family_keys = {
            UrlNormalizer.listing_family_key(seed)
            for item in self.config.degree_listings
            for seed in item.seeds
        }
        if not family_keys:
            return
        keep = {
            url
            for url in completed
            if UrlNormalizer.listing_family_key(url) not in family_keys
        }
        completed.clear()
        completed.update(keep)

    def _reclassify_url_levels(self, url_levels: UrlLevelMap) -> UrlLevelMap:
        classifier = self.config.level_classifier
        if not classifier.has_custom_patterns:
            return url_levels
        rebuilt = UrlLevelMap()
        for record in url_levels.records():
            url = record["course_url"]
            source = record.get("source_scope") or ""
            classified = classifier.classify(url)
            level = classified if classified != "other" else record["study_level"]
            rebuilt.add(url, level, source)
        return rebuilt

    def _warn_presetup_listing_gaps(self, study_levels: list[str] | None) -> None:
        if self.config.strategy != STRATEGY_DEGREE_SCOPED_PAGINATED:
            return
        configured = {item.scope for item in self.config.degree_listings}
        wanted_levels = study_levels or list(SCOPE_TO_LEVEL.values())
        missing_scopes = []
        for scope in DEGREE_SCOPES:
            level = scope_to_level(scope)
            if level in wanted_levels and scope not in configured:
                missing_scopes.append(scope)
        if missing_scopes:
            print(
                "Presetup scrape warning: no listing pages configured for "
                f"{', '.join(missing_scopes)}. Add *_COURSE_LISTING_PAGE_1 keys in .env "
                "or use a mixed catalogue with URL patterns."
            )

    def _complete_presetup_scrape(
        self,
        url_levels: UrlLevelMap,
        *,
        study_levels: list[str] | None,
        presetup_per_level: int,
        presetup_seed: int | None,
        progress_store: ProgressStore,
        progress: dict,
    ) -> list[str]:
        url_levels = self._reclassify_url_levels(url_levels)
        used_seed = presetup_seed if presetup_seed is not None else random.randrange(1, 2**31)
        courses = sample_urls_per_level(
            url_levels,
            n=presetup_per_level,
            seed=used_seed,
            levels=study_levels,
        )
        if not courses:
            raise ValueError(
                "Presetup scrape sample produced no URLs. Check catalogue/listing sources."
            )
        save_presetup_scrape_sample(
            self.output_dir,
            courses,
            seed=used_seed,
            n=presetup_per_level,
        )
        write_presetup_urls_csv(self.output_dir, courses)
        urls = unique_urls([row["course_url"] for row in courses])
        progress["phase"] = "urls_complete"
        progress["course_urls"] = urls
        progress_store.save(progress)

        full_count = self.artifacts.read_course_urls()
        full_count_n = len(full_count)
        print(
            f"Presetup scrape: kept {len(courses)} URL(s) "
            f"({presetup_per_level} per study level, seed={used_seed})"
        )
        print(f"Wrote presetup URL list -> {PRESETUP_URLS_CSV}")
        if full_count_n:
            print(
                f"Full catalogue preserved: {full_count_n} URL(s) in {COURSE_URLS_CSV} (unchanged)"
            )
        for row in courses:
            print(f"  [{row['study_level']}] {row['course_url']}")
        for level in EXECUTE_LEVEL_ORDER:
            if level == "other":
                continue
            if study_levels and level not in study_levels:
                continue
            count = sum(1 for row in courses if row["study_level"] == level)
            if count < presetup_per_level:
                print(
                    f"  Warning: only {count}/{presetup_per_level} URL(s) for {level}"
                )
        self.logger.ok(f"Presetup scrape urls={len(courses)}")
        self.logger.end("ok", urls=len(courses))
        return urls

    def run(
        self,
        fresh: bool = False,
        append: bool = False,
        study_levels: list[str] | None = None,
        presetup: bool = False,
        presetup_per_level: int = SCRAPE_PRESETUP_PER_LEVEL,
        presetup_seed: int | None = None,
    ) -> list[str]:
        strategy = self.config.strategy
        selected_scopes = self._filter_to_study_levels(study_levels)
        scoped = bool(selected_scopes)
        progress_store = (
            ProgressStore(self.output_dir, PRESETUP_SCRAPE_PROGRESS_JSON)
            if presetup
            else self.progress_store
        )
        keep_existing = append or scoped
        self.logger.start(
            "urls-only",
            strategy=strategy,
            fresh=fresh,
            append=keep_existing,
            study_levels=",".join(study_levels or []) or "all",
            presetup=presetup,
        )

        if presetup and not fresh and not append and not scoped:
            full_catalogue = load_url_levels(self.output_dir)
            if full_catalogue.urls():
                print(
                    f"Presetup scrape: sampling from existing full catalogue "
                    f"({len(full_catalogue.urls())} URLs in {COURSE_URLS_CSV})"
                )
                progress = progress_store.load() or ProgressStore.new("extracting_urls", strategy)
                return self._complete_presetup_scrape(
                    full_catalogue,
                    study_levels=study_levels,
                    presetup_per_level=presetup_per_level,
                    presetup_seed=presetup_seed,
                    progress_store=progress_store,
                    progress=progress,
                )

        if fresh and not scoped and not append:
            progress_store.clear()

        progress = progress_store.load()
        if (
            not presetup
            and progress
            and progress.get("phase") == "urls_complete"
            and not fresh
            and not append
            and not scoped
        ):
            urls = progress.get("course_urls") or self.artifacts.read_course_urls()
            print(f"URLs already complete ({len(urls)}). Use --fresh to re-extract.")
            print("Or add more degree scopes and run: --append-urls")
            self.logger.ok(f"Skipped extract; {len(urls)} URLs on disk")
            self.logger.end("ok", urls=len(urls))
            return urls

        all_urls: set[str] = set()
        url_levels = UrlLevelMap()
        if keep_existing and not presetup:
            existing = self.artifacts.read_course_urls()
            all_urls.update(existing)
            url_levels.merge(UrlLevelMap.from_progress((progress or {}).get("url_levels")))
            url_levels.merge(read_level_csvs(self.output_dir))
            print(f"Keeping {len(existing)} existing URLs")
            progress = progress or ProgressStore.new("extracting_urls", strategy)
            progress["phase"] = "extracting_urls"
        elif presetup and progress and progress.get("url_levels"):
            url_levels.merge(UrlLevelMap.from_progress(progress.get("url_levels")))
            all_urls.update(progress.get("course_urls") or [])
            progress = progress or ProgressStore.new("extracting_urls", strategy)
            progress["phase"] = "extracting_urls"
        else:
            progress = ProgressStore.new("extracting_urls", strategy)

        completed: set[str] = set(progress.get("listing_completed", []))
        group_state: dict[str, dict] = dict(progress.get("group_state", {}))
        if not presetup and progress.get("url_levels"):
            url_levels.merge(UrlLevelMap.from_progress(progress.get("url_levels")))
        if scoped:
            self._reset_selected_scope_progress(completed, group_state)
            print(f"Study levels: {', '.join(study_levels or [])}")
        if presetup:
            self._warn_presetup_listing_gaps(study_levels)
        progress["listing_completed"] = sorted(completed)
        progress["group_state"] = group_state
        progress_store.save(progress)

        print(f"STRATEGY={strategy}")
        print(f"COURSE_PATH_PATTERNS={len(self.config.path_pattern_sources)} rule(s)")
        if self.config.link_selector:
            print(f"COURSE_LINK_SELECTOR={self.config.link_selector}")

        if strategy == STRATEGY_ALL_COURSE:
            self._run_all_course(all_urls, completed, url_levels)
        elif strategy == STRATEGY_DEGREE_SCOPED_PAGINATED:
            self._run_paginated(
                all_urls,
                completed,
                group_state,
                progress,
                url_levels,
                scoped=scoped,
                presetup=presetup,
                presetup_per_level=presetup_per_level,
                study_levels=study_levels,
                progress_store=progress_store,
            )
        else:
            raise ValueError(f"Unsupported STRATEGY: {strategy}")

        if presetup:
            return self._complete_presetup_scrape(
                url_levels,
                study_levels=study_levels,
                presetup_per_level=presetup_per_level,
                presetup_seed=presetup_seed,
                progress_store=progress_store,
                progress=progress,
            )

        urls = sorted(all_urls)
        progress["phase"] = "urls_complete"
        progress["listing_completed"] = sorted(completed)
        progress["group_state"] = group_state
        self.artifacts.persist_urls(urls, progress, progress_store, url_levels=url_levels)
        print(f"Wrote {len(urls)} unique URLs -> {COURSE_URLS_CSV}")
        for level, filename in LEVEL_CSV_NAMES.items():
            count = sum(1 for record in url_levels.records() if record["study_level"] == level)
            if count:
                print(f"  {filename}: {count}")
        self.logger.ok(f"Extract complete urls={len(urls)}")
        self.logger.end("ok", urls=len(urls))
        return urls

    def _run_all_course(
        self,
        all_urls: set[str],
        completed: set[str],
        url_levels: UrlLevelMap,
    ) -> None:
        sources = self.config.degree_scopes or (
            [self.config.single_catalogue] if self.config.single_catalogue else []
        )
        print(f"Catalogue sources: {len(sources)} scope(s)")
        extractor = CatalogueUrlExtractor(self.code_dir, self.config, self.logger)
        needs_browser = any(not source.catalogue_html for source in sources)
        browser: BrowserSession | None = None
        if needs_browser:
            browser = BrowserSession().__enter__()
        try:
            for source in sources:
                if source.scope:
                    print(f"--- Degree scope: {source.scope} ---")
                extractor.extract(
                    source,
                    all_urls=all_urls,
                    completed=completed,
                    browser=browser,
                    url_levels=url_levels,
                )
        finally:
            if browser is not None:
                browser.__exit__(None, None, None)

    def _run_paginated(
        self,
        all_urls: set[str],
        completed: set[str],
        group_state: dict[str, dict],
        progress: dict,
        url_levels: UrlLevelMap,
        scoped: bool = False,
        presetup: bool = False,
        presetup_per_level: int = SCRAPE_PRESETUP_PER_LEVEL,
        study_levels: list[str] | None = None,
        progress_store: ProgressStore | None = None,
    ) -> None:
        active_progress_store = progress_store or self.progress_store
        listing_configs = self.config.degree_listings
        fingerprint = ListingConfigLoader.fingerprint(listing_configs)
        saved_fingerprint = progress.get("listing_configs")
        if (
            progress.get("phase") == "extracting_urls"
            and saved_fingerprint
            and saved_fingerprint != fingerprint
        ):
            saved_by_scope = {
                item.get("scope"): item
                for item in saved_fingerprint
                if isinstance(item, dict)
            }
            if scoped:
                for item, item_fp in zip(listing_configs, fingerprint):
                    saved = saved_by_scope.get(item.scope)
                    if saved and saved != item_fp:
                        raise ValueError(
                            f".env {item.scope} listing URLs changed since the last run. "
                            "Use --fresh to restart, or restore the previous .env to resume."
                        )
            else:
                raise ValueError(
                    ".env listing URLs changed since the last run. "
                    "Use --fresh to restart, or restore the previous .env to resume."
                )

        if progress.get("phase") == "extracting_urls":
            all_urls.update(progress.get("course_urls", []))
            saved_completed = list(progress.get("listing_completed", []))
            saved_group = {
                key: dict(value) if isinstance(value, dict) else value
                for key, value in dict(progress.get("group_state", {})).items()
            }
            completed.clear()
            completed.update(saved_completed)
            group_state.clear()
            group_state.update(saved_group)
            page_counter = len(completed)
            print(f"Resuming paginated extraction ({len(all_urls)} URLs, {page_counter} pages done)")
        else:
            page_counter = 0
            if not scoped or not saved_fingerprint:
                progress["listing_configs"] = fingerprint
            for listing_config in listing_configs:
                groups = SearchGroupBuilder.build(listing_config.seeds)
                for path_key, base_url_seed in groups.items():
                    param = UrlNormalizer.detect_pagination_param(base_url_seed)
                    state_key = UrlNormalizer.group_state_key(listing_config.scope, path_key)
                    group_state.setdefault(
                        state_key,
                        {
                            "page_index": UrlNormalizer.get_page_number(base_url_seed, param),
                            "max_pages": None,
                            "empty_streak": 0,
                            "same_page_streak": 0,
                            "previous_page_urls": [],
                            "pagination_param": param,
                            "page_step": UrlNormalizer.infer_page_step(listing_config.seeds, param),
                        },
                    )

        print(f"Paginated listing scopes: {len(listing_configs)}")
        for listing_config in listing_configs:
            print(
                f"  - {listing_config.scope}: {len(listing_config.seeds)} seed URL(s) "
                f"({listing_config.search_path})"
            )

        with BrowserSession() as browser:
            extractor = PaginatedListingExtractor(
                self.code_dir,
                self.config,
                browser,
                progress,
                active_progress_store,
                self.artifacts,
                self.logger,
                presetup=presetup,
                presetup_per_level=presetup_per_level,
                presetup_levels=study_levels,
            )
            for listing_config in listing_configs:
                print(f"--- Degree scope: {listing_config.scope} ---")
                page_counter = extractor.extract_group(
                    listing_config,
                    all_urls=all_urls,
                    completed=completed,
                    group_state=group_state,
                    page_counter=page_counter,
                    url_levels=url_levels,
                )
                if presetup and presetup_should_stop_pagination(
                    url_levels,
                    presetup_per_level,
                    study_levels,
                ):
                    break


# ============================================================================
# Course page download (used by download_and_clean_course_pages.py)
# ============================================================================

class CoursePageDownloader:
    """Downloads individual course pages listed in course_urls.csv."""

    def __init__(self, code_dir: Path, *, strategy: str):
        self.code_dir = code_dir.resolve()
        self.output_dir = resolve_output_dir(self.code_dir)
        self.strategy = strategy
        self.progress_store = ProgressStore(self.output_dir)
        self.artifacts = ArtifactStore(self.output_dir)
        self.logger = ScrapeLogger(self.output_dir)

    def run(
        self,
        fresh: bool = False,
        *,
        limit: int | None = None,
        urls: list[str] | None = None,
    ) -> dict[str, int]:
        subset = urls is not None
        self.logger.start(
            "download-only",
            strategy=self.strategy,
            fresh=fresh,
            limit=limit,
            subset=subset,
        )

        if urls is not None:
            urls = [url.strip() for url in urls if (url or "").strip()]
        else:
            urls = self.artifacts.read_course_urls()
            url_levels = load_url_levels(self.output_dir)
            classifier = StudyLevelClassifier.from_code_dir(self.code_dir)
            urls, intake_skipped = dedupe_urls_by_latest_intake(
                urls,
                url_levels=url_levels,
                classifier=classifier,
            )
            if intake_skipped:
                print(
                    f"Intake dedup: keeping latest year, "
                    f"skipped {len(intake_skipped)} older URL(s)"
                )
        if not urls:
            raise ValueError(f"No URLs in {COURSE_URLS_CSV}. Run scrape_course_urls.py first.")
        if limit is not None:
            urls = urls[:limit]

        pages_dir = self.output_dir / COURSE_PAGES_DIR
        pages_dir.mkdir(parents=True, exist_ok=True)

        progress = self.progress_store.load() or ProgressStore.new("downloading", self.strategy)
        if fresh:
            progress["downloaded_urls"] = []
            progress["failed_urls"] = []
        progress["phase"] = "downloading"
        self.progress_store.save(progress)

        downloaded = set(progress.get("downloaded_urls", []))
        failed = set(progress.get("failed_urls", []))
        map_rows: list[list[str]] = []
        stats = {"total": len(urls), "downloaded": 0, "failed": 0, "skipped": 0, "excluded": 0}
        course_filter = CourseTypeFilter.from_code_dir(self.code_dir)
        from course_download_prep import (
            load_course_browser_download_config,
            load_course_download_prep,
        )

        download_prep = load_course_download_prep(self.code_dir)
        browser_config = load_course_browser_download_config(self.code_dir)
        if not browser_config.headless:
            print("Course download: headed browser (COURSE_DOWNLOAD_HEADLESS=false)")

        with BrowserSession(
            download_prep=download_prep,
            headless=browser_config.headless,
            goto_timeout_ms=browser_config.goto_timeout_ms,
        ) as browser:
            for index, url in enumerate(urls, start=1):
                if url in downloaded:
                    stats["skipped"] += 1
                    continue
                print(f"  [{index}/{len(urls)}] {url}")
                try:
                    title, html = browser.download_html(url)
                    if course_filter.should_exclude_html(html, url=url):
                        stats["excluded"] += 1
                        downloaded.add(url)
                        failed.discard(url)
                        progress["downloaded_urls"] = sorted(downloaded)
                        progress["failed_urls"] = sorted(failed)
                        self.progress_store.save(progress)
                        self.logger.ok(f"Excluded (course type): {url}")
                        continue
                    filename = f"{Utils.sanitize_filename(title)}.html"
                    target = pages_dir / filename
                    if target.exists():
                        slug = Utils.sanitize_filename(
                            urlparse(url).path.strip("/").replace("/", "_")
                        )
                        filename = f"{Utils.sanitize_filename(title)}_{slug}.html"
                        target = pages_dir / filename
                    target.write_text(html, encoding="utf-8")
                    map_rows.append([url, f"{COURSE_PAGES_DIR}/{filename}"])
                    downloaded.add(url)
                    failed.discard(url)
                    stats["downloaded"] += 1
                    progress["downloaded_urls"] = sorted(downloaded)
                    progress["failed_urls"] = sorted(failed)
                    self.progress_store.save(progress)
                    self.logger.ok(f"Course page: {url} -> {filename}")
                except Exception as exc:
                    print(f"    ERROR: {exc}")
                    failed.add(url)
                    stats["failed"] += 1
                    progress["failed_urls"] = sorted(failed)
                    self.progress_store.save(progress)
                    self.logger.error(f"Download failed: {url} — {exc}")

        self.artifacts.write_failed(sorted(failed))
        existing_map = {row[0]: row[1] for row in map_rows}
        final_rows = [[url, existing_map[url]] for url in urls if url in existing_map]
        map_path = self.output_dir / COURSE_PAGE_MAP_CSV
        if map_path.exists():
            with map_path.open(newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    url = (row.get("course_url") or "").strip()
                    html_rel = (row.get("html_path") or "").strip()
                    if url and html_rel and url not in existing_map:
                        final_rows.append([url, html_rel])
        self.artifacts.write_page_map(final_rows)

        if not subset:
            progress["phase"] = "download_complete"
            self.progress_store.save(progress)
        print(
            f"Download done: downloaded={stats['downloaded']} "
            f"skipped={stats['skipped']} excluded={stats.get('excluded', 0)} "
            f"failed={stats['failed']}"
        )
        self.logger.end("ok", **stats)
        return stats


# ============================================================================
# Backward-compatible module API (download_and_clean_course_pages.py)
# ============================================================================

def load_env_file(env_path: Path) -> dict[str, str]:
    return EnvFile(env_path).values


def load_strategy_config(work_dir: Path) -> dict:
    env_path = work_dir / ENV_FILE
    env = EnvFile(env_path)
    strategy = env.get("STRATEGY", "").strip()
    if strategy not in VALID_STRATEGIES:
        raise ValueError(
            f"{env_path}: STRATEGY must be one of {sorted(VALID_STRATEGIES)!r} "
            f"(got {strategy!r})."
        )
    return {"strategy": strategy, "env_path": str(env_path)}


def load_config(work_dir: Path) -> ScraperConfig:
    return ConfigLoader.load(work_dir)


def load_all_course_config(work_dir: Path) -> ScraperConfig:
    config = ConfigLoader.load(work_dir)
    if config.strategy != STRATEGY_ALL_COURSE:
        raise ValueError(
            f"{config.env_path}: STRATEGY must be {STRATEGY_ALL_COURSE!r} "
            f"(got {config.strategy!r})."
        )
    return config


def download_course_pages(
    work_dir: Path,
    config: dict[str, str],
    fresh: bool = False,
    *,
    limit: int | None = None,
    urls: list[str] | None = None,
) -> dict[str, int]:
    return CoursePageDownloader(
        work_dir,
        strategy=config.get("strategy", ""),
    ).run(fresh=fresh, limit=limit, urls=urls)


# ============================================================================
# CLI entry point
# ============================================================================

class ScraperCLI:
    """Parses command-line args and runs the URL-extraction phase."""

    @staticmethod
    def build_arg_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description="Extract course URLs — config from .env (STRATEGY / COURSE_CATALOGUE_*)."
        )
        parser.add_argument("--fresh", action="store_true", help="Ignore saved progress and start clean")
        parser.add_argument(
            "--append-urls",
            action="store_true",
            help=(
                "Merge newly extracted URLs into existing course_urls.csv "
                "(use after changing COURSE_CATALOGUE_HTML / URL to a second source)"
            ),
        )
        parser.add_argument(
            "--study-level",
            action="append",
            dest="study_level",
            metavar="LEVEL",
            help=(
                "Scrape only this study level (repeatable): "
                "foundation, undergraduate, postgraduate, postgraduate_research"
            ),
        )
        parser.add_argument(
            "--pick-levels",
            action="store_true",
            help="Prompt in the terminal for which study level listing(s) to scrape",
        )
        add_code_dir_argument(parser)
        parser.add_argument(
            "--presetup",
            action="store_true",
            help=(
                "After extraction, keep only N URLs per study level for presetup workflow "
                f"(default {SCRAPE_PRESETUP_PER_LEVEL}; writes {PRESETUP_URLS_CSV} and presetup_scrape_sample.json)"
            ),
        )
        parser.add_argument(
            "--presetup-per-level",
            type=int,
            default=SCRAPE_PRESETUP_PER_LEVEL,
            help=f"Presetup scrape: URLs per study level (default: {SCRAPE_PRESETUP_PER_LEVEL})",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            help="Presetup scrape RNG seed (default: random)",
        )
        return parser

    @staticmethod
    def available_scopes(config: ScraperConfig) -> list[str]:
        scopes: list[str] = []
        for item in config.degree_listings:
            if item.scope and item.scope not in scopes:
                scopes.append(item.scope)
        for item in config.degree_scopes:
            if item.scope and item.scope not in scopes:
                scopes.append(item.scope)
        return scopes or list(DEGREE_SCOPES)

    @staticmethod
    def prompt_study_levels(available_scopes: list[str]) -> list[str]:
        print("Study levels to scrape:")
        print("  0) all")
        for index, scope in enumerate(available_scopes, start=1):
            level = SCOPE_TO_LEVEL.get(scope, scope_to_level(scope) or scope.lower())
            print(f"  {index}) {level}  ({scope})")
        raw = input("Enter numbers or names (comma-separated): ").strip()
        if not raw or raw in {"0", "*", "all"}:
            return []
        chosen: list[str] = []
        tokens = [part.strip() for part in raw.split(",") if part.strip()]
        for token in tokens:
            if token.isdigit():
                number = int(token)
                if number == 0:
                    return []
                if 1 <= number <= len(available_scopes):
                    chosen.append(SCOPE_TO_LEVEL.get(available_scopes[number - 1], available_scopes[number - 1]))
                    continue
            chosen.append(token)
        return parse_study_levels(chosen)

    @staticmethod
    def main(work_dir: Path | None = None) -> int:
        args = ScraperCLI.build_arg_parser().parse_args()
        code_dir = resolve_work_dir(work_dir if work_dir is not None else args.code_dir)
        try:
            config = ConfigLoader.load(code_dir)
            study_levels = parse_study_levels(args.study_level) if args.study_level else []
            if args.pick_levels:
                study_levels = ScraperCLI.prompt_study_levels(ScraperCLI.available_scopes(config))
            scraper = CourseUrlScraper(code_dir, config)
            scraper.run(
                fresh=args.fresh,
                append=args.append_urls,
                study_levels=study_levels or None,
                presetup=args.presetup,
                presetup_per_level=args.presetup_per_level,
                presetup_seed=args.seed,
            )
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            try:
                logger = ScrapeLogger(resolve_output_dir(code_dir))
                logger.error(f"Fatal: {exc}")
                logger.end("error", message=str(exc))
            except OSError:
                pass
            return 1
        return 0


if __name__ == "__main__":
    raise SystemExit(ScraperCLI.main())