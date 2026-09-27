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
_DURATION_MARKDOWN_RE = re.compile(r"^\*\*Duration:\*\*\s*(.+)\s*$", re.M | re.I)
_STUDY_MODE_MARKDOWN_RE = re.compile(
    r"^-\s*\*\*Study mode:\*\*\s*(.+)\s*$",
    re.M | re.I,
)
_FULL_TIME_MODE_RE = re.compile(r"\bfull[-\s]?time\b", re.I)
_PART_TIME_MODE_RE = re.compile(r"\bpart[-\s]?time\b", re.I)


def study_mode_is_part_time_only(text: str) -> bool:
    """True when text describes part-time study but not full-time (dual-mode courses are kept)."""
    if not text or not text.strip():
        return False
    if not _PART_TIME_MODE_RE.search(text):
        return False
    return not _FULL_TIME_MODE_RE.search(text)


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
    def study_options_from_plaintext(text: str) -> str | None:
        lines = [ln.strip() for ln in text.splitlines()]
        for index, line in enumerate(lines):
            if line.casefold() != "study options":
                continue
            value_index = index + 1
            while value_index < len(lines) and not lines[value_index]:
                value_index += 1
            if value_index < len(lines):
                return lines[value_index]
        return None

    @staticmethod
    def study_options_from_markdown(markdown: str) -> str | None:
        for heading in ("## Key course details", "## Key course information"):
            marker = heading
            if marker not in markdown:
                continue
            _, tail = markdown.split(marker, 1)
            next_section = re.search(r"\n## ", tail)
            body = tail[: next_section.start()] if next_section else tail
            value = CourseTypeExtractor.study_options_from_plaintext(body)
            if value:
                return value
        return CourseTypeExtractor.study_options_from_plaintext(markdown)

    @staticmethod
    def study_options_from_html(html: str) -> str | None:
        soup = BeautifulSoup(html, "html.parser")
        root = soup.select_one("#key-course-details") or soup.body or soup
        if not root:
            return None
        return CourseTypeExtractor.study_options_from_plaintext(
            root.get_text("\n", strip=True),
        )

    @staticmethod
    def _normalize_lsbu_mode_cell(text: str) -> str:
        cleaned = re.sub(r"^Mode\s*", "", text.strip(), flags=re.I)
        return cleaned.strip()

    @staticmethod
    def study_modes_from_lsbu_html(html: str) -> list[str]:
        """LSBU overview table: Mode | Duration | Start date | Application code."""
        soup = BeautifulSoup(html, "html.parser")
        modes: list[str] = []
        for row in soup.select("table.overview_course_info_table tr.overview_course_info_table__values"):
            cells = row.find_all("td")
            if not cells:
                continue
            mode = CourseTypeExtractor._normalize_lsbu_mode_cell(
                cells[0].get_text(" ", strip=True),
            )
            if mode:
                modes.append(mode)
        return modes

    @staticmethod
    def study_mode_from_lsbu_hero_icons(html: str) -> str | None:
        soup = BeautifulSoup(html, "html.parser")
        for component in soup.select(".hero-banner-courses__icon-components .icon-component"):
            header = component.select_one(".icon-component__header")
            description = component.select_one(".icon-component__description")
            if header is None or description is None:
                continue
            if header.get_text(" ", strip=True).casefold() != "study":
                continue
            value = description.get_text(" ", strip=True)
            return value or None
        return None

    @staticmethod
    def study_modes_from_lsbu_markdown(markdown: str) -> list[str]:
        modes: list[str] = []
        for row in re.finditer(
            r"^\|\s*Mode\s*\|\s*([^\n|]+)",
            markdown,
            re.I | re.M,
        ):
            modes.append(row.group(1).strip())
        if modes:
            return modes
        for match in re.finditer(
            r"(?:^|\n)Mode\s*\n+([^\n]+)",
            markdown,
            re.I,
        ):
            value = match.group(1).strip()
            if value.casefold() not in {"duration", "start date", "application code"}:
                modes.append(value)
        return modes


@dataclass
class CourseTypeFilter:
    exclude_course_types: list[str]
    exclude_url_patterns: list[str]
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

    def excludes_part_time_study_modes(self) -> bool:
        return self.course_type_is_excluded("part-time")

    def _exclude_part_time_only_study_mode(self, study_text: str | None) -> bool:
        if not self.excludes_part_time_study_modes() or not study_text:
            return False
        return study_mode_is_part_time_only(study_text)

    def _exclude_lsbu_part_time_only_modes(self, modes: list[str]) -> bool:
        if not self.excludes_part_time_study_modes() or not modes:
            return False
        return all(study_mode_is_part_time_only(mode) for mode in modes)

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
        study = CourseTypeExtractor.study_options_from_html(html)
        if self._exclude_part_time_only_study_mode(study):
            return True
        hero_study = CourseTypeExtractor.study_mode_from_lsbu_hero_icons(html)
        if self._exclude_part_time_only_study_mode(hero_study):
            return True
        return self._exclude_lsbu_part_time_only_modes(
            CourseTypeExtractor.study_modes_from_lsbu_html(html),
        )

    def should_exclude_markdown(self, markdown: str, *, url: str | None = None) -> bool:
        if not self.enabled:
            return False
        if self.url_is_excluded(url):
            return True
        course_type = CourseTypeExtractor.from_markdown(markdown)
        if course_type and self.course_type_is_excluded(course_type):
            return True
        duration_match = _DURATION_MARKDOWN_RE.search(markdown)
        if duration_match and self._exclude_part_time_only_study_mode(duration_match.group(1)):
            return True
        study_mode_match = _STUDY_MODE_MARKDOWN_RE.search(markdown)
        if study_mode_match and self._exclude_part_time_only_study_mode(
            study_mode_match.group(1),
        ):
            return True
        study = CourseTypeExtractor.study_options_from_markdown(markdown)
        if self._exclude_part_time_only_study_mode(study):
            return True
        return self._exclude_lsbu_part_time_only_modes(
            CourseTypeExtractor.study_modes_from_lsbu_markdown(markdown),
        )


# Backward-compatible aliases
_parse_env_list = CourseTypePatternMatcher.parse_env_list
_pattern_matches = CourseTypePatternMatcher.pattern_matches
extract_course_type_from_html = CourseTypeExtractor.from_html
extract_course_type_from_markdown = CourseTypeExtractor.from_markdown
