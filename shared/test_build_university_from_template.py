#!/usr/bin/env python3
"""Tests for Template.csv → .env generator."""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from build_university_from_template import (  # noqa: E402
    EnvFilePatcher,
    StrategyResolver,
    TemplateCsvParser,
    UniversityFromTemplateBuilder,
)


def _write_template(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class StrategyDetectionTests(unittest.TestCase):
    def test_aru_degree_scoped_paginated(self) -> None:
        config = TemplateCsvParser.parse_file(_FIXTURES / "aru_template.csv")
        self.assertEqual(StrategyResolver.auto_detect(config), "DegreeScopedPaginated.csv")
        self.assertEqual(StrategyResolver.resolve(config), "DegreeScopedPaginated.csv")

    def test_essex_paginated_single_scope(self) -> None:
        config = TemplateCsvParser.parse_file(_FIXTURES / "essex_template.csv")
        self.assertEqual(StrategyResolver.auto_detect(config), "Paginated.csv")

    def test_aston_all_course_single_scope(self) -> None:
        config = TemplateCsvParser.parse_file(_FIXTURES / "aston_template.csv")
        self.assertEqual(StrategyResolver.auto_detect(config), "ALL_COURSE.csv")

    def test_hull_degree_scoped_all_course(self) -> None:
        config = TemplateCsvParser.parse_file(_FIXTURES / "hull_template.csv")
        self.assertEqual(StrategyResolver.auto_detect(config), "DegreeScopedALLCourse.csv")

    def test_explicit_mismatch_warns(self) -> None:
        config = TemplateCsvParser.parse_file(_FIXTURES / "aru_template.csv")
        config.explicit_variant = "Paginated.csv"
        variant = StrategyResolver.resolve(config)
        self.assertEqual(variant, "Paginated.csv")
        self.assertTrue(any("suggests" in w for w in config.warnings))


class EnvMappingTests(unittest.TestCase):
    def test_aru_env_keys(self) -> None:
        config = TemplateCsvParser.parse_file(_FIXTURES / "aru_template.csv")
        skeleton = (_FIXTURES / "env_skeleton.md").read_text(encoding="utf-8")
        patched = EnvFilePatcher.patch(skeleton, config, "DegreeScopedPaginated.csv")
        self.assertIn("STRATEGY=DEGREE_SCOPED_PAGINATED", patched)
        self.assertIn(
            "UNDERGRADUATE_COURSE_LISTING_PAGE_1=https://www.aru.ac.uk/study/undergraduate",
            patched,
        )
        self.assertIn("FOUNDATION_COURSE_LISTING_PAGE_1=", patched)
        self.assertIn("bangladesh-entry :: https://www.aru.ac.uk/international/south-asia", patched)

    def test_aston_all_course_keys(self) -> None:
        config = TemplateCsvParser.parse_file(_FIXTURES / "aston_template.csv")
        skeleton = (_FIXTURES / "env_skeleton.md").read_text(encoding="utf-8")
        patched = EnvFilePatcher.patch(skeleton, config, "ALL_COURSE.csv")
        self.assertIn("STRATEGY=ALL_COURSE", patched)
        self.assertIn("COURSE_CATALOGUE_URL=https://www.aston.ac.uk/courses-atoz", patched)
        self.assertIn("COURSE_CATALOGUE_HTML=../course_listing/all_course.html", patched)


class BuildIntegrationTests(unittest.TestCase):
    def test_build_writes_dotenv_and_variant_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            uni = root / "Test University - TU"
            uni.mkdir()
            shutil_copy_template(uni / "Template.csv", _FIXTURES / "aru_template.csv")
            (uni / "code").mkdir()
            (uni / "code" / "ENV.MD").write_text(
                (_FIXTURES / "env_skeleton.md").read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            builder = UniversityFromTemplateBuilder(root)
            result = builder.build(template_csv=uni / "Template.csv")

            self.assertTrue(result["dotenv"].is_file())
            self.assertTrue(result["variant_csv"].is_file())
            self.assertEqual(result["variant_csv"].name, "DegreeScopedPaginated.csv")

            with result["variant_csv"].open(encoding="utf-8-sig") as handle:
                rows = list(csv.reader(handle))
            self.assertEqual(rows[0][0], "uniName")
            self.assertGreater(len(rows), 2)


def shutil_copy_template(dest: Path, src: Path) -> None:
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


_FIXTURES = Path(__file__).resolve().parent / "test_fixtures" / "build_university_from_template"


if __name__ == "__main__":
    unittest.main()
