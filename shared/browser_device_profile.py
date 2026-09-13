"""Sync cookies from the user's Chrome/Edge profile for Playwright downloads."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from uni_paths import resolve_code_dir

PLAYWRIGHT_IGNORED_ARGS = ("--enable-automation", "--no-sandbox")
DEFAULT_PROFILE_NAME = "Default"
DEVICE_PROFILE_SYNC_FILES = (
    "Cookies",
    "Network/Cookies",
    "Login Data",
    "Preferences",
    "Web Data",
    "Secure Preferences",
)


@dataclass(frozen=True)
class DeviceBrowser:
    name: str
    channel: str
    executable: Path
    user_data_dir: Path


def _first_existing_path(candidates: list[Path]) -> Path | None:
    for path in candidates:
        if path.is_file():
            return path
    return None


def detect_device_browsers() -> list[DeviceBrowser]:
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
    browsers = detect_device_browsers()
    if not browsers:
        raise RuntimeError(
            "No installed Chrome or Edge profile found. "
            "Install a browser or set COURSE_DOWNLOAD_USE_DEVICE_PROFILE=false."
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
                f"Close all {browser.name} windows and set COURSE_DOWNLOAD_REFRESH_PROFILE=true."
            )

    if copied or force:
        print(
            f"Synced {browser.name} profile {profile_name!r} "
            f"from {src_profile} -> {dest_root}"
        )
    else:
        print(f"Using cached {browser.name} profile at {dest_root}")
    return dest_root


def launch_device_browser_context(
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
    return context, page
