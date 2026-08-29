"""Exclude short-course, CPD, and part-time courses from download/clean pipeline."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

ENV_FILE = ".env"

DEFAULT_COURSE_TYPE_SELECTORS = (
    ".field--name-field-bbd-course-type .field--item",
    ".field--name-field-course-type .field--item",
    "[class*='course-type'] .field--item",
)

_COURSE_TYPE_MARKDOWN_RE = re.compile(r"^\*\*Course type:\*\*\s*(.+)\s*$", re.M | re.I)


def _parse_env_list(value: str | None) -> list[str]:
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


def _pattern_matches(actual: str, pattern: str) -> bool:
    actual_l = actual.strip().casefold()
    pattern_l = pattern.strip().casefold()
    if not pattern_l:
        return False
    if pattern_l.startswith("*") and pattern_l.endswith("*") and len(pattern_l) > 1:
        needle = pattern_l[1:-1]
        return bool(needle) and needle in actual_l
    if pattern_l.endswith("*"):
        return actual_l.startswith(pattern_l[:-1])
    if pattern_l.startswith("*"):
        return actual_l.endswith(pattern_l[1:])
    return actual_l == pattern_l


def extract_course_type_from_html(
    html: str,
    *,
    selectors: list[str] | None = None,
) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    for selector in selectors or list(DEFAULT_COURSE_TYPE_SELECTORS):
        node = soup.select_one(selector.strip())
        if not node:
            continue
        text = node.get_text(" ", strip=True)
        if text:
            return text
    return None


def extract_course_type_from_markdown(markdown: str) -> str | None:
    match = _COURSE_TYPE_MARKDOWN_RE.search(markdown)
    if not match:
        return None
    text = match.group(1).strip()
    return text or None


@dataclass
class CourseTypeFilter:
    exclude_course_types: list[str]
    exclude_url_patterns: list[str]
    course_type_selectors: list[str]

    @classmethod
    def from_code_dir(cls, code_dir: Path) -> CourseTypeFilter:
        from scrape_course_urls import load_env_file

        env = load_env_file(code_dir / ENV_FILE)
        selectors = _parse_env_list(env.get("COURSE_TYPE_HTML_SELECTORS"))
        return cls(
            exclude_course_types=_parse_env_list(env.get("COURSE_EXCLUDE_COURSE_TYPES")),
            exclude_url_patterns=_parse_env_list(env.get("COURSE_EXCLUDE_URL_PATTERNS")),
            course_type_selectors=selectors or list(DEFAULT_COURSE_TYPE_SELECTORS),
        )

    @property
    def enabled(self) -> bool:
        return bool(self.exclude_course_types or self.exclude_url_patterns)

    def url_is_excluded(self, url: str | None) -> bool:
        if not url or not self.exclude_url_patterns:
            return False
        path = urlparse(url).path.casefold()
        for pattern in self.exclude_url_patterns:
            if _pattern_matches(path, pattern):
                return True
        return False

    def course_type_is_excluded(self, course_type: str | None) -> bool:
        if not course_type or not self.exclude_course_types:
            return False
        for pattern in self.exclude_course_types:
            if _pattern_matches(course_type, pattern):
                return True
        return False

    def should_exclude_html(self, html: str, *, url: str | None = None) -> bool:
        if not self.enabled:
            return False
        if self.url_is_excluded(url):
            return True
        course_type = extract_course_type_from_html(
            html,
            selectors=self.course_type_selectors,
        )
        return self.course_type_is_excluded(course_type)

    def should_exclude_markdown(self, markdown: str, *, url: str | None = None) -> bool:
        if not self.enabled:
            return False
        if self.url_is_excluded(url):
            return True
        course_type = extract_course_type_from_markdown(markdown)
        if course_type:
            return self.course_type_is_excluded(course_type)
        return False
