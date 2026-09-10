#!/usr/bin/env python3
"""Tests for degree_name_inference."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from degree_name_inference import (  # noqa: E402
    DegreeInferenceInput,
    DegreeNameInferrer,
    apply_degree_to_course_dir,
    canonicalize_degree_name,
    find_course_markdown,
    infer_degree_heuristic,
    markdown_excerpt_for_degree,
)


class DegreeNameInferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.output_dir = self.root / "output"
        self.courses_dir = self.output_dir / "clean" / "courses" / "undergraduate"
        self.courses_dir.mkdir(parents=True)
        self.slug = "study-undergraduate-undergraduatecourses-msc-data-science"
        self.md_path = self.courses_dir / f"{self.slug}.md"
        self.md_path.write_text(
            "---\nstudy_level: undergraduate\ncourse_url: https://example.ac.uk/msc\n---\n"
            "# MSc Data Science\n\n## Key information\n\n- Award MSc\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_find_course_markdown(self) -> None:
        found = find_course_markdown(self.output_dir, self.slug)
        self.assertEqual(found, self.md_path)

    def test_markdown_excerpt_for_degree(self) -> None:
        excerpt = markdown_excerpt_for_degree(self.md_path.read_text(encoding="utf-8"))
        self.assertIn("MSc Data Science", excerpt)
        self.assertIn("Award: MSc", excerpt)

    def test_infer_degree_heuristic_from_course_name(self) -> None:
        self.assertEqual(infer_degree_heuristic("MSc Data Science", ""), "MSc")
        self.assertEqual(infer_degree_heuristic("Accounting and Finance", ""), "")

    def test_infer_degree_heuristic_pgr_default(self) -> None:
        self.assertEqual(
            infer_degree_heuristic("Medicine", "", study_level="postgraduate_research"),
            "PhD",
        )

    def test_canonicalize_degree_name(self) -> None:
        self.assertEqual(canonicalize_degree_name("BSc"), "BSc")
        self.assertIsNone(canonicalize_degree_name("MMath"))

    def test_accept_llm_matches_filters_unknown(self) -> None:
        inferrer = DegreeNameInferrer()
        accepted = inferrer._accepted_llm_matches(
            {"MSc Data Science": "BSc", "Bad Course": "MMath"},
            ["MSc Data Science", "Bad Course"],
        )
        self.assertEqual(accepted, {"MSc Data Science": "BSc"})

    @patch("ollama_client.chat")
    def test_infer_with_llm(self, mock_chat) -> None:
        mock_chat.return_value = (
            {"MSc Data Science": "MSc"},
            {},
        )
        inferrer = DegreeNameInferrer()
        picks = inferrer.infer_with_llm(
            [
                DegreeInferenceInput(
                    course_name="MSc Data Science",
                    study_level="postgraduate",
                    md_excerpt="title: MSc Data Science",
                    slug=self.slug,
                    course_dir=self.output_dir,
                )
            ]
        )
        self.assertEqual(picks, {"MSc Data Science": "MSc"})

    def test_apply_degree_to_course_dir(self) -> None:
        course_dir = self.output_dir / "extracted" / "postgraduate" / self.slug
        course_dir.mkdir(parents=True)
        output_json = {
            "courseName": "MSc Data Science",
            "courseUrl": "https://example.ac.uk/msc",
            "requirements": [{"degree": "BSc", "grade": "CGPA 3.0"}],
        }
        (course_dir / "output.json").write_text(json.dumps(output_json), encoding="utf-8")
        (course_dir / "stage1_parsed.json").write_text(json.dumps({}), encoding="utf-8")

        self.assertTrue(apply_degree_to_course_dir(course_dir, "MSc"))
        patched = json.loads((course_dir / "output.json").read_text(encoding="utf-8"))
        self.assertEqual(patched["degreeName"], "MSc")
        self.assertTrue((course_dir / "normalized.json").is_file())


if __name__ == "__main__":
    unittest.main()
