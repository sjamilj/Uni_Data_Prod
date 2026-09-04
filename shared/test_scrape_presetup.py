#!/usr/bin/env python3
"""Tests for scrape presetup sampling."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from study_level import (
    PRESETUP_URLS_CSV,
    StudyLevelClassifier,
    UrlLevelMap,
    read_presetup_urls_csv,
    sample_urls_per_level,
    select_presetup_download_courses,
    write_presetup_urls_csv,
    write_level_csvs,
    presetup_download_sample_stale,
)  # noqa: E402


class ScrapePresetupSampleTests(unittest.TestCase):
    def test_sample_urls_per_level_caps_each_level(self) -> None:
        mapping = UrlLevelMap()
        for index in range(8):
            mapping.add(f"https://example.ac.uk/foundation-{index}", "foundation", "FOUNDATION")
            mapping.add(f"https://example.ac.uk/ug-{index}", "undergraduate", "UNDERGRADUATE")

        sample = sample_urls_per_level(mapping, n=5, seed=42)
        foundation = [row for row in sample if row["study_level"] == "foundation"]
        undergraduate = [row for row in sample if row["study_level"] == "undergraduate"]
        self.assertEqual(len(foundation), 5)
        self.assertEqual(len(undergraduate), 5)
        self.assertEqual(len(sample), 10)

    def test_tag_urls_uses_path_patterns_on_mixed_listing(self) -> None:
        classifier = StudyLevelClassifier.from_env_lists(
            {
                "undergraduate": [r"^/courses/undergraduate/"],
                "postgraduate": [r"^/courses/postgraduate/"],
            }
        )
        mapping = UrlLevelMap()
        urls = [
            "https://www.cardiffmet.ac.uk/courses/undergraduate/ba-accounting",
            "https://www.cardiffmet.ac.uk/courses/postgraduate/msc-accounting-and-finance",
        ]
        mapping.tag_urls(urls, scope="UNDERGRADUATE", classifier=classifier, source_scope="UNDERGRADUATE")
        records = {record["course_url"]: record["study_level"] for record in mapping.records()}
        self.assertEqual(
            records["https://www.cardiffmet.ac.uk/courses/postgraduate/msc-accounting-and-finance"],
            "postgraduate",
        )
        self.assertEqual(
            records["https://www.cardiffmet.ac.uk/courses/undergraduate/ba-accounting"],
            "undergraduate",
        )

    def test_presetup_scrape_does_not_replace_full_course_urls(self) -> None:
        import tempfile
        from scrape_course_urls import ArtifactStore, ProgressStore

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            artifacts = ArtifactStore(output_dir)
            artifacts.write_course_urls(
                [
                    "https://example.ac.uk/courses/full-1",
                    "https://example.ac.uk/courses/full-2",
                    "https://example.ac.uk/courses/full-3",
                ]
            )
            mapping = UrlLevelMap()
            mapping.add("https://example.ac.uk/courses/full-1", "undergraduate", "UNDERGRADUATE")
            mapping.add("https://example.ac.uk/courses/full-2", "undergraduate", "UNDERGRADUATE")
            mapping.add("https://example.ac.uk/courses/full-3", "postgraduate", "POSTGRADUATE")

            write_presetup_urls_csv(
                output_dir,
                sample_urls_per_level(mapping, n=2, seed=1),
            )

            full_urls = artifacts.read_course_urls()
            self.assertEqual(len(full_urls), 3)
            presetup_rows = read_presetup_urls_csv(output_dir)
            self.assertEqual(len(presetup_rows), 3)
            self.assertTrue((output_dir / "presetup_urls.csv").is_file())

    def test_select_presetup_download_uses_all_presetup_scrape_urls(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            mapping = UrlLevelMap()
            for index in range(5):
                mapping.add(f"https://example.ac.uk/foundation-{index}", "foundation", "FOUNDATION")
                mapping.add(f"https://example.ac.uk/ug-{index}", "undergraduate", "UNDERGRADUATE")
            write_presetup_urls_csv(output_dir, sample_urls_per_level(mapping, n=5, seed=7))

            courses, seed, source = select_presetup_download_courses(output_dir, sample_size=10, seed=99)
            self.assertEqual(source, PRESETUP_URLS_CSV)
            self.assertEqual(len(courses), 10)
            self.assertEqual(seed, 99)

    def test_select_presetup_download_falls_back_to_stratified_sample(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            mapping = UrlLevelMap()
            for index in range(8):
                mapping.add(f"https://example.ac.uk/foundation-{index}", "foundation", "FOUNDATION")
                mapping.add(f"https://example.ac.uk/ug-{index}", "undergraduate", "UNDERGRADUATE")
            write_level_csvs(output_dir, mapping)

            courses, seed, source = select_presetup_download_courses(output_dir, sample_size=10, seed=42)
            self.assertEqual(source, "full_catalogue")
            self.assertEqual(len(courses), 10)
            self.assertEqual(seed, 42)

    def test_presetup_download_sample_stale_when_scrape_urls_differ(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            mapping = UrlLevelMap()
            for index in range(5):
                mapping.add(f"https://example.ac.uk/foundation-{index}", "foundation", "FOUNDATION")
            scrape_courses = sample_urls_per_level(mapping, n=5, seed=1)
            write_presetup_urls_csv(output_dir, scrape_courses)

            old_urls = [row["course_url"] for row in scrape_courses[:2]]
            self.assertTrue(presetup_download_sample_stale(output_dir, old_urls))
            all_urls = [row["course_url"] for row in scrape_courses]
            self.assertFalse(presetup_download_sample_stale(output_dir, all_urls))


if __name__ == "__main__":
    unittest.main()
