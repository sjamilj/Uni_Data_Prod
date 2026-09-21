"""AJAX / in-page pagination for course search listings (no ?page= URL)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

LISTING_PAGINATION_MODE_URL = "url"
LISTING_PAGINATION_MODE_AJAX_CLICK = "ajax_click"
# Reserved for Vue/Next-button listings (e.g. Kingston); not the same as ajax_click.
LISTING_PAGINATION_MODE_CLICK = "click"
VALID_LISTING_PAGINATION_MODES = {
    LISTING_PAGINATION_MODE_URL,
    LISTING_PAGINATION_MODE_AJAX_CLICK,
    LISTING_PAGINATION_MODE_CLICK,
}

# University of Bedfordshire / Umbraco CourseSearchResult markup
UMBRACO_COURSE_SEARCH_META_RE = re.compile(
    r"Showing\s+page\s*<strong>\s*(\d+)\s*</strong>\s+of\s*<strong>\s*(\d+)\s*</strong>"
    r".*?"
    r"Courses\s*<strong>\s*(\d+)\s*</strong>\s*-\s*<strong>\s*(\d+)\s*</strong>\s+of\s*<strong>\s*(\d+)\s*</strong>",
    re.I | re.DOTALL,
)

DO_COURSE_SEARCH_PATH_FRAGMENT = "DoCourseSearch"


# University of Bedfordshire — CourseLevels checkbox ids (stable in saved listing HTML)
BEDS_COURSE_LEVEL_CHECKBOX = {
    "undergraduate": "Undergraduate_313909",
    "postgraduate": "Postgraduate_313908",
    "postgraduate_research": "Postgraduate Research Scheme_439549",
    "foundation": "Foundation Degrees_-1",
}

BEDS_STUDY_MODE_CHECKBOX = {
    "full_time": "Full-time_614",
    "part_time": "Part-time_740",
}

# CourseVariants (Level accordion) — not the same as Foundation Degrees course level
BEDS_COURSE_VARIANT_CHECKBOX = {
    "with_foundation_year": "with Foundation Year_1519",
    "with_professional_practice_year": "with Professional Practice Year_1518",
}

UMBRACO_COURSE_SEARCH_FILTER_JS = """
(args) => {
  const keepLevels = new Set(args.keepLevels || []);
  const keepModes = new Set(args.keepModes || []);
  const keepVariants = new Set(args.keepVariants || []);
  const form = document.querySelector('#course-search-form');
  if (!form) return false;
  let changed = false;
  if (keepLevels.size) {
    form.querySelectorAll('input[type="checkbox"][name*="CourseLevels"]').forEach((cb) => {
      const want = keepLevels.has(cb.id);
      if (cb.checked !== want) {
        cb.checked = want;
        changed = true;
      }
    });
  }
  if (keepModes.size) {
    form.querySelectorAll('input[type="checkbox"][name*="Modes"]').forEach((cb) => {
      const want = keepModes.has(cb.id);
      if (cb.checked !== want) {
        cb.checked = want;
        changed = true;
      }
    });
  }
  form.querySelectorAll('input[type="checkbox"][name*="CourseVariants"]').forEach((cb) => {
    const want = keepVariants.size ? keepVariants.has(cb.id) : false;
    if (cb.checked !== want) {
      cb.checked = want;
      changed = true;
    }
  });
  const pageInput = document.querySelector('#current-page');
  if (pageInput) pageInput.value = '1';
  return changed;
}
"""

UMBRACO_SUBMIT_COURSE_SEARCH_JS = """
() => {
  if (typeof submitSearch === 'function') submitSearch();
}
"""

# Backwards-compatible alias
UMBRACO_LEVEL_FILTER_JS = UMBRACO_COURSE_SEARCH_FILTER_JS


@dataclass(frozen=True)
class ListingAjaxSettings:
    """Playwright selectors for LISTING_PAGINATION_MODE=ajax_click."""

    wait_selector: str = "a.search-results__title__link"
    page_button_selector_template: str = '.pagination button.page-link[data-page="{page}"]'
    results_container_selector: str = "#course-search-results"
    level_checkbox_ids: tuple[str, ...] = ()
    mode_checkbox_ids: tuple[str, ...] = ()
    variant_checkbox_ids: tuple[str, ...] = ()


def parse_umbraco_course_search_meta(html: str) -> tuple[int | None, int | None, int | None, int | None, int | None]:
    """Return (current_page, total_pages, course_start, course_end, total_courses)."""
    match = UMBRACO_COURSE_SEARCH_META_RE.search(html)
    if not match:
        return None, None, None, None, None
    return (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3)),
        int(match.group(4)),
        int(match.group(5)),
)


def listing_page_resume_key(
    base_listing_url: str,
    page_index: int,
    *,
    scope: str = "",
) -> str:
    """Stable progress key when the browser URL does not change between pages."""
    base = base_listing_url.split("#")[0].split("?")[0].rstrip("/")
    scope_tag = (scope or "").strip().lower().replace(" ", "_")
    if scope_tag:
        return f"{base}#scope={scope_tag}&page={page_index}"
    return f"{base}#page={page_index}"


def page_button_selector(settings: ListingAjaxSettings, page_index: int) -> str:
    return settings.page_button_selector_template.format(page=page_index)


def beds_listing_level_checkbox_ids(listing_url: str, scope: str) -> list[str]:
    """Map a degree-scoped listing URL (or pipeline scope) to one CourseLevels checkbox id."""
    path = urlparse(listing_url).path.lower().rstrip("/")
    scope_key = (scope or "").strip().lower().replace(" ", "_")

    if path.endswith("/postgraduate") or scope_key == "postgraduate":
        return [BEDS_COURSE_LEVEL_CHECKBOX["postgraduate"]]
    if "undergraduate" in path or scope_key == "undergraduate":
        return [BEDS_COURSE_LEVEL_CHECKBOX["undergraduate"]]
    if path.endswith("/foundation-degrees") or path.endswith("/foundationdegrees"):
        return [BEDS_COURSE_LEVEL_CHECKBOX["foundation"]]
    if "research" in path or scope_key in {"postgraduate_research", "postgraduate_research_scheme"}:
        return [BEDS_COURSE_LEVEL_CHECKBOX["postgraduate_research"]]
    return []


def resolve_ajax_level_checkbox_ids(
    listing_url: str,
    scope: str,
    configured: tuple[str, ...],
) -> list[str]:
    if configured:
        return list(configured)
    return beds_listing_level_checkbox_ids(listing_url, scope)


def resolve_ajax_mode_checkbox_ids(configured: tuple[str, ...]) -> list[str]:
    if configured:
        return list(configured)
    return [BEDS_STUDY_MODE_CHECKBOX["full_time"]]


def resolve_ajax_variant_checkbox_ids(configured: tuple[str, ...]) -> list[str]:
    if configured:
        return list(configured)
    return []


def beds_mode_checkbox_ids(mode_key: str) -> list[str]:
    key = (mode_key or "").strip().lower().replace("-", "_").replace(" ", "_")
    checkbox = BEDS_STUDY_MODE_CHECKBOX.get(key)
    return [checkbox] if checkbox else []
