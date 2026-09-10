#!/usr/bin/env python3
"""Tests for export_extracted_audit_csv."""

from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from export_extracted_audit_csv import (  # noqa: E402
    ExtractedAuditCsvExporter,
    entry_requirement_diagnostics,
    requirements_schema_signature,
)


class ExportExtractedAuditCsvTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.uni_name = "Test University - TU"
        self.uni_dir = self.root / self.uni_name
        self.output_dir = self.uni_dir / "output"
        self.extracted = self.output_dir / "extracted" / "postgraduate"
        self.extracted.mkdir(parents=True)

        reviewed = self.output_dir / f"dev_courses_{self.uni_name}_reviewed.csv"
        with reviewed.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "courseName",
                    "courseUrlExternal",
                    "minGpa",
                    "degreeName",
                    "errorReason",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "courseName": "Good MSc",
                    "courseUrlExternal": "https://example.ac.uk/study/postgraduate/courses/good-msc",
                    "minGpa": "3.25",
                    "degreeName": "MSc",
                    "errorReason": "",
                }
            )
            writer.writerow(
                {
                    "courseName": "Broken MSc",
                    "courseUrlExternal": "https://example.ac.uk/study/postgraduate/courses/broken-msc",
                    "minGpa": "",
                    "degreeName": "MSc",
                    "errorReason": "MISSING_REQUIRED_FIELD: missing required field(s): minGpa",
                }
            )

        self._write_entry_json(
            "good-msc",
            {
                "requirements": [{"country": "Bangladesh", "degree": "BSc", "grade": "60%"}],
                "AcademicRequirementsMetaData": [
                    {
                        "subtitle": "Entry Requirements",
                        "description": ["60% in a 4-year degree"],
                    }
                ],
            },
        )
        self._write_entry_json(
            "broken-msc",
            {
                "requirements": [
                    {
                        "country": "Bangladesh",
                        "description": ["Successful completion of a degree"],
                    }
                ],
                "AcademicRequirementsMetaData": [
                    {
                        "subtitle": "Entry Requirements",
                        "description": ["Successful completion of a degree"],
                    }
                ],
            },
        )

        self.exporter = ExtractedAuditCsvExporter(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_entry_json(self, slug: str, payload: dict) -> None:
        course_dir = self.extracted / slug
        course_dir.mkdir(parents=True, exist_ok=True)
        (course_dir / "entry_requirement_parsed.json").write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

    def test_requirements_schema_signature(self) -> None:
        self.assertEqual(
            requirements_schema_signature([{"country": "Bangladesh", "description": ["x"]}]),
            "country,description",
        )
        self.assertEqual(requirements_schema_signature([]), "empty")

    def test_entry_requirement_diagnostics(self) -> None:
        data = {
            "requirements": [{"country": "Bangladesh", "description": ["x"]}],
            "AcademicRequirementsMetaData": [
                {"subtitle": "Entry Requirements", "description": ["Entry text"]}
            ],
        }
        diag = entry_requirement_diagnostics(data, "postgraduate")
        self.assertEqual(diag["req_first_keys"], "country,description")
        self.assertEqual(diag["req_normalized_count"], "0")
        self.assertEqual(diag["entry_text"], "Entry text")

    def test_export_filters_missing_min_gpa(self) -> None:
        output_csv = self.output_dir / "extracted_audit.csv"
        result = self.exporter.export(
            self.uni_name,
            missing_fields=["minGpa"],
            missing_any=[],
            json_files=["entry_requirement_parsed.json"],
            explicit_paths=[],
            all_courses=False,
            output=output_csv,
            force=True,
        )
        self.assertEqual(result, output_csv)

        with output_csv.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["courseName"], "Broken MSc")
        self.assertEqual(row["reviewed_minGpa"], "")
        self.assertEqual(row["entry_requirement_parsed__req_first_keys"], "country,description")
        self.assertEqual(row["entry_requirement_parsed__req_normalized_count"], "0")
        self.assertIn("Successful completion", row["entry_requirement_parsed__entry_text"])


if __name__ == "__main__":
    unittest.main()
