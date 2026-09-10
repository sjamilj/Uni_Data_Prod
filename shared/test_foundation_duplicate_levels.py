#!/usr/bin/env python3
"""Tests for foundation/undergraduate duplicate level handling."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from degree_name_inference import (  # noqa: E402
    read_degree_name_from_course_dir,
    sync_degree_name_for_slug,
)
from export_dev_courses import DevCoursesExporter  # noqa: E402
from study_level import (  # noqa: E402
    StudyLevelClassifier,
    UrlLevelMap,
    collapse_duplicate_foundation_undergraduate_levels,
)


class FoundationDuplicateLevelTests(unittest.TestCase):
    def test_collapse_duplicate_levels_prefers_undergraduate_for_ug_url(self) -> None:
        url = "https://www.keele.ac.uk/study/undergraduate/undergraduatecourses/accountingandfinance"
        classifier = StudyLevelClassifier.from_env_lists(
            {"undergraduate": [r"^/study/undergraduate/"], "foundation": [r"foundation"]}
        )
        collapsed = collapse_duplicate_foundation_undergraduate_levels(
            url,
            ["foundation", "undergraduate"],
            classifier=classifier,
        )
        self.assertEqual(collapsed, ["undergraduate"])

    def test_dedupe_index_rows_keeps_foundation_and_undergraduate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            url = "https://www.keele.ac.uk/study/undergraduate/undergraduatecourses/accountingandfinance"
            rows = [
                {
                    "courseUrlExternal": url,
                    "study_level": "foundation",
                    "md_file": "foundation/study-undergraduate-undergraduatecourses-accountingandfinance.md",
                },
                {
                    "courseUrlExternal": url,
                    "study_level": "undergraduate",
                    "md_file": "undergraduate/study-undergraduate-undergraduatecourses-accountingandfinance.md",
                },
            ]
            selected = DevCoursesExporter.dedupe_index_rows_for_export(output_dir, rows)
            levels = sorted(row["study_level"] for row in selected)
            self.assertEqual(levels, ["foundation", "undergraduate"])

    def test_sync_degree_name_does_not_copy_between_levels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            slug = "study-undergraduate-undergraduatecourses-animation"
            foundation_dir = output_dir / "extracted" / "foundation" / slug
            ug_dir = output_dir / "extracted" / "undergraduate" / slug
            foundation_dir.mkdir(parents=True)
            ug_dir.mkdir(parents=True)
            (foundation_dir / "normalized.json").write_text(
                json.dumps({"courseName": "Animation", "degreeName": "BSc"}),
                encoding="utf-8",
            )
            (ug_dir / "normalized.json").write_text(
                json.dumps({"courseName": "Animation", "degreeName": ""}),
                encoding="utf-8",
            )
            self.assertFalse(sync_degree_name_for_slug(output_dir, slug))
            self.assertEqual(read_degree_name_from_course_dir(ug_dir), "")
            self.assertEqual(read_degree_name_from_course_dir(foundation_dir), "BSc")


if __name__ == "__main__":
    unittest.main()
