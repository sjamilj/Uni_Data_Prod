#!/usr/bin/env python3
"""Download course HTML pages and clean them into markdown.

Reads URLs from course_urls.csv (produced by scrape_course_urls.py), saves HTML
under course_pages/, then writes trimmed markdown under clean/courses/
(or clean/pre_setup_course/ for the 10-course presetup sample).

Uni pages are cleaned separately from {University}/uni_req/*.html → clean/uni/*.md.

Class-based refactor — behaviour matches the original procedural script; code is
organised into small single-purpose classes (config loading, markdown conversion,
course cleaning, uni_req cleaning, manifest I/O, pipeline orchestration).

Run from university code/ (same pattern as scrape_course_urls.py):
  python "../../shared/download_and_clean_course_pages.py" .
  python "../../shared/download_and_clean_course_pages.py" . --fresh
  python "../../shared/download_and_clean_course_pages.py" . --clean-only
  python "../../shared/download_and_clean_course_pages.py" . --clean-uni-only
  python "../../shared/download_and_clean_course_pages.py" . --clean-all
  python "../../shared/download_and_clean_course_pages.py" . --download-only
  python "../../shared/download_and_clean_course_pages.py" . --url https://example.ac.uk/course
  python "../../shared/download_and_clean_course_pages.py" . --study-level foundation --limit 10

Per-university HTML engines: COURSE_CLEAN_ENGINE in .env (generic | utopian | plugin).
Per-university markdown post-processing: shared/course_markdown_cleanup.py (.env
section removal) plus optional {University}/code/course_markdown_cleanup.py.

Course type filter: COURSE_EXCLUDE_COURSE_TYPES / COURSE_EXCLUDE_URL_PATTERNS in
.env skip short-course, CPD, and part-time pages after download and during clean.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup, NavigableString, Tag

_SHARED_DIR = Path(__file__).resolve().parent
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

from scrape_course_urls import (
    CANONICAL_URL_RE,
    COURSE_PAGE_MAP_CSV,
    COURSE_PAGES_DIR,
    COURSE_URLS_CSV,
    ENV_FILE,
    SAVED_URL_COMMENT_RE,
    ScrapeLogger,
    add_code_dir_argument,
    download_course_pages,
    load_env_file,
    load_strategy_config,
    resolve_work_dir,
)
from course_markdown_cleanup import (
    cleanup_course_markdown,
    cleanup_uni_markdown,
    uni_source_url,
)
from clean_config import CleanConfig, CleanConfigLoader
from course_type_filter import CourseTypeFilter
from engines import get_course_html_engine
from markdown_converter import MarkdownConverter, Utils
from uni_paths import resolve_code_dir, resolve_output_dir
from uni_pages import UNI_MD_BY_ROLE, course_slug_from_url, uni_md_output_name
from study_level import (
    CLEAN_COURSES_SUBDIR,
    StudyLevelClassifier,
    folder_for_level,
    clean_course_md_relative_path,
    intake_year_folder_from_stem,
    iter_course_markdown,
    levels_for_url,
    load_url_levels,
    normalize_url,
    parse_study_levels,
    read_urls_file,
    unique_urls,
    urls_for_levels,
)


# ============================================================================
# Constants
# ============================================================================

CLEAN_DIR = "clean"
CLEAN_WARNINGS_CSV = "clean_warnings.csv"
UNI_REQ_DIR = "uni_req"

SAVED_URL_COMMENT_FALLBACK_RE = re.compile(
    r"<!-- saved from url=\(([^)]+)\)", re.I
)


# ============================================================================
# Per-university markdown cleanup bridge
# ============================================================================

class CourseMarkdownCleanupBridge:
    """Dispatch to shared/course_markdown_cleanup.py using UNIVERSITY_NAME from .env."""

    def __init__(self, code_dir: Path):
        self.code_dir = resolve_code_dir(code_dir)

    def cleanup_course(self, markdown: str) -> str:
        return cleanup_course_markdown(markdown, code_dir=self.code_dir)

    def cleanup_uni(self, markdown: str, **kwargs: object) -> str:
        return cleanup_uni_markdown(
            markdown,
            code_dir=self.code_dir,
            **kwargs,
        )

    def uni_source_url(
        self,
        raw_source: str,
        **kwargs: object,
    ) -> str | None:
        return uni_source_url(
            raw_source,
            code_dir=self.code_dir,
            **kwargs,
        )


# ============================================================================
# University identity
# ============================================================================

class UniversityNameResolver:
    """Resolve display name from required UNIVERSITY_NAME in .env."""

    @staticmethod
    def resolve(work_dir: Path) -> str:
        env_path = work_dir / ENV_FILE

        if not env_path.exists():
            raise ValueError(
                f"Missing {ENV_FILE}; set UNIVERSITY_NAME= in .env"
            )

        env = load_env_file(env_path)
        name = (env.get("UNIVERSITY_NAME") or "").strip()

        if not name:
            raise ValueError(
                f"UNIVERSITY_NAME is required in {env_path}"
            )

        return name


class UniReqDirResolver:
    """Locate uni_req HTML — {University}/uni_req/ (preferred) or code/uni_req/."""

    @staticmethod
    def resolve(work_dir: Path) -> Path | None:
        work_dir = work_dir.resolve()

        for candidate in (
            work_dir.parent / UNI_REQ_DIR,
            work_dir / UNI_REQ_DIR,
        ):
            if candidate.is_dir():
                return candidate

        return None

    @staticmethod
    def source_html_rel(
        html_path: Path,
        work_dir: Path,
    ) -> str:
        html_path = html_path.resolve()
        work_dir = work_dir.resolve()

        for base in (
            work_dir.parent,
            work_dir,
        ):
            try:
                return html_path.relative_to(base).as_posix()
            except ValueError:
                continue

        return html_path.name


# ============================================================================
# HTML source helpers
# ============================================================================

class HtmlSourceExtractor:
    """Pull canonical / saved-from URL from downloaded HTML."""

    @staticmethod
    def extract_saved_url(html: str) -> str | None:
        match = SAVED_URL_COMMENT_RE.search(html[:2000])

        if match:
            return match.group(1).strip()

        match = SAVED_URL_COMMENT_FALLBACK_RE.search(html[:2000])

        if match:
            return match.group(1).strip()

        return None

    @classmethod
    def extract_source_url(cls, html: str) -> str:
        saved = cls.extract_saved_url(html)

        if saved:
            return saved

        soup = BeautifulSoup(html, "html.parser")

        link = soup.select_one(
            "link[rel='canonical'], link[rel='Canonical']"
        )

        if link and link.get("href"):
            return str(link["href"]).strip()

        match = CANONICAL_URL_RE.search(html)

        if match:
            return match.group(1).strip()

        return ""


# ============================================================================
# Clean warnings
# ============================================================================

@dataclass(frozen=True)
class CleanWarning:
    source_html: str
    source_url: str
    warning_type: str
    detail: str


class CleanWarningsWriter:
    """Write per-page cleaning warnings to output/clean_warnings.csv."""

    FIELDNAMES = (
        "source_html",
        "source_url",
        "warning_type",
        "detail",
    )

    @classmethod
    def write(
        cls,
        output_dir: Path,
        warnings: list[CleanWarning],
    ) -> Path:
        path = output_dir / CLEAN_WARNINGS_CSV

        with path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=cls.FIELDNAMES,
            )

            writer.writeheader()

            for warning in warnings:
                writer.writerow(
                    {
                        "source_html": warning.source_html,
                        "source_url": warning.source_url,
                        "warning_type": warning.warning_type,
                        "detail": warning.detail,
                    }
                )

        return path


# ============================================================================
# Course markdown (engine dispatch)
# ============================================================================

class CourseMarkdownBuilder:
    """Build course markdown using .env COURSE_CLEAN_BLOCKS + COURSE_CLEAN_ENGINE."""

    @classmethod
    def from_config(
        cls,
        html: str,
        clean_config: CleanConfig,
        code_dir: Path,
        *,
        warnings: list[CleanWarning] | None = None,
        source_html: str = "",
        source_url: str = "",
    ) -> str:
        soup = BeautifulSoup(html, "html.parser")

        engine = get_course_html_engine(
            clean_config.engine,
            code_dir,
        )

        sections: list[str] = []

        title = engine.course_title_from_soup(
            soup,
            clean_config,
        )

        if title:
            sections.append(f"# {title}")

        blocks_produced = 0

        for env_heading, selector in clean_config.blocks:
            node, resolved_selector = engine.find_block(
                soup,
                env_heading,
                selector,
            )

            if not node:
                detail = selector

                print(
                    f"  Warning: clean block not found: {detail}"
                )

                if warnings is not None:
                    warnings.append(
                        CleanWarning(
                            source_html=source_html,
                            source_url=source_url,
                            warning_type="block_not_found",
                            detail=detail,
                        )
                    )

                continue

            clone = BeautifulSoup(
                str(node),
                "html.parser",
            )

            block_root = clone.find(True) or clone

            engine.strip_within_block(
                block_root,
                clean_config.strip_within,
            )

            heading = (
                env_heading
                or engine.derive_heading_from_block(block_root)
            )

            body = engine.block_body(
                soup,
                block_root,
                resolved_selector,
                env_heading,
                clean_config,
            )

            if not body:
                continue

            if heading:
                block = (
                    f"## {heading}"
                    + "\n\n"
                    + body
                )
            else:
                block = body

            block = engine.append_block_extras(
                block_root,
                selector,
                block,
            )

            sections.append(block)
            blocks_produced += 1

        if blocks_produced == 0 and not title:
            print(
                "  Warning: no clean blocks produced content"
            )

            if warnings is not None:
                warnings.append(
                    CleanWarning(
                        source_html=source_html,
                        source_url=source_url,
                        warning_type="no_blocks_produced",
                        detail="",
                    )
                )

        markdown = Utils.normalise_text(
            "\n\n".join(
                section
                for section in sections
                if section.strip()
            )
        )

        markdown = re.sub(
            r"\n{3,}",
            "\n\n",
            markdown,
        )

        return markdown


class GenericMarkdownBuilder:
    """Full-page clean for uni_req HTML — no .env block selectors."""

    @classmethod
    def from_html(cls, html: str) -> str:
        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        sections: list[str] = []

        title = MarkdownConverter.page_title_from_soup(soup)

        if title:
            sections.append(f"# {title}")

        main = MarkdownConverter.extract_main_content(soup)
        body = MarkdownConverter.tag_to_markdown(main)

        if body:
            sections.append(body)

        markdown = Utils.normalise_text(
            "\n\n".join(
                section
                for section in sections
                if section.strip()
            )
        )

        markdown = re.sub(
            r"\n{3,}",
            "\n\n",
            markdown,
        )

        return markdown


# ============================================================================
# Course entry catalog
# ============================================================================

class CourseEntryCatalog:
    """Resolve (course_url, html_path) pairs from map CSV or course_pages/."""

    def __init__(self, code_dir: Path):
        self.code_dir = code_dir.resolve()
        self.output_dir = resolve_output_dir(self.code_dir)

    def read_entries(self) -> list[tuple[str, Path]]:
        map_path = self.output_dir / COURSE_PAGE_MAP_CSV
        pages_dir = self.output_dir / COURSE_PAGES_DIR

        entries: list[tuple[str, Path]] = []

        if map_path.exists():
            with map_path.open(
                newline="",
                encoding="utf-8",
            ) as handle:
                for row in csv.DictReader(handle):
                    course_url = (
                        row.get("course_url") or ""
                    ).strip()

                    html_rel = (
                        row.get("html_path")
                        or row.get("html_file")
                        or ""
                    ).strip()

                    if not html_rel:
                        continue

                    html_path = (
                        self.output_dir
                        / Path(html_rel)
                    )

                    if html_path.exists():
                        entries.append(
                            (
                                course_url,
                                html_path,
                            )
                        )

        if entries:
            return entries

        if not pages_dir.is_dir():
            return []

        for html_path in sorted(
            pages_dir.glob("*.html")
        ):
            raw_html = html_path.read_text(
                encoding="utf-8",
                errors="replace",
            )

            course_url = (
                HtmlSourceExtractor.extract_source_url(
                    raw_html
                )
            )

            entries.append(
                (
                    course_url,
                    html_path,
                )
            )

        return entries


# ============================================================================
# Manifest I/O
# ============================================================================

class ManifestWriter:
    @staticmethod
    def build_frontmatter(
        *,
        source_html: str,
        source_url: str,
        page_type: str,
        university: str,
        study_level: str = "",
        course_url: str = "",
    ) -> str:
        lines = [
            "---",
            f"source_html: {source_html}",
            f"source_url: {source_url}",
            f"page_type: {page_type}",
            f"university: {university}",
            f"cleaned_at: {date.today().isoformat()}",
        ]

        if course_url:
            lines.append(
                f"course_url: {course_url}"
            )

        if study_level:
            lines.append(
                f"study_level: {study_level}"
            )

        lines.extend(
            [
                "---",
                "",
            ]
        )

        return "\n".join(lines)

    @staticmethod
    def _merge_course_lists(
        existing: list[dict],
        incoming: list[dict],
    ) -> list[dict]:
        merged: dict[
            tuple[str, str],
            dict,
        ] = {}

        for item in existing:
            key = (
                normalize_url(
                    str(
                        item.get("course_url")
                        or ""
                    )
                ),
                str(
                    item.get("study_level")
                    or ""
                ),
            )

            merged[key] = item

        for item in incoming:
            key = (
                normalize_url(
                    str(
                        item.get("course_url")
                        or ""
                    )
                ),
                str(
                    item.get("study_level")
                    or ""
                ),
            )

            merged[key] = item

        return list(merged.values())

    @classmethod
    def merge(
        cls,
        work_dir: Path,
        courses: list[dict],
        uni_pages: list[dict],
        *,
        university_name: str,
        replace_courses: bool = False,
    ) -> None:
        output_dir = resolve_output_dir(work_dir)
        clean_root = output_dir / CLEAN_DIR
        manifest_path = clean_root / "manifest.json"

        manifest: dict = {
            "university": university_name,
            "cleaned_at": date.today().isoformat(),
            "courses": courses,
            "uni_pages": uni_pages,
        }

        if manifest_path.exists():
            try:
                existing = json.loads(
                    manifest_path.read_text(
                        encoding="utf-8"
                    )
                )

                if (
                    courses
                    and not replace_courses
                    and existing.get("courses")
                ):
                    manifest["courses"] = (
                        ManifestWriter._merge_course_lists(
                            existing.get("courses")
                            or [],
                            courses,
                        )
                    )

                elif (
                    not courses
                    and existing.get("courses")
                ):
                    manifest["courses"] = (
                        existing["courses"]
                    )

                if (
                    not uni_pages
                    and existing.get("uni_pages")
                ):
                    manifest["uni_pages"] = (
                        existing["uni_pages"]
                    )

            except (
                json.JSONDecodeError,
                OSError,
            ):
                pass

        clean_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        manifest_path.write_text(
            json.dumps(
                manifest,
                indent=2,
            ),
            encoding="utf-8",
        )


# ============================================================================
# Cleaners
# ============================================================================

class CoursePagesCleaner:
    """Convert course_pages/*.html → clean/{courses|pre_setup_course}/*.md using .env selectors."""

    def __init__(self, code_dir: Path):
        self.code_dir = code_dir.resolve()
        self.output_dir = resolve_output_dir(
            self.code_dir
        )
        self.university_name = (
            UniversityNameResolver.resolve(
                self.code_dir
            )
        )
        self.markdown_cleanup = (
            CourseMarkdownCleanupBridge(
                self.code_dir
            )
        )

    @staticmethod
    def _delete_markdown_for_source(
        courses_out: Path,
        *,
        html_rel: str,
        source_url: str,
    ) -> bool:
        deleted = False

        for md_path in iter_course_markdown(
            courses_out
        ):
            try:
                text = md_path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )
            except OSError:
                continue

            if (
                f"source_html: {html_rel}" in text
                or f"source_url: {source_url}" in text
            ):
                md_path.unlink()
                deleted = True

        return deleted

    def run(
        self,
        *,
        limit: int | None = None,
        urls: list[str] | None = None,
        filter_levels: list[str] | None = None,
        courses_subdir: str = CLEAN_COURSES_SUBDIR,
    ) -> dict:
        clean_root = self.output_dir / CLEAN_DIR
        courses_out = (
            clean_root / courses_subdir
        )

        courses_out.mkdir(
            parents=True,
            exist_ok=True,
        )

        entries = CourseEntryCatalog(
            self.code_dir
        ).read_entries()

        url_levels = load_url_levels(
            self.output_dir
        )

        classifier = (
            StudyLevelClassifier.from_code_dir(
                self.code_dir
            )
        )

        # ------------------------------------------------------------
        # Explicit URL filtering
        # ------------------------------------------------------------

        if urls is not None:
            wanted = {
                normalize_url(url)
                for url in urls
                if (url or "").strip()
            }

            entries = [
                (
                    course_url,
                    html_path,
                )
                for course_url, html_path in entries
                if normalize_url(course_url)
                in wanted
            ]

        # ------------------------------------------------------------
        # Study-level filtering
        # ------------------------------------------------------------

        if filter_levels:
            allowed = set(filter_levels)
            filtered: list[
                tuple[str, Path]
            ] = []

            for course_url, html_path in entries:
                found = levels_for_url(
                    course_url,
                    url_levels=url_levels,
                    classifier=classifier,
                )

                if any(
                    level in allowed
                    for level in found
                ):
                    filtered.append(
                        (
                            course_url,
                            html_path,
                        )
                    )

            entries = filtered

        # ------------------------------------------------------------
        # Limit
        # ------------------------------------------------------------

        if limit is not None:
            entries = entries[:limit]

        if not entries:
            raise ValueError(
                f"No HTML files in {COURSE_PAGES_DIR}/ "
                f"and no {COURSE_PAGE_MAP_CSV}. "
                f"Run download first or ensure "
                f"{COURSE_URLS_CSV} URLs were downloaded."
            )

        manifest: dict = {
            "university": self.university_name,
            "cleaned_at": date.today().isoformat(),
            "courses": [],
        }

        # ------------------------------------------------------------
        # IMPORTANT:
        # This is output-level deduplication.
        #
        # We DO NOT dedupe course URLs.
        # Foundation and undergraduate may legitimately share
        # the same URL.
        # ------------------------------------------------------------

        used_keys: set[
            tuple[str, str]
        ] = set()

        clean_config = (
            CleanConfigLoader.load(
                self.code_dir
            )
        )

        course_filter = (
            CourseTypeFilter.from_code_dir(
                self.code_dir
            )
        )

        excluded_count = 0

        # NEW:
        # Track collisions instead of silently skipping them.
        duplicate_count = 0

        level_counts: dict[str, int] = {}

        warnings: list[
            CleanWarning
        ] = []

        print(
            f"Cleaning {len(entries)} course pages..."
        )

        if clean_config.blocks:
            print(
                f"COURSE_CLEAN_BLOCKS="
                f"{len(clean_config.blocks)} block(s), "
                f"engine={clean_config.engine}"
            )
        else:
            print(
                "COURSE_CLEAN_BLOCKS not set — "
                "using generic main-content extraction"
            )

        # ------------------------------------------------------------
        # Process each HTML page
        # ------------------------------------------------------------

        for course_url, html_path in entries:
            html_rel = (
                html_path
                .relative_to(self.output_dir)
                .as_posix()
            )

            raw_html = html_path.read_text(
                encoding="utf-8",
                errors="replace",
            )

            # Source URL comes from saved HTML first.
            source_url = (
                HtmlSourceExtractor.extract_source_url(
                    raw_html
                )
                or course_url
            )

            # --------------------------------------------------------
            # Course type filtering
            # --------------------------------------------------------

            if course_filter.should_exclude_html(
                raw_html,
                url=source_url or course_url,
            ):
                excluded_count += 1

                self._delete_markdown_for_source(
                    courses_out,
                    html_rel=html_rel,
                    source_url=source_url,
                )

                html_path.unlink(
                    missing_ok=True
                )

                continue

            # --------------------------------------------------------
            # Generate output slug
            # --------------------------------------------------------

            slug_base = course_slug_from_url(
                source_url
                or html_path.stem
            )

            # --------------------------------------------------------
            # Resolve study levels
            # --------------------------------------------------------

            study_levels = levels_for_url(
                course_url or source_url,
                url_levels=url_levels,
                classifier=classifier,
            )

            # --------------------------------------------------------
            # Build markdown
            # --------------------------------------------------------

            if clean_config.blocks:
                markdown = (
                    CourseMarkdownBuilder.from_config(
                        raw_html,
                        clean_config,
                        self.code_dir,
                        warnings=warnings,
                        source_html=html_rel,
                        source_url=source_url,
                    )
                )
            else:
                markdown = (
                    GenericMarkdownBuilder.from_html(
                        raw_html
                    )
                )

            markdown = (
                self.markdown_cleanup.cleanup_course(
                    markdown
                )
            )

            # --------------------------------------------------------
            # Write one markdown per study level
            # --------------------------------------------------------

            for study_level in study_levels:
                folder = folder_for_level(
                    study_level
                )

                # Existing behaviour:
                # one output file per (folder, slug)
                key = (
                    folder,
                    slug_base,
                )

                # ----------------------------------------------------
                # DUPLICATE OUTPUT KEY DETECTION
                # ----------------------------------------------------
                #
                # Previously this was:
                #
                #   if key in used_keys:
                #       continue
                #
                # That made duplicate output collisions invisible.
                #
                # Now we print exactly what collided.
                # ----------------------------------------------------

                if key in used_keys:
                    duplicate_count += 1

                    print(
                        "  DUPLICATE OUTPUT KEY:"
                    )
                    print(
                        f"    course_url : {course_url}"
                    )
                    print(
                        f"    html       : {html_path.name}"
                    )
                    print(
                        f"    source_url : {source_url}"
                    )
                    print(
                        f"    slug       : {slug_base}"
                    )
                    print(
                        f"    folder     : {folder}"
                    )
                    print(
                        f"    key        : {key}"
                    )

                    continue

                used_keys.add(key)

                # ----------------------------------------------------
                # Intake-year folder
                # ----------------------------------------------------

                year_folder = (
                    intake_year_folder_from_stem(
                        slug_base
                    )
                )

                level_dir = (
                    courses_out / folder
                )

                if year_folder:
                    level_dir = (
                        level_dir / year_folder
                    )

                level_dir.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                output_path = (
                    level_dir
                    / f"{slug_base}.md"
                )

                # ----------------------------------------------------
                # Write markdown
                # ----------------------------------------------------

                output_path.write_text(
                    ManifestWriter.build_frontmatter(
                        source_html=html_rel,
                        source_url=source_url,
                        page_type="course",
                        university=self.university_name,
                        study_level=folder,
                        course_url=course_url,
                    )
                    + markdown
                    + "\n",
                    encoding="utf-8",
                )

                # ----------------------------------------------------
                # Manifest path
                # ----------------------------------------------------

                relative_md = (
                    clean_course_md_relative_path(
                        folder,
                        slug_base,
                        clean_dir=CLEAN_DIR,
                        courses_subdir=courses_subdir,
                    )
                )

                manifest["courses"].append(
                    {
                        "course_url": (
                            course_url
                            or source_url
                        ),
                        "source_html": html_rel,
                        "clean_md": relative_md,
                        "source_url": source_url,
                        "study_level": folder,
                    }
                )

                level_counts[folder] = (
                    level_counts.get(folder, 0)
                    + 1
                )

        # ------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------

        if excluded_count:
            print(
                f"Excluded {excluded_count} "
                f"short-course/part-time pages"
            )

        # NEW:
        # Explicit duplicate summary.
        if duplicate_count:
            print(
                f"Skipped {duplicate_count} "
                f"duplicate output key(s)"
            )

        warnings_path = (
            CleanWarningsWriter.write(
                self.output_dir,
                warnings,
            )
        )

        if warnings:
            print(
                f"Wrote {len(warnings)} cleaning "
                f"warning(s) to {warnings_path}"
            )
        else:
            print(
                f"Wrote {warnings_path} "
                f"(no warnings)"
            )

        print(
            f"Wrote {len(manifest['courses'])} "
            f"course markdown files to "
            f"{courses_out}"
        )

        for level, count in sorted(
            level_counts.items()
        ):
            print(
                f"  {level}: {count}"
            )

        return manifest


class UniReqPagesCleaner:
    """Convert uni_req/*.html → clean/uni/*.md — no .env configuration."""

    def __init__(self, code_dir: Path):
        self.code_dir = code_dir.resolve()
        self.output_dir = resolve_output_dir(
            self.code_dir
        )
        self.university_name = (
            UniversityNameResolver.resolve(
                self.code_dir
            )
        )
        self.markdown_cleanup = (
            CourseMarkdownCleanupBridge(
                self.code_dir
            )
        )

    def run(self) -> list[dict]:
        uni_req_dir = UniReqDirResolver.resolve(
            self.code_dir
        )

        if uni_req_dir is None:
            return []

        html_files = sorted(
            uni_req_dir.glob("*.html")
        )

        if not html_files:
            return []

        clean_root = (
            self.output_dir / CLEAN_DIR
        )

        uni_out = clean_root / "uni"

        uni_out.mkdir(
            parents=True,
            exist_ok=True,
        )

        manifest_pages: list[dict] = []

        md_to_role = {
            md: role
            for role, md in UNI_MD_BY_ROLE.items()
        }

        print(
            f"Cleaning {len(html_files)} "
            f"uni_req page(s) from "
            f"{uni_req_dir}..."
        )

        for html_path in html_files:
            html_rel = (
                UniReqDirResolver.source_html_rel(
                    html_path,
                    self.code_dir,
                )
            )

            raw_html = html_path.read_text(
                encoding="utf-8",
                errors="replace",
            )

            source_url = (
                HtmlSourceExtractor.extract_source_url(
                    raw_html
                )
            )

            if not source_url:
                source_url = (
                    self.markdown_cleanup.uni_source_url(
                        raw_html,
                        html_stem=html_path.stem,
                    )
                    or ""
                )

            md_name = uni_md_output_name(
                html_path.stem
            )

            slug = Path(md_name).stem

            markdown = (
                GenericMarkdownBuilder.from_html(
                    raw_html
                )
            )

            markdown = (
                self.markdown_cleanup.cleanup_uni(
                    markdown,
                    html_stem=html_path.stem,
                    raw_source=raw_html,
                )
            )

            output_path = (
                uni_out / md_name
            )

            output_path.write_text(
                ManifestWriter.build_frontmatter(
                    source_html=html_rel,
                    source_url=source_url,
                    page_type="uni",
                    university=self.university_name,
                )
                + markdown
                + "\n",
                encoding="utf-8",
            )

            manifest_pages.append(
                {
                    "source_html": html_rel,
                    "source_url": source_url,
                    "clean_md": (
                        f"{CLEAN_DIR}/uni/"
                        f"{md_name}"
                    ),
                    "page_type": md_to_role.get(
                        md_name,
                        slug,
                    ),
                }
            )

        print(
            f"Wrote {len(manifest_pages)} "
            f"uni markdown files to {uni_out}"
        )

        return manifest_pages


# ============================================================================
# Cleaning orchestrator
# ============================================================================

class CleaningOrchestrator:
    """Run course and/or uni_req cleaning and write manifest.json."""

    def __init__(self, code_dir: Path):
        self.code_dir = code_dir.resolve()
        self.output_dir = resolve_output_dir(
            self.code_dir
        )

    def run_courses(
        self,
        *,
        limit: int | None = None,
        urls: list[str] | None = None,
        filter_levels: list[str] | None = None,
        courses_subdir: str = CLEAN_COURSES_SUBDIR,
    ) -> dict:
        university_name = (
            UniversityNameResolver.resolve(
                self.code_dir
            )
        )

        course_manifest: dict = {
            "courses": []
        }

        try:
            course_manifest = (
                CoursePagesCleaner(
                    self.code_dir
                ).run(
                    limit=limit,
                    urls=urls,
                    filter_levels=filter_levels,
                    courses_subdir=courses_subdir,
                )
            )

        except ValueError as exc:
            if "No HTML files" not in str(exc):
                raise

            print(
                f"Skipping course pages: {exc}"
            )

        subset = (
            urls is not None
            or bool(filter_levels)
            or limit is not None
        )

        ManifestWriter.merge(
            self.code_dir,
            course_manifest.get(
                "courses",
                [],
            ),
            [],
            university_name=university_name,
            replace_courses=not subset,
        )

        if not course_manifest.get(
            "courses"
        ):
            raise ValueError(
                f"Nothing to clean: "
                f"no HTML in "
                f"{COURSE_PAGES_DIR}/"
            )

        manifest_path = (
            self.output_dir
            / CLEAN_DIR
            / "manifest.json"
        )

        print(
            f"Wrote {manifest_path}"
        )

        return {
            "courses": course_manifest.get(
                "courses",
                [],
            ),
            "uni_pages": [],
        }

    def run_uni(self) -> dict:
        university_name = (
            UniversityNameResolver.resolve(
                self.code_dir
            )
        )

        uni_pages = (
            UniReqPagesCleaner(
                self.code_dir
            ).run()
        )

        if not uni_pages:
            raise ValueError(
                f"Nothing to clean: "
                f"no HTML in {UNI_REQ_DIR}/"
            )

        ManifestWriter.merge(
            self.code_dir,
            [],
            uni_pages,
            university_name=university_name,
        )

        manifest_path = (
            self.output_dir
            / CLEAN_DIR
            / "manifest.json"
        )

        print(
            f"Wrote {manifest_path}"
        )

        return {
            "courses": [],
            "uni_pages": uni_pages,
        }

    def run(
        self,
        *,
        limit: int | None = None,
        urls: list[str] | None = None,
        filter_levels: list[str] | None = None,
        courses_subdir: str = CLEAN_COURSES_SUBDIR,
    ) -> dict:
        university_name = (
            UniversityNameResolver.resolve(
                self.code_dir
            )
        )

        course_manifest: dict = {
            "courses": []
        }

        try:
            course_manifest = (
                CoursePagesCleaner(
                    self.code_dir
                ).run(
                    limit=limit,
                    urls=urls,
                    filter_levels=filter_levels,
                    courses_subdir=courses_subdir,
                )
            )

        except ValueError as exc:
            if "No HTML files" not in str(exc):
                raise

            print(
                f"Skipping course pages: {exc}"
            )

        uni_pages = (
            UniReqPagesCleaner(
                self.code_dir
            ).run()
        )

        subset = (
            urls is not None
            or bool(filter_levels)
            or limit is not None
        )

        ManifestWriter.merge(
            self.code_dir,
            course_manifest.get(
                "courses",
                [],
            ),
            uni_pages,
            university_name=university_name,
            replace_courses=not subset,
        )

        if (
            not course_manifest.get(
                "courses"
            )
            and not uni_pages
        ):
            raise ValueError(
                f"Nothing to clean: "
                f"no HTML in "
                f"{COURSE_PAGES_DIR}/ "
                f"or {UNI_REQ_DIR}/"
            )

        manifest_path = (
            self.output_dir
            / CLEAN_DIR
            / "manifest.json"
        )

        print(
            f"Wrote {manifest_path}"
        )

        return {
            "courses": course_manifest.get(
                "courses",
                [],
            ),
            "uni_pages": uni_pages,
        }


# ============================================================================
# Top-level pipeline
# ============================================================================

class CoursePagesPipeline:
    """Download course HTML from course_urls.csv, then clean to markdown."""

    def __init__(
        self,
        code_dir: Path,
        config: dict[str, str],
    ):
        self.code_dir = code_dir.resolve()
        self.output_dir = resolve_output_dir(
            self.code_dir
        )
        self.config = config

    def run(
        self,
        *,
        fresh: bool = False,
        limit: int | None = None,
        download_only: bool = False,
        clean_only: bool = False,
        clean_uni_only: bool = False,
        clean_all: bool = False,
        urls: list[str] | None = None,
        filter_levels: list[str] | None = None,
        courses_subdir: str = CLEAN_COURSES_SUBDIR,
    ) -> dict:

        if (
            not clean_only
            and not clean_uni_only
            and not clean_all
        ):
            download_course_pages(
                self.code_dir,
                self.config,
                fresh=fresh,
                limit=limit,
                urls=urls,
            )

        if download_only:
            return {}

        orchestrator = CleaningOrchestrator(
            self.code_dir
        )

        if clean_uni_only:
            return orchestrator.run_uni()

        if clean_all:
            return orchestrator.run(
                limit=limit,
                urls=urls,
                filter_levels=filter_levels,
                courses_subdir=courses_subdir,
            )

        return orchestrator.run_courses(
            limit=limit,
            urls=urls,
            filter_levels=filter_levels,
            courses_subdir=courses_subdir,
        )


# ============================================================================
# Backward-compatible module API
# ============================================================================

def clean_course_pages(
    work_dir: Path,
    *,
    limit: int | None = None,
) -> dict:
    return CleaningOrchestrator(
        work_dir
    ).run_courses(
        limit=limit
    )


def clean_uni_req_pages(
    work_dir: Path,
) -> list[dict]:
    return (
        CleaningOrchestrator(
            work_dir
        )
        .run_uni()["uni_pages"]
    )


def run_cleaning(
    work_dir: Path,
    *,
    limit: int | None = None,
    uni: bool = False,
) -> dict:
    orchestrator = CleaningOrchestrator(
        work_dir
    )

    if uni:
        return orchestrator.run_uni()

    return orchestrator.run_courses(
        limit=limit
    )


def download_and_clean_course_pages(
    work_dir: Path,
    config: dict[str, str],
    *,
    fresh: bool = False,
    limit: int | None = None,
    download_only: bool = False,
    clean_only: bool = False,
    clean_uni_only: bool = False,
    clean_all: bool = False,
    urls: list[str] | None = None,
    filter_levels: list[str] | None = None,
    courses_subdir: str = CLEAN_COURSES_SUBDIR,
) -> dict:
    return CoursePagesPipeline(
        work_dir,
        config,
    ).run(
        fresh=fresh,
        limit=limit,
        download_only=download_only,
        clean_only=clean_only,
        clean_uni_only=clean_uni_only,
        clean_all=clean_all,
        urls=urls,
        filter_levels=filter_levels,
        courses_subdir=courses_subdir,
    )


def resolve_url_subset(
    output_dir: Path,
    *,
    urls: list[str] | None = None,
    urls_file: Path | None = None,
    filter_levels: list[str] | None = None,
) -> tuple[
    list[str] | None,
    list[str] | None,
]:
    """Return (explicit_urls_or_None, study_levels_or_None)
    for download/clean filters.
    """

    collected: list[str] = []

    if urls:
        collected.extend(urls)

    if urls_file is not None:
        collected.extend(
            read_urls_file(urls_file)
        )

    collected = unique_urls(collected)

    levels = (
        parse_study_levels(
            filter_levels
        )
        if filter_levels
        else []
    )

    if collected:
        return (
            collected,
            levels or None,
        )

    if levels:
        records = urls_for_levels(
            load_url_levels(output_dir),
            levels,
        )

        return (
            unique_urls(
                [
                    row["course_url"]
                    for row in records
                ]
            ),
            levels,
        )

    return None, None


# ============================================================================
# CLI
# ============================================================================

class CoursePagesCLI:
    """Parses command-line args and runs the download + clean pipeline."""

    @staticmethod
    def build_arg_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description=(
                "Download course HTML pages "
                "and clean them into markdown."
            )
        )

        parser.add_argument(
            "--fresh",
            action="store_true",
            help=(
                "Re-download all URLs "
                "(clears download progress)"
            ),
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help=(
                "Process only the first N course URLs "
                "(download and/or clean, for testing)"
            ),
        )

        parser.add_argument(
            "--download-only",
            action="store_true",
            help=(
                "Download HTML only; skip cleaning"
            ),
        )

        parser.add_argument(
            "--clean-only",
            action="store_true",
            help=(
                "Clean existing course HTML only; "
                "skip download and uni_req"
            ),
        )

        parser.add_argument(
            "--clean-uni-only",
            action="store_true",
            help=(
                "Clean uni_req HTML only; "
                "skip download and course pages"
            ),
        )

        parser.add_argument(
            "--clean-all",
            action="store_true",
            help=(
                "Clean both course pages and uni_req; "
                "skip download"
            ),
        )

        parser.add_argument(
            "--url",
            action="append",
            default=[],
            metavar="URL",
            help=(
                "Process only this course URL "
                "(repeatable)"
            ),
        )

        parser.add_argument(
            "--urls-file",
            type=Path,
            default=None,
            help=(
                "JSON/CSV/text file of course URLs "
                "to process"
            ),
        )

        parser.add_argument(
            "--study-level",
            action="append",
            default=[],
            metavar="LEVEL",
            help=(
                "Restrict to a study level "
                "(repeatable): foundation, "
                "undergraduate, postgraduate, "
                "postgraduate_research"
            ),
        )

        add_code_dir_argument(parser)

        return parser

    @staticmethod
    def main(
        code_dir: Path | None = None,
    ) -> int:

        args = (
            CoursePagesCLI
            .build_arg_parser()
            .parse_args()
        )

        clean_modes = sum(
            1
            for flag in (
                args.clean_only,
                args.clean_uni_only,
                args.clean_all,
            )
            if flag
        )

        if clean_modes > 1:
            print(
                "Error: --clean-only, "
                "--clean-uni-only, and "
                "--clean-all are mutually exclusive.",
                file=sys.stderr,
            )

            return 1

        if (
            args.download_only
            and clean_modes
        ):
            print(
                "Error: --download-only "
                "cannot be combined with a clean mode.",
                file=sys.stderr,
            )

            return 1

        work_dir = resolve_work_dir(
            code_dir
            if code_dir is not None
            else args.code_dir
        )

        try:
            urls, filter_levels = (
                resolve_url_subset(
                    resolve_output_dir(work_dir),
                    urls=args.url,
                    urls_file=args.urls_file,
                    filter_levels=args.study_level,
                )
            )

            config = load_strategy_config(
                work_dir
            )

            CoursePagesPipeline(
                work_dir,
                config,
            ).run(
                fresh=args.fresh,
                limit=args.limit,
                download_only=args.download_only,
                clean_only=args.clean_only,
                clean_uni_only=args.clean_uni_only,
                clean_all=args.clean_all,
                urls=urls,
                filter_levels=filter_levels,
            )

        except Exception as exc:
            print(
                f"Error: {exc}",
                file=sys.stderr,
            )

            try:
                logger = ScrapeLogger(
                    resolve_output_dir(work_dir)
                )

                logger.error(
                    f"Fatal: {exc}"
                )

                logger.end(
                    "error",
                    message=str(exc),
                )

            except OSError:
                pass

            return 1

        return 0


def main() -> int:
    return CoursePagesCLI.main()


if __name__ == "__main__":
    raise SystemExit(main())