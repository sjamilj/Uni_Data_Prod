"""Canterbury Christ Church University course page download hooks.

Shared pipeline calls prepare_course_page_download() before saving HTML so
entry requirements show the International tab (not UK-only defaults).
"""

from __future__ import annotations

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


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

    for selector in (
        'button[type="button"].tab-closed:has-text("International")',
        "button.tab-closed:has-text('International')",
        'button:has-text("International")',
    ):
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


def prepare_course_page_download(page, url: str) -> None:
    """Click International tab before HTML capture."""
    _ = url
    if select_international_tab(page):
        print("    International tab selected", flush=True)
    else:
        print("    Warning: International tab not found - saving default view", flush=True)
