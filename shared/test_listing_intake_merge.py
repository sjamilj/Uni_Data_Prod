#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from listing_intake_merge import merge_catalog_months_with_page_intakes  # noqa: E402
from study_level import UrlLevelMap  # noqa: E402
from listing_intake_merge import listing_intake_months_for_url  # noqa: E402


class ListingIntakeMergeTests(unittest.TestCase):
    def test_merge_adds_missing_january_same_year_as_september(self) -> None:
        merged = merge_catalog_months_with_page_intakes(
            "September 2027",
            ["september", "january"],
        )
        self.assertEqual(merged, "September 2027, January 2027")

    def test_merge_corrects_january_year_when_page_has_academic_year_plus_one(self) -> None:
        merged = merge_catalog_months_with_page_intakes(
            "January 2028, September 2027",
            ["september", "january"],
        )
        self.assertEqual(merged, "September 2027, January 2027")

    def test_listing_months_from_url_levels(self) -> None:
        mapping = UrlLevelMap()
        url = "https://www.herts.ac.uk/courses/postgraduate-masters/example"
        mapping.add(url, "postgraduate", "POSTGRADUATE", listing_intake_month="september")
        mapping.add(url, "postgraduate", "POSTGRADUATE", listing_intake_month="january")
        months = listing_intake_months_for_url(url, mapping, study_level="postgraduate")
        self.assertEqual(months, ["september", "january"])


if __name__ == "__main__":
    unittest.main()
