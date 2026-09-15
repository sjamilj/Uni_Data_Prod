"""Exclude courses by URL path, catalogue link text, or course-type label.

Used at scrape (COURSE_EXCLUDE_LINK_TEXT_PATTERNS + URL patterns), download/clean,
and LLM index build.
"""

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
_MODE_MARKDOWN_RE = re.compile(r"^\-\s+\*\*Mode:\*\*\s*(.+)\s*$", re.M | re.I)
_STUDY_MODE_HEADINGS = frozenset({"study mode", "mode"})


class CourseTypePatternMatcher:
    """Parse .env lists and match course-type / URL exclusion patterns."""

    @staticmethod
    def parse_env_list(value: str | None) -> list[str]:
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

    @staticmethod
    def pattern_matches(actual: str, pattern: str) -> bool:
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


class CourseTypeExtractor:
    """Extract course type labels from HTML or markdown."""

    @staticmethod
    def from_html(html: str, *, selectors: list[str] | None = None) -> str | None:
        soup = BeautifulSoup(html, "html.parser")
        for selector in selectors or list(DEFAULT_COURSE_TYPE_SELECTORS):
            node = soup.select_one(selector.strip())
            if not node:
                continue
            text = node.get_text(" ", strip=True)
            if text:
                return text
        return None

    @staticmethod
    def from_markdown(markdown: str) -> str | None:
        match = _COURSE_TYPE_MARKDOWN_RE.search(markdown)
        if not match:
            return None
        text = match.group(1).strip()
        return text or None

    @staticmethod
    def from_markdown_mode(markdown: str) -> str | None:
        match = _MODE_MARKDOWN_RE.search(markdown)
        if not match:
            return None
        text = match.group(1).strip()
        return text or None

    @staticmethod
    def _banner_detail_value(detail) -> str:
        button = detail.select_one(".dropdown-button")
        if button:
            return button.get_text(" ", strip=True)
        option = detail.select_one(".optionText")
        if option:
            return option.get_text(" ", strip=True)
        value = detail.select_one("span.value")
        if value:
            return value.get_text(" ", strip=True)
        heading = detail.select_one(".heading")
        text = detail.get_text(" ", strip=True)
        if heading:
            label = heading.get_text(" ", strip=True)
            if text.startswith(label):
                text = text[len(label) :].strip()
        return text

    @staticmethod
    def from_html_study_mode(html: str) -> str | None:
        soup = BeautifulSoup(html, "html.parser")
        banner = soup.select_one(".course-details-banner")
        if not banner:
            return None
        for detail in banner.select(".detail"):
            heading = detail.select_one(".heading")
            if not heading:
                continue
            label = heading.get_text(" ", strip=True).casefold()
            if label not in _STUDY_MODE_HEADINGS:
                continue
            text = CourseTypeExtractor._banner_detail_value(detail).strip()
            if text:
                return text
        return None


@dataclass
class CourseTypeFilter:
    exclude_course_types: list[str]
    exclude_url_patterns: list[str]
    exclude_link_text_patterns: list[str]
    course_type_selectors: list[str]

    @classmethod
    def from_code_dir(cls, code_dir: Path) -> CourseTypeFilter:
        from scrape_course_urls import load_env_file

        env = load_env_file(code_dir / ENV_FILE)
        selectors = CourseTypePatternMatcher.parse_env_list(env.get("COURSE_TYPE_HTML_SELECTORS"))
        return cls(
            exclude_course_types=CourseTypePatternMatcher.parse_env_list(
                env.get("COURSE_EXCLUDE_COURSE_TYPES")
            ),
            exclude_url_patterns=CourseTypePatternMatcher.parse_env_list(
                env.get("COURSE_EXCLUDE_URL_PATTERNS")
            ),
            exclude_link_text_patterns=CourseTypePatternMatcher.parse_env_list(
                env.get("COURSE_EXCLUDE_LINK_TEXT_PATTERNS")
            ),
            course_type_selectors=selectors or list(DEFAULT_COURSE_TYPE_SELECTORS),
        )

    @property
    def enabled(self) -> bool:
        return bool(
            self.exclude_course_types
            or self.exclude_url_patterns
            or self.exclude_link_text_patterns
        )

    def link_text_is_excluded(self, text: str | None) -> bool:
        if not text or not self.exclude_link_text_patterns:
            return False
        for pattern in self.exclude_link_text_patterns:
            if CourseTypePatternMatcher.pattern_matches(text, pattern):
                return True
        return False

    def prune_url_catalogue(self, all_urls: set[str], url_levels) -> int:
        """Remove excluded URLs from scrape sets and UrlLevelMap (mutates in place)."""
        from study_level import normalize_url

        removed = 0
        for url in list(all_urls):
            if not self.url_is_excluded(url):
                continue
            all_urls.discard(url)
            removed += 1
            for key in (url, normalize_url(url)):
                url_levels.levels.pop(key, None)
                url_levels.course_names.pop(key, None)
        return removed

    def url_is_excluded(self, url: str | None) -> bool:
        if not url or not self.exclude_url_patterns:
            return False
        path = urlparse(url).path.casefold()
        for pattern in self.exclude_url_patterns:
            if CourseTypePatternMatcher.pattern_matches(path, pattern):
                return True
        return False

    def course_type_is_excluded(self, course_type: str | None) -> bool:
        if not course_type or not self.exclude_course_types:
            return False
        for pattern in self.exclude_course_types:
            if CourseTypePatternMatcher.pattern_matches(course_type, pattern):
                return True
        return False

    def should_exclude_html(self, html: str, *, url: str | None = None) -> bool:
        if not self.enabled:
            return False
        if self.url_is_excluded(url):
            return True
        course_type = CourseTypeExtractor.from_html(
            html,
            selectors=self.course_type_selectors,
        )
        if self.course_type_is_excluded(course_type):
            return True
        study_mode = CourseTypeExtractor.from_html_study_mode(html)
        return self.course_type_is_excluded(study_mode)

    def should_exclude_markdown(self, markdown: str, *, url: str | None = None) -> bool:
        if not self.enabled:
            return False
        if self.url_is_excluded(url):
            return True
        course_type = CourseTypeExtractor.from_markdown(markdown)
        if course_type and self.course_type_is_excluded(course_type):
            return True
        mode = CourseTypeExtractor.from_markdown_mode(markdown)
        return self.course_type_is_excluded(mode)


# Backward-compatible aliases
_parse_env_list = CourseTypePatternMatcher.parse_env_list
_pattern_matches = CourseTypePatternMatcher.pattern_matches
extract_course_type_from_html = CourseTypeExtractor.from_html
extract_course_type_from_markdown = CourseTypeExtractor.from_markdown
extract_study_mode_from_html = CourseTypeExtractor.from_html_study_mode
extract_mode_from_markdown = CourseTypeExtractor.from_markdown_mode
