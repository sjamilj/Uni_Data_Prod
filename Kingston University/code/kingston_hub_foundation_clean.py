#!/usr/bin/env python3
"""Download and clean Kingston hub foundation pages — one .md per route variant.

Kingston integrated foundation hubs use a Vue Course Route Selector:
  Select course → Start date → Mode

This script opens each combination (default start year 2027), captures the
rendered page, and writes markdown under:

  output/clean/pre_setup_course/foundation/hub_routes/

Run from repo root or Kingston code/:

  python "Kingston University/code/kingston_hub_foundation_clean.py"
  python "Kingston University/code/kingston_hub_foundation_clean.py" --url \\
    "https://www.kingston.ac.uk/study/foundation/foundation-year-in-engineering"
  python "Kingston University/code/kingston_hub_foundation_clean.py" --start-year 2027 --limit-routes 2
  python "Kingston University/code/kingston_hub_foundation_clean.py" --headed --browser-profile
  python "Kingston University/code/kingston_hub_foundation_clean.py" --connect-cdp
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from bs4 import BeautifulSoup

_CODE_DIR = Path(__file__).resolve().parent
_SHARED = _CODE_DIR.parents[1] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from clean_config import CleanConfig, CleanConfigLoader
from course_markdown_cleanup import cleanup_course_markdown
from download_and_clean_course_pages import (
    CleanWarning,
    CourseMarkdownBuilder,
    ManifestWriter,
    UniversityNameResolver,
)
from scrape_course_urls import DEFAULT_USER_AGENT, BrowserSession, ENV_FILE, load_env_file
from study_level import PRESETUP_CLEAN_SUBDIR
from uni_paths import resolve_code_dir, resolve_output_dir
from uni_pages import course_slug_from_url

HUB_PATH_RES = (
    re.compile(r"^/study/foundation/foundation-year-in-", re.I),
    re.compile(r"^/study/undergraduate/(?:midwifery|nursing|science)-foundation-year", re.I),
)

ROUTE_SECTION = "[data-js-section-course-route-selector]"
DEFAULT_START_YEAR = "2027"
DEFAULT_BROWSER_PROFILE = ".playwright-profile"
DEFAULT_CDP_URL = "http://127.0.0.1:9222"
DEFAULT_PROFILE_NAME = "Default"
DEVICE_PROFILE_SYNC_FILES = (
    "Cookies",
    "Network/Cookies",
    "Login Data",
    "Preferences",
    "Web Data",
    "Secure Preferences",
)
PLAYWRIGHT_IGNORED_ARGS = ("--enable-automation", "--no-sandbox")
HUB_ROUTES_SUBDIR = "hub_routes"
HTML_SUBDIR = "hub_routes"


@dataclass(frozen=True)
class DeviceBrowser:
    name: str
    channel: str
    executable: Path
    user_data_dir: Path


@dataclass
class RouteVariant:
    hub_url: str
    course_label: str
    start_year: str
    mode_label: str
    ucas_code: str = ""


def is_hub_url(url: str) -> bool:
    path = urlparse(url).path.rstrip("/")
    return any(pattern.search(path) for pattern in HUB_PATH_RES)


def slugify(text: str, *, limit: int = 100) -> str:
    slug = re.sub(r"[^\w\-]+", "-", (text or "").strip()).strip("-").lower()
    return slug[:limit] or "route"


def load_hub_urls(output_dir: Path, *, explicit: list[str] | None = None) -> list[str]:
    if explicit:
        urls = [u.strip() for u in explicit if u.strip()]
        return [u for u in urls if is_hub_url(u)]

    path = output_dir / "foundation_course_urls.csv"
    if not path.is_file():
        path = output_dir / "course_urls.csv"
    urls: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            url = (row.get("course_url") or "").strip()
            if url and is_hub_url(url):
                urls.append(url)
    return sorted(set(urls))


def default_browser_profile_dir(code_dir: Path) -> Path:
    return resolve_code_dir(code_dir) / DEFAULT_BROWSER_PROFILE


def _first_existing_path(candidates: list[Path]) -> Path | None:
    for path in candidates:
        if path.is_file():
            return path
    return None


def _detect_device_browsers() -> list[DeviceBrowser]:
    local_app = Path(os.environ.get("LOCALAPPDATA", ""))
    program_files = Path(os.environ.get("PROGRAMFILES", ""))
    program_files_x86 = Path(os.environ.get("PROGRAMFILES(X86)", program_files))

    browsers: list[DeviceBrowser] = []
    edge_exe = _first_existing_path(
        [
            program_files_x86 / "Microsoft/Edge/Application/msedge.exe",
            program_files / "Microsoft/Edge/Application/msedge.exe",
        ]
    )
    edge_data = local_app / "Microsoft/Edge/User Data"
    if edge_exe and edge_data.is_dir():
        browsers.append(
            DeviceBrowser(
                name="edge",
                channel="msedge",
                executable=edge_exe,
                user_data_dir=edge_data,
            )
        )

    chrome_exe = _first_existing_path(
        [
            program_files / "Google/Chrome/Application/chrome.exe",
            program_files_x86 / "Google/Chrome/Application/chrome.exe",
            local_app / "Google/Chrome/Application/chrome.exe",
        ]
    )
    chrome_data = local_app / "Google/Chrome/User Data"
    if chrome_exe and chrome_data.is_dir():
        browsers.append(
            DeviceBrowser(
                name="chrome",
                channel="chrome",
                executable=chrome_exe,
                user_data_dir=chrome_data,
            )
        )
    return browsers


def resolve_device_browser(preference: str = "auto") -> DeviceBrowser:
    browsers = _detect_device_browsers()
    if not browsers:
        raise RuntimeError(
            "No installed Chrome or Edge profile found. "
            "Install a browser or pass --connect-cdp after starting one with "
            "--remote-debugging-port=9222."
        )
    if preference != "auto":
        for browser in browsers:
            if browser.name == preference:
                return browser
        available = ", ".join(browser.name for browser in browsers)
        raise RuntimeError(f"Browser {preference!r} not found. Available: {available}")
    return browsers[0]


def _cdp_endpoint(cdp_url: str) -> str:
    parsed = urlparse(cdp_url)
    if parsed.scheme and parsed.netloc:
        return cdp_url.rstrip("/")
    return DEFAULT_CDP_URL


def _page_from_cdp_browser(browser):
    context = browser.contexts[0] if browser.contexts else browser.new_context()
    return context.pages[0] if context.pages else context.new_page()


def try_connect_cdp(playwright, cdp_url: str):
    try:
        browser = playwright.chromium.connect_over_cdp(_cdp_endpoint(cdp_url))
    except Exception:
        return None
    return browser, _page_from_cdp_browser(browser)


def device_profile_cache_dir(code_dir: Path, browser: DeviceBrowser) -> Path:
    return resolve_code_dir(code_dir) / f".device-profile-{browser.name}"


def _copy_profile_item(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
    else:
        shutil.copy2(src, dest)


def sync_device_profile(
    browser: DeviceBrowser,
    profile_name: str,
    dest_root: Path,
    *,
    force: bool = False,
) -> Path:
    """Copy cookies/session files from the real browser into a Playwright-safe dir."""
    dest_root.mkdir(parents=True, exist_ok=True)
    src_root = browser.user_data_dir
    src_profile = src_root / profile_name
    dest_profile = dest_root / profile_name
    dest_profile.mkdir(parents=True, exist_ok=True)

    if not src_profile.is_dir():
        raise RuntimeError(
            f"Profile {profile_name!r} not found under {src_root}. "
            "Check --profile-name or pick another browser profile in edge://version."
        )

    local_state = src_root / "Local State"
    dest_local = dest_root / "Local State"
    if local_state.is_file() and (
        force
        or not dest_local.is_file()
        or local_state.stat().st_mtime > dest_local.stat().st_mtime
    ):
        try:
            _copy_profile_item(local_state, dest_local)
        except OSError as exc:
            print(f"  Warning: could not copy Local State: {exc}")

    copied = 0
    for name in DEVICE_PROFILE_SYNC_FILES:
        src = src_profile / name
        if not src.exists():
            continue
        dest = dest_profile / name
        if not force and dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
            continue
        try:
            _copy_profile_item(src, dest)
            copied += 1
        except OSError as exc:
            print(
                f"  Warning: could not copy {name}: {exc}. "
                f"Close all {browser.name} windows and run with --refresh-device-profile."
            )

    if copied or force:
        print(
            f"Synced {browser.name} profile {profile_name!r} "
            f"from {src_profile} -> {dest_root}"
        )
    else:
        print(f"Using cached {browser.name} profile at {dest_root}")
    return dest_root


def launch_device_browser(
    playwright,
    *,
    code_dir: Path,
    browser_name: str,
    profile_name: str,
    headed: bool,
    refresh_profile: bool,
):
    browser_spec = resolve_device_browser(browser_name)
    cache_dir = sync_device_profile(
        browser_spec,
        profile_name,
        device_profile_cache_dir(code_dir, browser_spec),
        force=refresh_profile,
    )

    print(
        f"Opening {browser_spec.name} with your {profile_name!r} cookies "
        f"(cached at {cache_dir})"
    )
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(cache_dir),
        channel=browser_spec.channel,
        headless=not headed,
        args=[
            f"--profile-directory={profile_name}",
            "--disable-blink-features=AutomationControlled",
        ],
        ignore_default_args=list(PLAYWRIGHT_IGNORED_ARGS),
        viewport={"width": 1400, "height": 900},
        locale="en-GB",
    )
    page = context.pages[0] if context.pages else context.new_page()
    return context, page, "persistent"


class KingstonRouteSelector:
    """Interact with Kingston Course Route Selector (three listbox columns)."""

    DROPDOWN_PANEL_SELECTORS = (
        "[role='listbox']:visible",
        ".c-listbox-scrollbar:visible",
        "div.bg-color-white.w-full.pb-fl-lg:visible",
    )
    OPTION_SELECTORS = (
        "[role='listbox']:visible [role='option']",
        ".c-listbox-scrollbar:visible button",
        "div.bg-color-white.w-full.pb-fl-lg:visible button",
    )

    def __init__(self, page):
        self.page = page
        self.section = page.locator(ROUTE_SECTION)

    def wait_ready(self) -> None:
        self.section.wait_for(state="visible", timeout=30000)
        self.page.wait_for_timeout(800)

    def _close_dropdowns(self) -> None:
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(250)

    def _column_button(self, heading: str):
        col = self.section.locator("div.md\\:col-span-4").filter(
            has=self.page.locator(f"h3:text-matches('{heading}', 'i')")
        )
        return col.locator("button[aria-haspopup='listbox']").first

    def _wait_for_dropdown_panel(self) -> None:
        last_error: Exception | None = None
        for selector in self.DROPDOWN_PANEL_SELECTORS:
            try:
                self.page.locator(selector).first.wait_for(state="visible", timeout=5000)
                return
            except PlaywrightTimeoutError as exc:
                last_error = exc
        raise RuntimeError(f"Dropdown panel did not open: {last_error}")

    def _open_listbox(self, heading: str) -> None:
        self._close_dropdowns()
        button = self._column_button(heading)
        button.wait_for(state="visible", timeout=10000)
        if button.is_disabled():
            raise RuntimeError(f"{heading} dropdown is disabled")
        button.click(timeout=5000)
        self.page.wait_for_timeout(500)
        self._wait_for_dropdown_panel()

    def _list_visible_options(self) -> list[str]:
        for selector in self.OPTION_SELECTORS:
            options = self.page.locator(selector)
            count = options.count()
            if count == 0:
                continue
            texts: list[str] = []
            for index in range(count):
                text = options.nth(index).inner_text(timeout=3000).strip()
                text = re.sub(r"\s+", " ", text)
                if text and text.lower() not in {"please select"}:
                    texts.append(text)
            if texts:
                return texts
        return []

    def _choose_option(self, label: str) -> None:
        chosen = False
        for selector in self.OPTION_SELECTORS:
            option = self.page.locator(selector, has_text=label).first
            try:
                if option.count() and option.is_visible(timeout=1500):
                    option.click(timeout=5000)
                    chosen = True
                    break
            except PlaywrightTimeoutError:
                continue
        if not chosen:
            raise RuntimeError(f"Could not select dropdown option: {label!r}")
        self.page.wait_for_timeout(700)
        self._close_dropdowns()

    def _wait_for_column_enabled(self, heading: str, *, timeout_ms: int = 15000) -> None:
        button = self._column_button(heading)
        deadline = time.time() + (timeout_ms / 1000)
        while time.time() < deadline:
            if button.is_visible(timeout=1000) and not button.is_disabled():
                return
            self.page.wait_for_timeout(300)
        raise RuntimeError(f"{heading} dropdown did not become enabled")

    def list_course_options(self) -> list[str]:
        self._open_listbox("Select course")
        options = self._list_visible_options()
        self._close_dropdowns()
        return options

    def select_course(self, label: str) -> None:
        self._open_listbox("Select course")
        self._choose_option(label)
        self._wait_for_column_enabled("Start date")

    def select_start_year(self, year: str) -> None:
        self._wait_for_column_enabled("Start date")
        self._open_listbox("Start date")
        options = self._list_visible_options()
        match = next((opt for opt in options if year in opt), None)
        if not match:
            raise RuntimeError(f"Start date {year!r} not in options: {options!r}")
        self._choose_option(match)
        self._wait_for_column_enabled("Mode")

    def select_mode(self, *, prefer_foundation: bool = True) -> str:
        self._wait_for_column_enabled("Mode")
        self._open_listbox("Mode")
        options = self._list_visible_options()
        if not options:
            raise RuntimeError("No mode options available")
        chosen = options[0]
        if prefer_foundation:
            for opt in options:
                if "foundation year" in opt.lower():
                    chosen = opt
                    break
        self._choose_option(chosen)
        return chosen

    def read_ucas_code(self) -> str:
        try:
            block = self.page.locator("h3:text-matches('UCAS Code', 'i')").locator(
                "xpath=following::div[contains(@class,'col-start-2')]"
            ).first
            text = block.inner_text(timeout=3000).strip()
            match = re.search(r"\b[A-Z0-9]{4,5}\b", text)
            return match.group(0) if match else text
        except PlaywrightTimeoutError:
            return ""

    def wait_for_route_settled(self) -> None:
        deadline = time.time() + 15
        while time.time() < deadline:
            if self.read_ucas_code():
                return
            self.page.wait_for_timeout(300)

    def prepare_sections_for_capture(self, start_year: str) -> None:
        for section_id in ("entry-requirements", "fees-and-funding"):
            section = self.page.locator(f"#{section_id}")
            if section.count() == 0:
                continue
            section.scroll_into_view_if_needed(timeout=5000)
            self.page.wait_for_timeout(400)
            buttons = section.locator("[data-js-accordion-button]")
            labels: list[str] = []
            for index in range(buttons.count()):
                button = buttons.nth(index)
                try:
                    label = button.locator(".c-accordion-item__button-text").inner_text(
                        timeout=2000
                    )
                except PlaywrightTimeoutError:
                    label = ""
                labels.append(label)
            effective_year = resolve_effective_accordion_year(labels, start_year)
            for index in range(buttons.count()):
                button = buttons.nth(index)
                label = labels[index]
                if label and not accordion_label_keep(label, start_year, effective_year):
                    continue
                if button.get_attribute("aria-expanded") != "true":
                    button.click(timeout=5000)
                    self.page.wait_for_timeout(350)

    def read_key_facts(self) -> dict[str, str]:
        facts: dict[str, str] = {}
        bar = self.page.locator("[aria-live='polite'] .c-container-fl").last
        if bar.count() == 0:
            return facts
        rows = bar.locator("div.grid")
        for index in range(rows.count()):
            row = rows.nth(index)
            try:
                label = row.locator("h3").inner_text(timeout=1000).strip()
                value = row.locator(".col-start-2").inner_text(timeout=1000).strip()
                value = re.sub(r"\s+", " ", value)
            except PlaywrightTimeoutError:
                continue
            if label and value:
                facts[label] = value
        return facts


ACCORDION_YEAR_IN_LABEL = re.compile(r"(\d{4})/\d{2}")
ACCORDION_QUAL_YEAR = re.compile(r"qualifications needed for\s*(\d{4})", re.I)


def accordion_year_from_label(label: str) -> str | None:
    text = re.sub(r"\s+", " ", label.strip())
    match = ACCORDION_YEAR_IN_LABEL.search(text)
    if match:
        return match.group(1)
    match = ACCORDION_QUAL_YEAR.search(text)
    if match:
        return match.group(1)
    return None


def resolve_effective_accordion_year(labels: list[str], start_year: str) -> str | None:
    years = sorted({year for label in labels if (year := accordion_year_from_label(label))})
    if not years:
        return None
    if start_year in years:
        return start_year
    return years[-1]


def accordion_label_keep(label: str, start_year: str, effective_year: str | None) -> bool:
    year = accordion_year_from_label(label)
    if year is None:
        return True
    if effective_year is None:
        return start_year in label
    return year == effective_year


def collect_section_accordion_labels(section) -> list[str]:
    labels: list[str] = []
    for button in section.select("[data-js-accordion-button] .c-accordion-item__button-text"):
        labels.append(button.get_text(" ", strip=True))
    return labels


def preprocess_hub_html(html: str, start_year: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for section in soup.select("#fees-and-funding, #entry-requirements"):
        labels = collect_section_accordion_labels(section)
        effective_year = resolve_effective_accordion_year(labels, start_year)
        for item in section.select(".c-accordion-item"):
            button = item.select_one(".c-accordion-item__button-text")
            label = button.get_text(" ", strip=True) if button else ""
            if label and not accordion_label_keep(label, start_year, effective_year):
                item.decompose()
    return str(soup)


def format_key_facts_markdown(facts: dict[str, str]) -> str:
    if not facts:
        return ""
    lines = ["## Key course information", ""]
    for label, value in facts.items():
        lines.append(f"- **{label}:** {value}")
    return "\n".join(lines)


def inject_key_facts(markdown: str, facts_markdown: str) -> str:
    if not facts_markdown.strip():
        return markdown
    marker = "## Entry requirements"
    if marker in markdown:
        return markdown.replace(marker, facts_markdown + "\n\n" + marker, 1)
    return markdown.rstrip() + "\n\n" + facts_markdown + "\n"


def patch_hub_fees_markdown(
    markdown: str,
    html: str,
    variant: RouteVariant,
) -> str:
    """Hub fees accordions point to linked degrees; keep only the selected route."""
    marker = "## Fees and funding"
    if marker not in markdown:
        return markdown

    soup = BeautifulSoup(html, "html.parser")
    why = soup.select_one("#why-choose-this-course")
    if not why:
        return markdown

    course_lines: list[str] = []
    for item in why.select("li"):
        text = re.sub(r"\s+", " ", item.get_text(" ", strip=True))
        if not text or "ucas code" not in text.lower():
            continue
        course_lines.append(f"- {text}")

    course_lines = filter_hub_fees_to_route(course_lines, variant)
    if not course_lines:
        return markdown

    parts = markdown.split(marker, 1)
    if len(parts) != 2:
        return markdown
    head, tail = parts
    tail = re.sub(
        r"(\n### [\d/]+\n\nFees are included on the relevant webpage[^\n]*\.\n\n)(?:- .+\n?)+",
        r"\1" + "\n".join(course_lines) + "\n",
        tail,
        count=1,
    )
    return head + marker + tail


def filter_hub_fees_to_route(lines: list[str], variant: RouteVariant) -> list[str]:
    if variant.ucas_code:
        for line in lines:
            if variant.ucas_code.upper() in line.upper():
                return [line]

    label = re.sub(r"\s+", " ", variant.course_label.strip().lower())
    label = re.sub(r"\s*\(subject to validation\)\s*", " ", label).strip()
    for line in lines:
        if label and label in line.lower():
            return [line]

    for line in lines:
        first_words = " ".join(label.split()[:3])
        if first_words and first_words in line.lower():
            return [line]
    return lines[:1]


def load_hub_route_clean_config(code_dir: Path) -> CleanConfig:
    base = CleanConfigLoader.load(code_dir)
    env = load_env_file(resolve_code_dir(code_dir) / ENV_FILE)
    blocks_raw = CleanConfigLoader.parse_selector_list(env.get("HUB_ROUTE_CLEAN_BLOCKS"))
    if not blocks_raw:
        blocks = [
            ("Entry requirements", "#entry-requirements"),
            ("Fees and funding", "#fees-and-funding"),
        ]
    else:
        blocks = [CleanConfigLoader.parse_clean_block_line(line) for line in blocks_raw]
    return CleanConfig(
        blocks=blocks,
        strip_within=base.strip_within,
        expand_tabs=base.expand_tabs,
        title_selector=base.title_selector,
        engine=base.engine,
        env_path=base.env_path,
    )


def build_markdown(
    code_dir: Path,
    html: str,
    *,
    source_html: str,
    source_url: str,
    clean_config: CleanConfig | None = None,
) -> str:
    config = clean_config or CleanConfigLoader.load(code_dir)
    warnings: list[CleanWarning] = []
    markdown = CourseMarkdownBuilder.from_config(
        html,
        config,
        code_dir,
        warnings=warnings,
        source_html=source_html,
        source_url=source_url,
    )
    return cleanup_course_markdown(markdown, code_dir=code_dir)


def build_frontmatter(
    *,
    university: str,
    hub_url: str,
    variant: RouteVariant,
    source_html: str,
    md_rel: str,
) -> str:
    lines = [
        "---",
        f"source_html: {source_html}",
        f"source_url: {hub_url}",
        "page_type: course",
        f"university: {university}",
        f"cleaned_at: {date.today().isoformat()}",
        f"course_url: {hub_url}",
        "study_level: foundation",
        f"hub_url: {hub_url}",
        f"route_course: {variant.course_label}",
        f"start_year: {variant.start_year}",
        f"route_mode: {variant.mode_label}",
        f"output_md: {md_rel}",
    ]
    if variant.ucas_code:
        lines.append(f"ucas_code: {variant.ucas_code}")
    lines.extend(["---", ""])
    return "\n".join(lines)


def variant_slug(hub_url: str, variant: RouteVariant) -> str:
    hub_slug = course_slug_from_url(hub_url)
    route_slug = slugify(variant.course_label)
    year = slugify(variant.start_year)
    mode_slug = slugify(variant.mode_label)[:40]
    return f"{hub_slug}__{route_slug}__{year}__{mode_slug}"


def process_hub(
    page,
    *,
    code_dir: Path,
    output_dir: Path,
    hub_url: str,
    start_year: str,
    limit_routes: int | None,
    dry_run: bool,
) -> int:
    university = UniversityNameResolver.resolve(code_dir)
    html_dir = output_dir / "course_pages" / HTML_SUBDIR
    md_dir = output_dir / "clean" / PRESETUP_CLEAN_SUBDIR / "foundation" / HUB_ROUTES_SUBDIR
    html_dir.mkdir(parents=True, exist_ok=True)
    md_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nHub: {hub_url}")
    page.goto(hub_url, wait_until="domcontentloaded", timeout=60000)
    BrowserSession.dismiss_cookies(page)
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except PlaywrightTimeoutError:
        page.wait_for_load_state("load", timeout=15000)
    page.wait_for_timeout(1500)

    title = (page.title() or "").lower()
    if "just a moment" in title:
        page.wait_for_timeout(8000)
        page.reload(wait_until="domcontentloaded", timeout=60000)
        BrowserSession.dismiss_cookies(page)
        page.wait_for_timeout(2000)
        title = (page.title() or "").lower()

    if "just a moment" in title:
        raise RuntimeError("Cloudflare challenge — retry with --headed or later")

    selector = KingstonRouteSelector(page)
    selector.wait_ready()

    if not selector.section.locator("h3:text-matches('Select course', 'i')").count():
        print("  No route selector on page — skip")
        return 0

    course_options = selector.list_course_options()
    if not course_options:
        print("  No course options in selector — skip")
        return 0

    if limit_routes is not None:
        course_options = course_options[:limit_routes]

    print(f"  Routes to process: {len(course_options)} (start year {start_year})")
    written = 0

    for course_label in course_options:
        print(f"  - {course_label}")
        if dry_run:
            continue

        page.goto(hub_url, wait_until="domcontentloaded", timeout=60000)
        BrowserSession.dismiss_cookies(page)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeoutError:
            page.wait_for_load_state("load", timeout=10000)
        page.wait_for_timeout(1000)
        selector = KingstonRouteSelector(page)
        selector.wait_ready()

        selector.select_course(course_label)
        selector.select_start_year(start_year)
        mode_label = selector.select_mode(prefer_foundation=True)
        selector.wait_for_route_settled()
        selector.prepare_sections_for_capture(start_year)
        ucas = selector.read_ucas_code()

        variant = RouteVariant(
            hub_url=hub_url,
            course_label=course_label,
            start_year=start_year,
            mode_label=mode_label,
            ucas_code=ucas,
        )
        slug = variant_slug(hub_url, variant)
        html_name = f"{slug}.html"
        md_name = f"{slug}.md"
        html_path = html_dir / html_name
        md_path = md_dir / md_name

        html = preprocess_hub_html(page.content(), start_year)
        html_path.write_text(html, encoding="utf-8")

        html_rel = f"course_pages/{HTML_SUBDIR}/{html_name}"
        md_rel = f"clean/{PRESETUP_CLEAN_SUBDIR}/foundation/{HUB_ROUTES_SUBDIR}/{md_name}"
        body = build_frontmatter(
            university=university,
            hub_url=hub_url,
            variant=variant,
            source_html=html_rel,
            md_rel=md_rel,
        )
        markdown = build_markdown(
            code_dir,
            html,
            source_html=html_rel,
            source_url=hub_url,
            clean_config=load_hub_route_clean_config(code_dir),
        )
        markdown = inject_key_facts(
            markdown,
            format_key_facts_markdown(selector.read_key_facts()),
        )
        markdown = patch_hub_fees_markdown(markdown, html, variant)
        title = f"# {course_label} ({start_year})"
        if ucas:
            title += f" — UCAS {ucas}"
        md_lines = markdown.splitlines()
        if md_lines and md_lines[0].startswith("# "):
            md_lines[0] = title
            markdown_body = "\n".join(md_lines)
        else:
            markdown_body = title + "\n\n" + markdown
        md_path.write_text(body + markdown_body + "\n", encoding="utf-8")
        print(f"    -> {md_path.name}" + (f" (UCAS {ucas})" if ucas else ""))
        written += 1
        time.sleep(0.5)

    return written


@dataclass
class BrowserLaunchConfig:
    mode: str  # ephemeral | isolated | device | cdp
    code_dir: Path = _CODE_DIR
    headed: bool = True
    profile_dir: Path | None = None
    browser_name: str = "auto"
    profile_name: str = DEFAULT_PROFILE_NAME
    cdp_url: str = DEFAULT_CDP_URL
    refresh_profile: bool = False


def launch_page(playwright, config: BrowserLaunchConfig):
    """Return (handle, page, close_mode)."""
    if config.mode == "device":
        return launch_device_browser(
            playwright,
            code_dir=config.code_dir,
            browser_name=config.browser_name,
            profile_name=config.profile_name,
            headed=config.headed,
            refresh_profile=config.refresh_profile,
        )

    if config.mode == "cdp":
        connected = try_connect_cdp(playwright, config.cdp_url)
        if not connected:
            browser_spec = resolve_device_browser(config.browser_name)
            raise RuntimeError(
                f"Could not connect to {_cdp_endpoint(config.cdp_url)}.\n"
                "Close all browser windows, then start Edge/Chrome manually:\n"
                f'  "{browser_spec.executable}" --remote-debugging-port=9222\n'
                "Then run with --connect-cdp"
            )
        print(f"Connected to existing browser via {_cdp_endpoint(config.cdp_url)}")
        return connected[0], connected[1], "cdp"

    if config.mode == "isolated":
        profile_dir = config.profile_dir or default_browser_profile_dir(config.code_dir)
        profile_dir.mkdir(parents=True, exist_ok=True)
        print(f"Isolated browser profile: {profile_dir}")
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=not config.headed,
            user_agent=DEFAULT_USER_AGENT,
            viewport={"width": 1400, "height": 900},
            locale="en-GB",
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=list(PLAYWRIGHT_IGNORED_ARGS),
        )
        page = context.pages[0] if context.pages else context.new_page()
        return context, page, "persistent"

    browser = playwright.chromium.launch(headless=not config.headed)
    context = browser.new_context(user_agent=DEFAULT_USER_AGENT)
    page = context.new_page()
    return context, page, "ephemeral"


def close_page(handle, *, close_mode: str) -> None:
    if close_mode == "cdp":
        handle.close()
        return
    handle.close()


def resolve_browser_launch_config(args, code_dir: Path) -> BrowserLaunchConfig:
    if args.no_browser_profile:
        return BrowserLaunchConfig(mode="ephemeral", code_dir=code_dir, headed=args.headed)

    if args.connect_cdp is not None:
        return BrowserLaunchConfig(
            mode="cdp",
            code_dir=code_dir,
            headed=True,
            browser_name=args.browser,
            cdp_url=args.connect_cdp,
        )

    profile_arg = args.browser_profile
    if profile_arg == "isolated":
        return BrowserLaunchConfig(
            mode="isolated",
            code_dir=code_dir,
            headed=args.headed,
            profile_dir=default_browser_profile_dir(code_dir),
        )

    if profile_arg and profile_arg not in {"device", "default"}:
        return BrowserLaunchConfig(
            mode="isolated",
            code_dir=code_dir,
            headed=args.headed,
            profile_dir=Path(profile_arg).expanduser().resolve(),
        )

    return BrowserLaunchConfig(
        mode="device",
        code_dir=code_dir,
        headed=True,
        browser_name=args.browser,
        profile_name=args.profile_name,
        refresh_profile=args.refresh_device_profile,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-dir", type=Path, default=_CODE_DIR)
    parser.add_argument(
        "--url",
        action="append",
        default=[],
        help="Hub foundation URL (repeatable). Default: all hubs in foundation_course_urls.csv",
    )
    parser.add_argument("--start-year", default=DEFAULT_START_YEAR)
    parser.add_argument(
        "--limit-routes",
        type=int,
        default=None,
        help="Process only first N course options per hub (for testing)",
    )
    parser.add_argument("--dry-run", action="store_true", help="List routes only, no download/clean")
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show browser window (ephemeral mode only; device profile always opens a window)",
    )
    parser.add_argument(
        "--browser-profile",
        nargs="?",
        const="device",
        default="device",
        metavar="MODE",
        help=(
            "Browser profile mode (default: device). "
            "Pass alone for your installed Chrome/Edge profile; "
            "'isolated' for code/.playwright-profile; or a custom directory path."
        ),
    )
    parser.add_argument(
        "--no-browser-profile",
        action="store_true",
        help="Ephemeral Playwright browser (no saved cookies)",
    )
    parser.add_argument(
        "--browser",
        choices=["auto", "chrome", "edge"],
        default="auto",
        help="Which installed browser profile to use (default: auto-detect)",
    )
    parser.add_argument(
        "--profile-name",
        default=DEFAULT_PROFILE_NAME,
        help=f"Chrome/Edge profile folder name (default: {DEFAULT_PROFILE_NAME})",
    )
    parser.add_argument(
        "--refresh-device-profile",
        action="store_true",
        help="Re-copy cookies from your real Edge/Chrome profile before scraping",
    )
    parser.add_argument(
        "--connect-cdp",
        nargs="?",
        const=DEFAULT_CDP_URL,
        default=None,
        metavar="URL",
        help=(
            "Attach to an already running browser at CDP URL "
            f"(default {DEFAULT_CDP_URL}). Start Edge first with "
            "--remote-debugging-port=9222."
        ),
    )
    args = parser.parse_args()

    code_dir = resolve_code_dir(args.code_dir)
    output_dir = resolve_output_dir(code_dir)
    browser_config = resolve_browser_launch_config(args, code_dir)
    hub_urls = load_hub_urls(output_dir, explicit=args.url or None)
    if not hub_urls:
        print("No hub foundation URLs found.", file=sys.stderr)
        return 1

    print(f"Hub foundation pages: {len(hub_urls)}")
    total = 0
    failed = 0

    with sync_playwright() as playwright:
        handle, page, close_mode = launch_page(playwright, browser_config)
        try:
            for hub_url in hub_urls:
                try:
                    total += process_hub(
                        page,
                        code_dir=code_dir,
                        output_dir=output_dir,
                        hub_url=hub_url,
                        start_year=str(args.start_year),
                        limit_routes=args.limit_routes,
                        dry_run=args.dry_run,
                    )
                except Exception as exc:
                    failed += 1
                    print(f"  ERROR: {exc}", file=sys.stderr)
        finally:
            close_page(handle, close_mode=close_mode)

    print(f"\nDone: {total} markdown file(s) written, {failed} hub(s) failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
