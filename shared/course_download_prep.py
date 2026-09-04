"""Playwright steps before saving course page HTML (per-university .env)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scrape_course_urls import ENV_FILE, load_env_file


def _parse_selector_list(value: str | None) -> list[str]:
    if not value or not str(value).strip():
        return []
    items: list[str] = []
    for part in re.split(r"[\n;]+", str(value)):
        item = part.strip().strip('"').strip("'")
        if not item:
            continue
        if item.startswith("#") and not re.match(r"#\w", item):
            continue
        items.append(item)
    return items


@dataclass
class CourseBrowserDownloadConfig:
    """Playwright browser options for course page downloads."""

    headless: bool = True
    goto_timeout_ms: int = 60000


@dataclass
class CourseDownloadPrepConfig:
    """Optional Playwright interactions before course HTML is saved."""

    mode: str
    entry_tab_selectors: list[str]
    country_select: str
    country_label: str
    country_wait_url: str
    scroll_to: str
    env_path: str

    @property
    def enabled(self) -> bool:
        return bool(self.mode)


def _env_bool(value: str | None, *, default: bool) -> bool:
    if value is None or not str(value).strip():
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


class CourseDownloadPrepLoader:
    """Load COURSE_DOWNLOAD_* settings from code/.env."""

    @classmethod
    def load(cls, code_dir: Path) -> CourseDownloadPrepConfig:
        env_path = code_dir / ENV_FILE
        env = load_env_file(env_path)
        mode = (env.get("COURSE_DOWNLOAD_PREP") or "").strip().lower()
        default_tabs = [
            'a:has-text("Entry requirements")',
            'a[href="#entryRequirements"]',
            'button:has-text("Entry requirements")',
        ]
        entry_tabs = _parse_selector_list(
            env.get("COURSE_DOWNLOAD_ENTRY_TAB_SELECTORS")
        ) or default_tabs
        return CourseDownloadPrepConfig(
            mode=mode,
            entry_tab_selectors=entry_tabs,
            country_select=(
                env.get("COURSE_DOWNLOAD_COUNTRY_SELECT") or "#country-requirement"
            ).strip(),
            country_label=(
                env.get("COURSE_DOWNLOAD_COUNTRY") or "Bangladesh"
            ).strip(),
            country_wait_url=(
                env.get("COURSE_DOWNLOAD_COUNTRY_WAIT_URL")
                or "courseInternationalEntryEquivalent"
            ).strip(),
            scroll_to=(env.get("COURSE_DOWNLOAD_SCROLL_TO") or "#entryRequirements").strip(),
            env_path=str(env_path),
        )


class CourseDownloadPreparer:
    """Run configured Playwright steps on a loaded course page."""

    def __init__(self, config: CourseDownloadPrepConfig):
        self.config = config

    def prepare(self, page: Any) -> None:
        if not self.config.enabled:
            return
        if self.config.mode in {"entry_tab_country", "entry_tab_country_select"}:
            self._entry_tab_country(page)
            return
        raise ValueError(
            f"Unknown COURSE_DOWNLOAD_PREP={self.config.mode!r} in {self.config.env_path}"
        )

    def _click_first_visible(self, page: Any, selectors: list[str]) -> bool:
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.count() and locator.is_visible(timeout=2000):
                    locator.click(timeout=5000)
                    page.wait_for_timeout(1000)
                    return True
            except Exception:
                continue
        return False

    def _entry_tab_country(self, page: Any) -> None:
        clicked = self._click_first_visible(
            page,
            self.config.entry_tab_selectors,
        )
        if not clicked:
            print("    Warning: entry tab not found — saving default view")

        if self.config.scroll_to:
            try:
                page.locator(self.config.scroll_to).first.scroll_into_view_if_needed(
                    timeout=5000
                )
                page.wait_for_timeout(500)
            except Exception:
                pass

        country_select = self.config.country_select
        if not page.locator(country_select).count():
            print(
                f"    Warning: country select {country_select!r} not found — "
                "saving default view"
            )
            return

        wait_fragment = self.config.country_wait_url

        def _matches_response(response: Any) -> bool:
            return (
                wait_fragment in response.url
                and response.status == 200
            )

        try:
            with page.expect_response(_matches_response, timeout=15000):
                page.locator(country_select).select_option(
                    label=self.config.country_label
                )
        except Exception:
            page.locator(country_select).select_option(
                label=self.config.country_label
            )

        page.wait_for_timeout(1500)


def load_course_browser_download_config(code_dir: Path) -> CourseBrowserDownloadConfig:
    env_path = code_dir / ENV_FILE
    env = load_env_file(env_path)
    headless = _env_bool(env.get("COURSE_DOWNLOAD_HEADLESS"), default=True)
    timeout_raw = (env.get("COURSE_DOWNLOAD_GOTO_TIMEOUT_MS") or "").strip()
    goto_timeout_ms = int(timeout_raw) if timeout_raw.isdigit() else 60000
    return CourseBrowserDownloadConfig(
        headless=headless,
        goto_timeout_ms=goto_timeout_ms,
    )


def load_course_download_prep(code_dir: Path) -> CourseDownloadPreparer | None:
    config = CourseDownloadPrepLoader.load(code_dir)
    if not config.enabled:
        return None
    return CourseDownloadPreparer(config)
