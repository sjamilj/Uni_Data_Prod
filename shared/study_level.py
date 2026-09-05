"""Study-level tagging for scrape CSVs, clean folders, and LLM extract."""

from __future__ import annotations

import csv
import json
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

DEGREE_SCOPES = (
    "UNDERGRADUATE",
    "POSTGRADUATE",
    "POSTGRADUATE_RESEARCH",
    "FOUNDATION",
)

STUDY_LEVELS = (
    "undergraduate",
    "postgraduate",
    "postgraduate_research",
    "foundation",
    "other",
)

SCOPE_TO_LEVEL = {
    "UNDERGRADUATE": "undergraduate",
    "POSTGRADUATE": "postgraduate",
    "POSTGRADUATE_RESEARCH": "postgraduate_research",
    "FOUNDATION": "foundation",
}

LEVEL_CSV_NAMES = {
    "undergraduate": "undergraduate_course_urls.csv",
    "postgraduate": "postgraduate_course_urls.csv",
    "postgraduate_research": "postgraduate_research_course_urls.csv",
    "foundation": "foundation_course_urls.csv",
    "other": "other_course_urls.csv",
}

ENV_PATTERN_KEYS = {
    "undergraduate": "UNDERGRADUATE_URL_PATTERNS",
    "postgraduate": "POSTGRADUATE_URL_PATTERNS",
    "postgraduate_research": "POSTGRADUATE_RESEARCH_URL_PATTERNS",
    "foundation": "FOUNDATION_URL_PATTERNS",
}

LEVEL_MATCH_ORDER = (
    "foundation",
    "postgraduate_research",
    "postgraduate",
    "undergraduate",
)

LEVEL_CSV_COLUMNS = ("course_url", "study_level", "source_scope")

PRESETUP_SAMPLE_JSON = "presetup_sample.json"
PRESETUP_SAMPLE_SIZE = 10
SCRAPE_PRESETUP_SAMPLE_JSON = "presetup_scrape_sample.json"
SCRAPE_PRESETUP_PER_LEVEL = 5
PRESETUP_URLS_CSV = "presetup_urls.csv"
PRESETUP_SCRAPE_PROGRESS_JSON = "presetup_scrape_progress.json"
CLEAN_COURSES_SUBDIR = "courses"
PRESETUP_CLEAN_SUBDIR = "pre_setup_course"
PRESETUP_EXTRACT_SUBDIR = "pre_setup_course_extracted"

LEVEL_ALIASES = {
    "ug": "undergraduate",
    "under": "undergraduate",
    "undergrad": "undergraduate",
    "undergraduate": "undergraduate",
    "pg": "postgraduate",
    "post": "postgraduate",
    "postgrad": "postgraduate",
    "postgraduate": "postgraduate",
    "pgr": "postgraduate_research",
    "research": "postgraduate_research",
    "postgraduate_research": "postgraduate_research",
    "foundation": "foundation",
    "other": "other",
}

EXECUTE_LEVEL_ORDER = (
    "foundation",
    "undergraduate",
    "postgraduate",
    "postgraduate_research",
    "other",
)

_DEFAULT_FOUNDATION_RE = re.compile(r"foundation", re.I)
_DEFAULT_RESEARCH_RE = re.compile(
    r"courses-phd|(?:^|[-_/])(?:phd|mres)(?:[-_/]|$)",
    re.I,
)
_DEFAULT_POSTGRADUATE_RE = re.compile(
    r"(?:^|[-_/])(?:msc|mba|llm|pgdip|pgcert|ma)(?:[-_/]|$)",
    re.I,
)

_INTAKE_YEAR_SUFFIX_RE = re.compile(r"-(\d{4})-(\d{2})$")
_INTAKE_YEAR_FOLDER_RE = re.compile(r"^\d{4} - \d{4}$")


def scope_to_level(scope: str | None) -> str:
    raw = (scope or "").strip()
    if not raw:
        return ""
    key = raw.replace("-", "_").replace(" ", "_").upper()
    if key in SCOPE_TO_LEVEL:
        return SCOPE_TO_LEVEL[key]
    lower = raw.replace("-", "_").replace(" ", "_").lower()
    if lower in STUDY_LEVELS:
        return lower
    return ""


def folder_for_level(study_level: str | None) -> str:
    level = (study_level or "").strip().lower().replace("-", "_")
    if level in STUDY_LEVELS and level != "other":
        return level
    if level == "other":
        return "other"
    return "undergraduate"


def llm_course_level(study_level: str | None) -> str:
    """Map folder/scrape level onto the three LLM entry/english buckets."""
    level = (study_level or "").strip().lower().replace("-", "_")
    if level in {"foundation"}:
        return "foundation"
    if level in {"postgraduate", "postgraduate_research"}:
        return "postgraduate"
    return "undergraduate"


def extraction_resume_key(study_level: str | None, slug: str) -> str:
    return f"{folder_for_level(study_level)}::{slug}"


def is_resume_completed(completed: set[str], *, study_level: str | None, slug: str) -> bool:
    key = extraction_resume_key(study_level, slug)
    return key in completed


@dataclass
class StudyLevelClassifier:
    """Classify a course URL into undergraduate / postgraduate / foundation / research."""

    custom_patterns: dict[str, list[re.Pattern[str]]] = field(default_factory=dict)

    @property
    def has_custom_patterns(self) -> bool:
        return any(self.custom_patterns.values())

    @classmethod
    def from_env_lists(cls, pattern_lists: dict[str, list[str]]) -> StudyLevelClassifier:
        compiled: dict[str, list[re.Pattern[str]]] = {}
        for level, raw_patterns in pattern_lists.items():
            compiled[level] = []
            for pattern in raw_patterns:
                try:
                    compiled[level].append(re.compile(pattern, re.I))
                except re.error:
                    compiled[level].append(re.compile(re.escape(pattern), re.I))
        return cls(custom_patterns=compiled)

    @classmethod
    def from_env_file(cls, env: object, env_path: Path | None = None) -> StudyLevelClassifier:
        pattern_lists: dict[str, list[str]] = {}
        get_list = getattr(env, "get_list", None)
        if callable(get_list):
            for level, key in ENV_PATTERN_KEYS.items():
                pattern_lists[level] = get_list(key)
        else:
            getter = getattr(env, "get", None)
            for level, key in ENV_PATTERN_KEYS.items():
                raw = getter(key, "") if callable(getter) else ""
                pattern_lists[level] = [
                    item.strip()
                    for item in re.split(r"[\n;]+", str(raw or ""))
                    if item.strip() and not item.strip().startswith("#")
                ]
        _ = env_path
        return cls.from_env_lists(pattern_lists)

    @classmethod
    def from_code_dir(cls, code_dir: Path) -> StudyLevelClassifier:
        from scrape_course_urls import ENV_FILE, EnvFile

        return cls.from_env_file(EnvFile(code_dir / ENV_FILE), code_dir / ENV_FILE)

    def classify(self, url: str, *, course_name: str = "") -> str:
        path = urlparse(url).path
        haystack = f"{url}\n{path}\n{course_name}"
        if self.has_custom_patterns:
            for level in LEVEL_MATCH_ORDER:
                for pattern in self.custom_patterns.get(level, []):
                    if pattern.search(path) or pattern.search(haystack):
                        return level
            return "other"
        if _DEFAULT_FOUNDATION_RE.search(haystack):
            return "foundation"
        if _DEFAULT_RESEARCH_RE.search(path) or _DEFAULT_RESEARCH_RE.search(url):
            return "postgraduate_research"
        if _DEFAULT_POSTGRADUATE_RE.search(path):
            return "postgraduate"
        return "undergraduate"


@dataclass
class UrlLevelMap:
    """url -> {study_level: source_scope}."""

    levels: dict[str, dict[str, str]] = field(default_factory=dict)

    def add(self, url: str, study_level: str, source_scope: str = "") -> None:
        url = (url or "").strip()
        level = (study_level or "").strip()
        if not url or not level:
            return
        bucket = self.levels.setdefault(url, {})
        if level not in bucket or source_scope:
            bucket[level] = source_scope or bucket.get(level, "")

    def add_many(self, urls: list[str] | set[str], study_level: str, source_scope: str = "") -> None:
        for url in urls:
            self.add(url, study_level, source_scope)

    def tag_urls(
        self,
        urls: list[str] | set[str],
        *,
        scope: str = "",
        classifier: StudyLevelClassifier | None = None,
        source_scope: str = "",
    ) -> None:
        classifier = classifier or StudyLevelClassifier()
        level_from_scope = scope_to_level(scope)
        label = source_scope or scope or "ALL_COURSE"
        if classifier.has_custom_patterns:
            for url in urls:
                classified = classifier.classify(url)
                if classified == "other" and level_from_scope:
                    level = level_from_scope
                else:
                    level = classified
                self.add(url, level, label)
            return
        if level_from_scope:
            self.add_many(urls, level_from_scope, label)
            return
        for url in urls:
            self.add(url, classifier.classify(url), label)

    def urls(self) -> list[str]:
        return sorted(self.levels)

    def levels_for(self, url: str) -> list[str]:
        url = (url or "").strip()
        if not url:
            return []
        direct = list(self.levels.get(url, {}))
        if direct:
            return direct
        normalized = normalize_url(url)
        if normalized != url:
            direct = list(self.levels.get(normalized, {}))
            if direct:
                return direct
        path_key = url_path_key(url)
        if not path_key:
            return []
        for known_url, levels in self.levels.items():
            if url_path_key(known_url) == path_key:
                return list(levels)
        return []

    def records(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for url in sorted(self.levels):
            for level, source_scope in sorted(self.levels[url].items()):
                rows.append(
                    {
                        "course_url": url,
                        "study_level": level,
                        "source_scope": source_scope,
                    }
                )
        return rows

    def to_progress(self) -> dict[str, dict[str, str]]:
        return {url: dict(levels) for url, levels in self.levels.items()}

    @classmethod
    def from_progress(cls, payload: object) -> UrlLevelMap:
        mapping = cls()
        if isinstance(payload, dict):
            for url, levels in payload.items():
                if isinstance(levels, dict):
                    for level, source_scope in levels.items():
                        mapping.add(str(url), str(level), str(source_scope or ""))
                elif isinstance(levels, list):
                    for level in levels:
                        mapping.add(str(url), str(level), "")
        return mapping

    def merge(self, other: UrlLevelMap) -> None:
        for url, levels in other.levels.items():
            for level, source_scope in levels.items():
                self.add(url, level, source_scope)


def read_presetup_urls_csv(output_dir: Path) -> list[dict[str, str]]:
    path = output_dir / PRESETUP_URLS_CSV
    if not path.is_file():
        return []
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            url = (row.get("course_url") or row.get("url") or "").strip()
            if not url:
                continue
            rows.append(
                {
                    "course_url": url,
                    "study_level": (row.get("study_level") or "").strip(),
                    "source_scope": (row.get("source_scope") or "PRESETUP_SCRAPE").strip(),
                }
            )
    return rows


def load_presetup_url_levels(output_dir: Path) -> UrlLevelMap:
    mapping = UrlLevelMap()
    for row in read_presetup_urls_csv(output_dir):
        mapping.add(row["course_url"], row["study_level"], row.get("source_scope") or "PRESETUP_SCRAPE")
    return mapping


def count_presetup_scrape_urls(output_dir: Path) -> int:
    return len(read_presetup_urls_csv(output_dir))


def select_presetup_download_courses(
    output_dir: Path,
    *,
    sample_size: int = PRESETUP_SAMPLE_SIZE,
    seed: int | None = None,
) -> tuple[list[dict[str, str]], int, str]:
    """Pick URLs for presetup download/clean.

    When presetup_urls.csv exists, use every URL from that file (no subsampling).
    Otherwise stratified sample from the full catalogue.
    Returns (courses, seed, source_label).
    """
    presetup_scrape = read_presetup_urls_csv(output_dir)
    if presetup_scrape:
        scrape_sample = PresetupSampler.load_presetup_scrape_sample(output_dir)
        used_seed = seed if seed is not None else int(scrape_sample.get("seed") or 0)
        return presetup_scrape, used_seed, PRESETUP_URLS_CSV

    mapping = load_url_levels(output_dir)
    if not mapping.urls():
        return [], 0, ""
    used_seed = seed if seed is not None else random.randrange(1, 2**31)
    courses = PresetupSampler.sample_urls_stratified(mapping, n=sample_size, seed=used_seed)
    return courses, used_seed, "full_catalogue"


def presetup_download_sample_stale(output_dir: Path, existing_urls: list[str]) -> bool:
    """True when presetup_urls.csv exists and differs from presetup_sample.json."""
    scrape_rows = read_presetup_urls_csv(output_dir)
    if not scrape_rows:
        return False
    scrape_set = {
        PresetupSampler.normalize_url(row["course_url"]) for row in scrape_rows if row.get("course_url")
    }
    existing_set = {PresetupSampler.normalize_url(url) for url in existing_urls if url}
    return scrape_set != existing_set


def write_level_csvs(output_dir: Path, url_levels: UrlLevelMap) -> None:
    records_by_level: dict[str, list[dict[str, str]]] = {level: [] for level in LEVEL_CSV_NAMES}
    for record in url_levels.records():
        level = record["study_level"]
        records_by_level.setdefault(level, []).append(record)

    for level, filename in LEVEL_CSV_NAMES.items():
        path = output_dir / filename
        rows = records_by_level.get(level, [])
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(LEVEL_CSV_COLUMNS), quoting=csv.QUOTE_ALL)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)


def write_presetup_urls_csv(output_dir: Path, courses: list[dict[str, str]]) -> Path:
    """Write presetup scrape sample URLs with study_level to presetup_urls.csv."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / PRESETUP_URLS_CSV
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(LEVEL_CSV_COLUMNS),
            quoting=csv.QUOTE_ALL,
        )
        writer.writeheader()
        for row in courses:
            writer.writerow(
                {
                    "course_url": row.get("course_url", ""),
                    "study_level": row.get("study_level", ""),
                    "source_scope": row.get("source_scope") or "PRESETUP_SCRAPE",
                }
            )
    return path


def read_level_csvs(output_dir: Path) -> UrlLevelMap:
    mapping = UrlLevelMap()
    for filename in LEVEL_CSV_NAMES.values():
        path = output_dir / filename
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                url = (row.get("course_url") or row.get("url") or "").strip()
                level = (row.get("study_level") or "").strip()
                source_scope = (row.get("source_scope") or "").strip()
                mapping.add(url, level, source_scope)
    return mapping


def url_path_key(url: str) -> str:
    """Path-only key so scraped www.aru.ac.uk URLs match saved HTML source URLs."""
    from urllib.parse import urlparse

    path = urlparse((url or "").strip()).path.rstrip("/")
    return path.lower() if path else ""


def load_url_levels(output_dir: Path) -> UrlLevelMap:
    mapping = read_level_csvs(output_dir)
    progress_path = output_dir / "scrape_progress.json"
    if progress_path.exists():
        try:
            progress = json.loads(progress_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            progress = {}
        mapping.merge(UrlLevelMap.from_progress(progress.get("url_levels")))
    return mapping


def levels_for_url(
    url: str,
    *,
    url_levels: UrlLevelMap | None = None,
    classifier: StudyLevelClassifier | None = None,
    course_name: str = "",
) -> list[str]:
    if url_levels:
        found = url_levels.levels_for(url)
        if found:
            return found
    classifier = classifier or StudyLevelClassifier()
    return [classifier.classify(url, course_name=course_name)]


def _intake_dedupe_key(
    url: str,
    *,
    url_levels: UrlLevelMap | None = None,
    classifier: StudyLevelClassifier | None = None,
) -> tuple[tuple[str, ...], str]:
    from uni_pages import course_slug_from_url

    slug = course_slug_from_url(url)
    identity = StudyLevelPathResolver.course_identity_slug(slug)
    levels = tuple(
        sorted(
            levels_for_url(
                url,
                url_levels=url_levels,
                classifier=classifier,
            )
        )
    )
    return levels, identity


def _pick_latest_intake_url(
    urls: list[str],
    *,
    url_levels: UrlLevelMap | None = None,
    classifier: StudyLevelClassifier | None = None,
) -> str:
    from uni_pages import course_slug_from_url

    return max(
        urls,
        key=lambda url: (
            StudyLevelPathResolver.intake_start_year_from_slug(
                course_slug_from_url(url)
            ),
            url.lower(),
        ),
    )


def dedupe_urls_by_latest_intake(
    urls: list[str],
    *,
    url_levels: UrlLevelMap | None = None,
    classifier: StudyLevelClassifier | None = None,
) -> tuple[list[str], list[str]]:
    """When the same course exists for multiple intake years, keep only the latest.

    Grouping is per (study_level set, course identity slug). Foundation and
    undergraduate URLs are never merged unless they share the same levels.
    """
    if len(urls) <= 1:
        return list(urls), []

    classifier = classifier or StudyLevelClassifier()
    groups: dict[tuple[tuple[str, ...], str], list[tuple[int, str]]] = {}
    for index, url in enumerate(urls):
        key = _intake_dedupe_key(
            url,
            url_levels=url_levels,
            classifier=classifier,
        )
        groups.setdefault(key, []).append((index, url))

    kept_indices: set[int] = set()
    skipped: list[str] = []
    for items in groups.values():
        if len(items) == 1:
            kept_indices.add(items[0][0])
            continue
        group_urls = [url for _index, url in items]
        winner = _pick_latest_intake_url(
            group_urls,
            url_levels=url_levels,
            classifier=classifier,
        )
        for index, url in items:
            if url == winner and index not in kept_indices:
                kept_indices.add(index)
            elif url != winner:
                skipped.append(url)

    kept = [urls[index] for index in sorted(kept_indices)]
    return kept, skipped


def dedupe_course_entries_by_latest_intake(
    entries: list[tuple[str, Path]],
    *,
    url_levels: UrlLevelMap | None = None,
    classifier: StudyLevelClassifier | None = None,
) -> tuple[list[tuple[str, Path]], list[tuple[str, Path]]]:
    """Like dedupe_urls_by_latest_intake for (course_url, html_path) catalog rows."""
    if len(entries) <= 1:
        return list(entries), []

    classifier = classifier or StudyLevelClassifier()
    groups: dict[tuple[tuple[str, ...], str], list[tuple[int, tuple[str, Path]]]] = {}
    for index, entry in enumerate(entries):
        course_url, _html_path = entry
        key = _intake_dedupe_key(
            course_url,
            url_levels=url_levels,
            classifier=classifier,
        )
        groups.setdefault(key, []).append((index, entry))

    kept_indices: set[int] = set()
    skipped: list[tuple[str, Path]] = []
    for items in groups.values():
        if len(items) == 1:
            kept_indices.add(items[0][0])
            continue
        group_urls = [course_url for _index, (course_url, _path) in items]
        winner_url = _pick_latest_intake_url(
            group_urls,
            url_levels=url_levels,
            classifier=classifier,
        )
        for index, entry in items:
            course_url, _path = entry
            if course_url == winner_url and index not in kept_indices:
                kept_indices.add(index)
            elif course_url != winner_url:
                skipped.append(entry)

    kept = [entries[index] for index in sorted(kept_indices)]
    return kept, skipped


def study_level_from_markdown(
    md_path: Path,
    meta: dict[str, str] | None = None,
    *,
    courses_dir: Path | None = None,
    course_url: str = "",
    course_name: str = "",
    classifier: StudyLevelClassifier | None = None,
) -> str:
    meta = meta or {}
    from_meta = scope_to_level(meta.get("study_level", ""))
    if from_meta:
        return from_meta
    level_folder = study_level_folder_from_path(md_path, courses_dir=courses_dir)
    normalized = level_folder.lower().replace("-", "_")
    if normalized in STUDY_LEVELS:
        return normalized
    if course_url or course_name:
        classifier = classifier or StudyLevelClassifier()
        return classifier.classify(course_url, course_name=course_name)
    return "undergraduate"


def parse_study_level(raw: str) -> str:
    key = (raw or "").strip().lower().replace(" ", "_").replace("-", "_")
    if key in LEVEL_ALIASES:
        return LEVEL_ALIASES[key]
    via_scope = scope_to_level(raw)
    if via_scope:
        return via_scope
    raise ValueError(
        f"Unknown study level {raw!r}. Expected one of: "
        f"foundation, undergraduate, postgraduate, postgraduate_research, other."
    )


def parse_study_levels(values: list[str] | None) -> list[str]:
    seen: list[str] = []
    for raw in values or []:
        level = parse_study_level(raw)
        if level not in seen:
            seen.append(level)
    return seen


class StudyLevelPathResolver:
    """Resolve study-level folder paths for clean markdown and extraction."""

    INTAKE_YEAR_SUFFIX_RE = _INTAKE_YEAR_SUFFIX_RE
    INTAKE_YEAR_FOLDER_RE = _INTAKE_YEAR_FOLDER_RE

    @staticmethod
    def intake_start_year_from_md_path(md_path: Path) -> int:
        """Start year from intake folder (e.g. '2027 - 2028') or slug suffix (-2027-28)."""
        parent = (md_path.parent.name or "").strip()
        if StudyLevelPathResolver.is_intake_year_folder(parent):
            return int(parent.split(" - ")[0].strip())
        year_folder = StudyLevelPathResolver.intake_year_folder_from_stem(md_path.stem)
        if year_folder:
            return int(year_folder.split(" - ")[0].strip())
        return 0

    @staticmethod
    def intake_year_folder_from_stem(stem: str) -> str:
        """Map slug stem suffix -2026-27 → folder name '2026 - 2027'."""
        match = _INTAKE_YEAR_SUFFIX_RE.search((stem or "").strip())
        if not match:
            return ""
        start_year = int(match.group(1))
        end_suffix = int(match.group(2))
        end_year = (start_year // 100) * 100 + end_suffix
        if end_year <= start_year:
            end_year += 100
        return f"{start_year} - {end_year}"

    @staticmethod
    def intake_start_year_from_slug(slug: str) -> int:
        """Start year from slug suffix (-2027-28 → 2027), or 0 when absent."""
        match = _INTAKE_YEAR_SUFFIX_RE.search((slug or "").strip())
        if not match:
            return 0
        return int(match.group(1))

    @staticmethod
    def course_identity_slug(slug: str) -> str:
        """Course slug without trailing intake year (sound-engineering-bsc-hons-2026-27 → …-hons)."""
        text = (slug or "").strip()
        stripped = _INTAKE_YEAR_SUFFIX_RE.sub("", text)
        return stripped if stripped else text

    @staticmethod
    def is_intake_year_folder(name: str) -> bool:
        return bool(_INTAKE_YEAR_FOLDER_RE.match((name or "").strip()))

    @staticmethod
    def study_level_folder_from_path(md_path: Path, courses_dir: Path | None = None) -> str:
        """Return study-level folder (undergraduate, foundation, …) for a course markdown path."""
        if courses_dir:
            try:
                rel = md_path.relative_to(courses_dir)
                if rel.parts and rel.parts[0] in STUDY_LEVELS:
                    return rel.parts[0]
            except ValueError:
                pass
        parent_name = md_path.parent.name
        if parent_name in STUDY_LEVELS:
            return parent_name
        grandparent_name = md_path.parent.parent.name if md_path.parent.parent else ""
        if grandparent_name in STUDY_LEVELS:
            return grandparent_name
        return parent_name

    @staticmethod
    def clean_course_md_relative_path(
        study_level: str,
        slug_base: str,
        *,
        clean_dir: str = "clean",
        courses_subdir: str = CLEAN_COURSES_SUBDIR,
    ) -> str:
        folder = folder_for_level(study_level)
        year_folder = StudyLevelPathResolver.intake_year_folder_from_stem(slug_base)
        parts = [clean_dir, courses_subdir, folder]
        if year_folder:
            parts.append(year_folder)
        parts.append(f"{slug_base}.md")
        return "/".join(parts)

    @staticmethod
    def clean_courses_root(output_dir: Path, *, presetup: bool = False) -> Path:
        subdir = PRESETUP_CLEAN_SUBDIR if presetup else CLEAN_COURSES_SUBDIR
        return output_dir / "clean" / subdir

    @staticmethod
    def iter_course_markdown(courses_dir: Path) -> list[Path]:
        if not courses_dir.is_dir():
            return []
        return sorted(
            (path for path in courses_dir.rglob("*.md") if path.is_file()),
            key=lambda path: path.as_posix().lower(),
        )

    @staticmethod
    def relative_course_md(md_path: Path, courses_dir: Path) -> str:
        try:
            return md_path.relative_to(courses_dir).as_posix()
        except ValueError:
            return md_path.name

    @staticmethod
    def extraction_dir(
        output_dir: Path,
        slug: str,
        study_level: str | None,
        *,
        extract_root: str | None = None,
    ) -> Path:
        folder = folder_for_level(study_level)
        if extract_root:
            return output_dir / "extracted" / extract_root / folder / slug
        nested = output_dir / "extracted" / folder / slug
        legacy = output_dir / "extracted" / slug
        if nested.exists() or not legacy.exists():
            return nested
        return legacy

    @staticmethod
    def iter_extracted_json(extracted_dir: Path, filename: str) -> list[Path]:
        if not extracted_dir.is_dir():
            return []
        paths = list(extracted_dir.glob(f"*/{filename}"))
        paths.extend(extracted_dir.glob(f"*/*/{filename}"))
        return sorted({path for path in paths if path.is_file()})


class PresetupSampler:
    """Presetup sample selection and URL list helpers."""

    PRESETUP_SAMPLE_JSON = PRESETUP_SAMPLE_JSON
    PRESETUP_SAMPLE_SIZE = PRESETUP_SAMPLE_SIZE
    SCRAPE_PRESETUP_SAMPLE_JSON = SCRAPE_PRESETUP_SAMPLE_JSON
    SCRAPE_PRESETUP_PER_LEVEL = SCRAPE_PRESETUP_PER_LEVEL

    @staticmethod
    def presetup_scrape_sample_path(output_dir: Path) -> Path:
        return output_dir / SCRAPE_PRESETUP_SAMPLE_JSON

    @staticmethod
    def load_presetup_scrape_sample(output_dir: Path) -> dict:
        path = PresetupSampler.presetup_scrape_sample_path(output_dir)
        if not path.is_file():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def save_presetup_scrape_sample(
        output_dir: Path,
        courses: list[dict[str, str]],
        *,
        seed: int,
        n: int = SCRAPE_PRESETUP_PER_LEVEL,
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "per_level": n,
            "seed": seed,
            "sampled_at": datetime.now(timezone.utc).isoformat(),
            "courses": courses,
        }
        path = PresetupSampler.presetup_scrape_sample_path(output_dir)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    @staticmethod
    def presetup_scrape_sample_urls(payload: dict | None) -> list[str]:
        return PresetupSampler.presetup_sample_urls(payload)

    @staticmethod
    def normalize_url(url: str) -> str:
        return (url or "").strip().rstrip("/")

    @staticmethod
    def unique_urls(urls: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for url in urls:
            key = PresetupSampler.normalize_url(url)
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(url.strip())
        return out

    @staticmethod
    def presetup_sample_path(output_dir: Path) -> Path:
        return output_dir / PRESETUP_SAMPLE_JSON

    @staticmethod
    def load_presetup_sample(output_dir: Path) -> dict:
        path = PresetupSampler.presetup_sample_path(output_dir)
        if not path.is_file():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def save_presetup_sample(
        output_dir: Path,
        courses: list[dict[str, str]],
        *,
        seed: int,
        n: int = PRESETUP_SAMPLE_SIZE,
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "n": n,
            "seed": seed,
            "sampled_at": datetime.now(timezone.utc).isoformat(),
            "courses": courses,
        }
        path = PresetupSampler.presetup_sample_path(output_dir)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    @staticmethod
    def presetup_sample_urls(payload: dict | None) -> list[str]:
        courses = (payload or {}).get("courses") or []
        urls: list[str] = []
        for item in courses:
            if isinstance(item, dict):
                urls.append(str(item.get("course_url") or ""))
            elif isinstance(item, str):
                urls.append(item)
        return PresetupSampler.unique_urls(urls)

    @staticmethod
    def urls_for_levels(url_levels: UrlLevelMap, levels: list[str]) -> list[dict[str, str]]:
        allowed = set(levels)
        records: list[dict[str, str]] = []
        seen: set[str] = set()
        for level in EXECUTE_LEVEL_ORDER:
            if level not in allowed:
                continue
            for record in url_levels.records():
                if record["study_level"] != level:
                    continue
                key = PresetupSampler.normalize_url(record["course_url"])
                if not key or key in seen:
                    continue
                seen.add(key)
                records.append(record)
        return records

    @staticmethod
    def sample_urls_stratified(
        url_levels: UrlLevelMap,
        n: int = PRESETUP_SAMPLE_SIZE,
        seed: int | None = None,
        levels: list[str] | None = None,
    ) -> list[dict[str, str]]:
        """Shuffle each non-empty level, then round-robin until n unique URLs."""
        if n <= 0:
            return []
        rng = random.Random(seed)
        order = [level for level in EXECUTE_LEVEL_ORDER if not levels or level in levels]
        buckets: dict[str, list[str]] = {level: [] for level in order}
        seen_in_bucket: dict[str, set[str]] = {level: set() for level in order}
        for record in url_levels.records():
            level = record["study_level"]
            if level not in buckets:
                continue
            url = record["course_url"].strip()
            key = PresetupSampler.normalize_url(url)
            if not key or key in seen_in_bucket[level]:
                continue
            seen_in_bucket[level].add(key)
            buckets[level].append(url)
        for level in order:
            rng.shuffle(buckets[level])

        queues = {level: list(urls) for level, urls in buckets.items() if urls}
        chosen: list[dict[str, str]] = []
        seen: set[str] = set()
        while len(chosen) < n:
            progressed = False
            for level in order:
                queue = queues.get(level)
                if not queue:
                    continue
                while queue:
                    url = queue.pop(0)
                    key = PresetupSampler.normalize_url(url)
                    if key in seen:
                        continue
                    seen.add(key)
                    chosen.append({"course_url": url, "study_level": level})
                    progressed = True
                    break
                if len(chosen) >= n:
                    break
            if not progressed:
                break
        return chosen

    @staticmethod
    def sample_urls_per_level(
        url_levels: UrlLevelMap,
        n: int = SCRAPE_PRESETUP_PER_LEVEL,
        seed: int | None = None,
        levels: list[str] | None = None,
    ) -> list[dict[str, str]]:
        """Pick up to n shuffled URLs from each non-empty study level."""
        if n <= 0:
            return []
        rng = random.Random(seed)
        order = [level for level in EXECUTE_LEVEL_ORDER if not levels or level in levels]
        chosen: list[dict[str, str]] = []
        for level in order:
            urls = [
                record["course_url"]
                for record in url_levels.records()
                if record["study_level"] == level
            ]
            rng.shuffle(urls)
            seen: set[str] = set()
            level_chosen: list[str] = []
            for url in urls:
                key = PresetupSampler.normalize_url(url)
                if not key or key in seen:
                    continue
                seen.add(key)
                level_chosen.append(url)
                if len(level_chosen) >= n:
                    break
            for url in level_chosen:
                chosen.append({"course_url": url, "study_level": level})
        return chosen

    @staticmethod
    def read_urls_file(path: Path) -> list[str]:
        """Read URLs from JSON (presetup sample / list), CSV, or one-URL-per-line text."""
        text = path.read_text(encoding="utf-8-sig")
        stripped = text.strip()
        if not stripped:
            return []
        if stripped[0] in "{[":
            payload = json.loads(stripped)
            if isinstance(payload, dict):
                rows = payload.get("courses") or payload.get("urls") or []
                urls: list[str] = []
                if isinstance(rows, list):
                    for item in rows:
                        if isinstance(item, str):
                            urls.append(item)
                        elif isinstance(item, dict):
                            urls.append(str(item.get("course_url") or item.get("url") or ""))
                return PresetupSampler.unique_urls(urls)
            if isinstance(payload, list):
                urls = []
                for item in payload:
                    if isinstance(item, str):
                        urls.append(item)
                    elif isinstance(item, dict):
                        urls.append(str(item.get("course_url") or item.get("url") or ""))
                return PresetupSampler.unique_urls(urls)
        if "course_url" in stripped.splitlines()[0].lower() or path.suffix.lower() == ".csv":
            import io

            handle = io.StringIO(text)
            urls = []
            for row in csv.DictReader(handle):
                urls.append((row.get("course_url") or row.get("url") or "").strip())
            return PresetupSampler.unique_urls(urls)
        return PresetupSampler.unique_urls(
            [line.strip() for line in stripped.splitlines() if line.strip() and not line.strip().startswith("#")]
        )

    @staticmethod
    def level_url_counts(output_dir: Path) -> dict[str, int]:
        mapping = load_url_levels(output_dir)
        counts = {level: 0 for level in STUDY_LEVELS}
        seen: dict[str, set[str]] = {level: set() for level in STUDY_LEVELS}
        for record in mapping.records():
            level = record["study_level"]
            key = PresetupSampler.normalize_url(record["course_url"])
            if not key:
                continue
            if level not in seen:
                seen[level] = set()
                counts[level] = 0
            if key in seen[level]:
                continue
            seen[level].add(key)
            counts[level] = counts.get(level, 0) + 1
        return counts


def presetup_level_counts(
    url_levels: UrlLevelMap,
    levels: list[str] | None = None,
) -> dict[str, int]:
    order = [level for level in EXECUTE_LEVEL_ORDER if not levels or level in levels]
    counts = {level: 0 for level in order}
    seen: dict[str, set[str]] = {level: set() for level in order}
    for record in url_levels.records():
        level = record["study_level"]
        if level not in counts:
            continue
        key = PresetupSampler.normalize_url(record["course_url"])
        if not key or key in seen[level]:
            continue
        seen[level].add(key)
        counts[level] += 1
    return counts


def presetup_should_stop_pagination(
    url_levels: UrlLevelMap,
    n: int,
    levels: list[str] | None = None,
) -> bool:
    """Stop listing pagination when every level seen so far has at least n URLs."""
    if n <= 0:
        return False
    counts = presetup_level_counts(url_levels, levels)
    present = [(level, count) for level, count in counts.items() if count > 0]
    if not present:
        return False
    return all(count >= n for _, count in present)


# Backward-compatible module-level aliases for path resolver / presetup sampler
intake_start_year_from_md_path = StudyLevelPathResolver.intake_start_year_from_md_path
intake_start_year_from_slug = StudyLevelPathResolver.intake_start_year_from_slug
intake_year_folder_from_stem = StudyLevelPathResolver.intake_year_folder_from_stem
course_identity_slug = StudyLevelPathResolver.course_identity_slug
is_intake_year_folder = StudyLevelPathResolver.is_intake_year_folder
study_level_folder_from_path = StudyLevelPathResolver.study_level_folder_from_path
clean_course_md_relative_path = StudyLevelPathResolver.clean_course_md_relative_path
clean_courses_root = StudyLevelPathResolver.clean_courses_root
iter_course_markdown = StudyLevelPathResolver.iter_course_markdown
relative_course_md = StudyLevelPathResolver.relative_course_md
extraction_dir = StudyLevelPathResolver.extraction_dir
iter_extracted_json = StudyLevelPathResolver.iter_extracted_json
normalize_url = PresetupSampler.normalize_url
unique_urls = PresetupSampler.unique_urls
presetup_sample_path = PresetupSampler.presetup_sample_path
load_presetup_sample = PresetupSampler.load_presetup_sample
save_presetup_sample = PresetupSampler.save_presetup_sample
presetup_sample_urls = PresetupSampler.presetup_sample_urls
urls_for_levels = PresetupSampler.urls_for_levels
sample_urls_stratified = PresetupSampler.sample_urls_stratified
sample_urls_per_level = PresetupSampler.sample_urls_per_level
read_urls_file = PresetupSampler.read_urls_file
level_url_counts = PresetupSampler.level_url_counts
presetup_scrape_sample_path = PresetupSampler.presetup_scrape_sample_path
load_presetup_scrape_sample = PresetupSampler.load_presetup_scrape_sample
save_presetup_scrape_sample = PresetupSampler.save_presetup_scrape_sample
presetup_scrape_sample_urls = PresetupSampler.presetup_scrape_sample_urls
write_presetup_urls_csv = write_presetup_urls_csv
load_presetup_url_levels = load_presetup_url_levels
count_presetup_scrape_urls = count_presetup_scrape_urls
read_presetup_urls_csv = read_presetup_urls_csv
select_presetup_download_courses = select_presetup_download_courses
presetup_download_sample_stale = presetup_download_sample_stale
