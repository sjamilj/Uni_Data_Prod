"""Browser launch for course download and listing (Playwright).

CDP attach, device-profile cookie sync, and Cloudflare wait behaviour are defined in
docs/shared/cloudflare-course-download.md — keep implementation aligned with that doc.
"""
from __future__ import annotations

import os
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from uni_paths import resolve_code_dir

DEFAULT_CDP_URL = "http://127.0.0.1:9222"
DEFAULT_PROFILE_NAME = "Default"
PLAYWRIGHT_IGNORED_ARGS = ("--enable-automation", "--no-sandbox")
DEVICE_PROFILE_SYNC_FILES = (
    "Cookies",
    "Network/Cookies",
    "Login Data",
    "Preferences",
    "Web Data",
    "Secure Preferences",
)

_CLOUDFLARE_TITLE_MARKERS = (
    "just a moment",
    "verifying you are human",
    "attention required",
)
_CLOUDFLARE_HTML_MARKERS = (
    "cf-browser-verification",
    "challenge-platform",
    "turnstile",
    "cdn-cgi/challenge",
)


@dataclass(frozen=True)
class DeviceBrowser:
    name: str
    channel: str
    executable: Path
    user_data_dir: Path


@dataclass(frozen=True)
class CourseDownloadBrowserConfig:
    """Parsed COURSE_DOWNLOAD_* keys from university code/.env."""

    cdp_url: str = ""
    use_device_profile: bool = False
    browser: str = "auto"
    profile_name: str = DEFAULT_PROFILE_NAME
    refresh_profile: bool = False
    headless: bool = True
    cloudflare_warmup: bool = False
    cloudflare_auto_click: bool = False
    cloudflare_wait_seconds: int = 0

    @classmethod
    def from_env(cls, env: dict[str, str]) -> CourseDownloadBrowserConfig:
        def _bool(key: str, default: bool = False) -> bool:
            raw = (env.get(key) or "").strip().lower()
            if not raw:
                return default
            return raw in {"1", "true", "yes", "on"}

        def _int(key: str, default: int = 0) -> int:
            raw = (env.get(key) or "").strip()
            if not raw:
                return default
            try:
                return max(0, int(raw))
            except ValueError:
                return default

        browser = (env.get("COURSE_DOWNLOAD_BROWSER") or "").strip().lower()
        if not browser:
            channel = (env.get("COURSE_DOWNLOAD_BROWSER_CHANNEL") or "").strip().lower()
            if channel in {"msedge", "edge"}:
                browser = "edge"
            elif channel == "chrome":
                browser = "chrome"
            else:
                browser = "auto"

        refresh = _bool("COURSE_DOWNLOAD_REFRESH_DEVICE_PROFILE") or _bool(
            "COURSE_DOWNLOAD_REFRESH_PROFILE"
        )

        headless_default = True
        headless_raw = (env.get("COURSE_DOWNLOAD_HEADLESS") or "").strip().lower()
        if headless_raw:
            headless = headless_raw in {"1", "true", "yes", "on"}
        else:
            headless = headless_default

        return cls(
            cdp_url=(env.get("COURSE_DOWNLOAD_CDP_URL") or "").strip(),
            use_device_profile=_bool("COURSE_DOWNLOAD_USE_DEVICE_PROFILE"),
            browser=browser or "auto",
            profile_name=(env.get("COURSE_DOWNLOAD_PROFILE_NAME") or DEFAULT_PROFILE_NAME).strip()
            or DEFAULT_PROFILE_NAME,
            refresh_profile=refresh,
            headless=headless,
            cloudflare_warmup=_bool("COURSE_DOWNLOAD_CLOUDFLARE_WARMUP"),
            cloudflare_auto_click=_bool("COURSE_DOWNLOAD_CLOUDFLARE_AUTO_CLICK"),
            cloudflare_wait_seconds=_int("COURSE_DOWNLOAD_CLOUDFLARE_WAIT_SECONDS"),
        )


def _first_existing_path(candidates: list[Path]) -> Path | None:
    for path in candidates:
        if path.is_file():
            return path
    return None


def detect_device_browsers() -> list[DeviceBrowser]:
    """Installed Chromium-based browsers (see cloudflare-course-download.md)."""
    local_app = Path(os.environ.get("LOCALAPPDATA", ""))
    program_files = Path(os.environ.get("PROGRAMFILES", ""))
    program_files_x86 = Path(os.environ.get("PROGRAMFILES(X86)", program_files))

    browsers: list[DeviceBrowser] = []

    brave_exe = _first_existing_path(
        [
            program_files / "BraveSoftware/Brave-Browser/Application/brave.exe",
            local_app / "BraveSoftware/Brave-Browser/Application/brave.exe",
        ]
    )
    brave_data = local_app / "BraveSoftware/Brave-Browser/User Data"
    if brave_exe and brave_data.is_dir():
        browsers.append(
            DeviceBrowser(
                name="brave",
                channel="",
                executable=brave_exe,
                user_data_dir=brave_data,
            )
        )

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
    browsers = detect_device_browsers()
    if not browsers:
        raise RuntimeError(
            "No installed Brave, Chrome, or Edge profile found. "
            "Install a browser, use CDP (COURSE_DOWNLOAD_CDP_URL), or set "
            "COURSE_DOWNLOAD_USE_DEVICE_PROFILE=false."
        )
    if preference != "auto":
        for browser in browsers:
            if browser.name == preference:
                return browser
        available = ", ".join(browser.name for browser in browsers)
        raise RuntimeError(f"Browser {preference!r} not found. Available: {available}")
    return browsers[0]


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
            "Check COURSE_DOWNLOAD_PROFILE_NAME."
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
                f"Close all {browser.name} windows and set "
                "COURSE_DOWNLOAD_REFRESH_DEVICE_PROFILE=true."
            )

    if copied or force:
        print(
            f"Synced {browser.name} profile {profile_name!r} "
            f"from {src_profile} -> {dest_root}"
        )
    else:
        print(f"Using cached {browser.name} profile at {dest_root}")
    return dest_root


def cdp_endpoint(cdp_url: str) -> str:
    parsed = urlparse(cdp_url)
    if parsed.scheme and parsed.netloc:
        return cdp_url.rstrip("/")
    return DEFAULT_CDP_URL


def _iter_cdp_pages(browser: Any) -> list[Any]:
    pages: list[Any] = []
    for context in browser.contexts or []:
        pages.extend(context.pages or [])
    return pages


def page_from_cdp_browser(browser: Any, *, prefer_host: str = "") -> Any:
    pages = _iter_cdp_pages(browser)
    host = (prefer_host or "").strip().lower()
    if host and pages:
        for page in pages:
            try:
                netloc = urlparse(page.url or "").netloc.lower()
            except Exception:
                continue
            if netloc == host or netloc.endswith("." + host):
                return page
    if pages:
        return pages[0]
    context = browser.contexts[0] if browser.contexts else browser.new_context()
    return context.pages[0] if context.pages else context.new_page()


def try_connect_cdp(
    playwright: Any, cdp_url: str, *, prefer_host: str = ""
) -> tuple[Any, Any] | None:
    try:
        browser = playwright.chromium.connect_over_cdp(cdp_endpoint(cdp_url))
    except Exception:
        return None
    return browser, page_from_cdp_browser(browser, prefer_host=prefer_host)


def launch_device_browser_context(
    playwright: Any,
    *,
    code_dir: Path,
    browser_name: str,
    profile_name: str,
    headed: bool,
    refresh_profile: bool,
) -> tuple[Any, Any]:
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
    launch_kwargs: dict[str, Any] = {
        "user_data_dir": str(cache_dir),
        "headless": not headed,
        "args": [
            f"--profile-directory={profile_name}",
            "--disable-blink-features=AutomationControlled",
        ],
        "ignore_default_args": list(PLAYWRIGHT_IGNORED_ARGS),
        "viewport": {"width": 1400, "height": 900},
        "locale": "en-GB",
    }
    if browser_spec.channel:
        launch_kwargs["channel"] = browser_spec.channel
    else:
        launch_kwargs["executable_path"] = str(browser_spec.executable)

    context = playwright.chromium.launch_persistent_context(**launch_kwargs)
    page = context.pages[0] if context.pages else context.new_page()
    return context, page


def launch_course_download_browser(
    playwright: Any,
    *,
    code_dir: Path,
    config: CourseDownloadBrowserConfig,
    user_agent: str,
    prefer_host: str = "",
) -> tuple[Any, Any, str]:
    """Return (handle, page, close_mode). close_mode: cdp | persistent | ephemeral."""
    code_dir = resolve_code_dir(code_dir)

    if config.cdp_url:
        connected = try_connect_cdp(playwright, config.cdp_url, prefer_host=prefer_host)
        if not connected:
            browser_spec = resolve_device_browser(config.browser)
            raise RuntimeError(
                f"Could not connect to {cdp_endpoint(config.cdp_url)}.\n"
                "Start your browser with remote debugging, for example:\n"
                f'  "{browser_spec.executable}" --remote-debugging-port=9222\n'
                "Open a tab and pass Cloudflare manually, then re-run.\n"
                "See docs/shared/cloudflare-course-download.md"
            )
        print(f"Connected to existing browser via {cdp_endpoint(config.cdp_url)}")
        return connected[0], connected[1], "cdp"

    if config.use_device_profile:
        context, page = launch_device_browser_context(
            playwright,
            code_dir=code_dir,
            browser_name=config.browser,
            profile_name=config.profile_name,
            headed=not config.headless,
            refresh_profile=config.refresh_profile,
        )
        return context, page, "persistent"

    browser = playwright.chromium.launch(headless=config.headless)
    context = browser.new_context(user_agent=user_agent)
    page = context.new_page()
    return browser, page, "ephemeral"


def close_course_download_browser(handle: Any, close_mode: str) -> None:
    if close_mode == "cdp":
        handle.close()
        return
    handle.close()


def is_cloudflare_challenge_page(title: str, html: str) -> bool:
    title_l = (title or "").casefold()
    if any(marker in title_l for marker in _CLOUDFLARE_TITLE_MARKERS):
        return True
    html_l = (html or "").casefold()
    return any(marker in html_l for marker in _CLOUDFLARE_HTML_MARKERS)


def wait_for_cloudflare_clear(
    page: Any,
    *,
    max_seconds: int,
    poll_ms: int = 2000,
) -> bool:
    if max_seconds <= 0:
        return False
    deadline = time.time() + max_seconds
    while time.time() < deadline:
        title = page.title() or ""
        html = page.content()
        if not is_cloudflare_challenge_page(title, html):
            return True
        remaining = int(deadline - time.time())
        print(
            f"  Cloudflare challenge — complete verification in your browser "
            f"({remaining}s left)…"
        )
        page.wait_for_timeout(poll_ms)
    title = page.title() or ""
    return not is_cloudflare_challenge_page(title, page.content())


def maybe_auto_click_cloudflare(page: Any) -> None:
    selectors = (
        "input[type='checkbox']",
        "label:has-text('Verify you are human')",
        "iframe[src*='challenges.cloudflare.com']",
    )
    for selector in selectors:
        try:
            target = page.locator(selector).first
            if target.is_visible(timeout=1500):
                target.click(timeout=3000)
                page.wait_for_timeout(1000)
                return
        except Exception:
            continue
