#!/usr/bin/env python3
"""Tests for review package script."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from package_review_output import REVIEW_DIR_NAME, ReviewPackageBuilder  # noqa: E402


class ReviewPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.uni_name = "Test University - TU"
        self.uni_dir = self.root / self.uni_name
        self.uni_dir.mkdir()
        (self.uni_dir / "DegreeScopedPaginated.csv").write_text("uniName\n", encoding="utf-8")
        output_dir = self.uni_dir / "output"
        output_dir.mkdir()
        reviewed = output_dir / f"dev_courses_{self.uni_name}_reviewed.csv"
        reviewed.write_text("courseName\n", encoding="utf-8")
        self.builder = ReviewPackageBuilder(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_package_copies_both_files(self) -> None:
        result = self.builder.package(self.uni_name)

        self.assertTrue(result.variant_csv.is_file())
        self.assertTrue(result.reviewed_csv.is_file())
        self.assertEqual(
            result.review_dir,
            self.root / REVIEW_DIR_NAME / self.uni_name,
        )
        self.assertEqual(result.variant_csv.name, "DegreeScopedPaginated.csv")
        self.assertEqual(
            result.reviewed_csv.name,
            f"dev_courses_{self.uni_name}_reviewed.csv",
        )

    def test_missing_reviewed_csv_raises(self) -> None:
        (self.uni_dir / "output" / f"dev_courses_{self.uni_name}_reviewed.csv").unlink()
        with self.assertRaises(FileNotFoundError):
            self.builder.package(self.uni_name)

    def test_missing_variant_csv_raises(self) -> None:
        (self.uni_dir / "DegreeScopedPaginated.csv").unlink()
        with self.assertRaises(FileNotFoundError):
            self.builder.package(self.uni_name)

    def test_multiple_variant_csvs_raises(self) -> None:
        (self.uni_dir / "Paginated.csv").write_text("uniName\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.builder.package(self.uni_name)

    def test_dry_run_does_not_write(self) -> None:
        result = self.builder.package(self.uni_name, dry_run=True)
        self.assertFalse(result.review_dir.exists())

    def test_force_overwrites_existing(self) -> None:
        self.builder.package(self.uni_name)
        result = self.builder.package(self.uni_name, force=True)
        self.assertTrue(result.variant_csv.is_file())
        self.assertTrue(result.reviewed_csv.is_file())


if __name__ == "__main__":
    unittest.main()
