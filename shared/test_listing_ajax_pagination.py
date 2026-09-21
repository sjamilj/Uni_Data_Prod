#!/usr/bin/env python3
"""Tests for AJAX course-search listing pagination helpers."""

import unittest

from listing_ajax_pagination import (
    beds_listing_level_checkbox_ids,
    listing_page_resume_key,
    parse_umbraco_course_search_meta,
)


class TestUmbracoCourseSearchMeta(unittest.TestCase):
    SAMPLE = """
    <div class="search-results-found pb-4 mb-4 border-bottom">
        Showing page
        <strong>1</strong> of
        <strong>22</strong> (Courses
        <strong>1</strong> -
        <strong>10</strong> of
        <strong>218</strong>)
    </div>
    """

    def test_parse_meta(self) -> None:
        current, total_pages, start, end, total = parse_umbraco_course_search_meta(self.SAMPLE)
        self.assertEqual((current, total_pages, start, end, total), (1, 22, 1, 10, 218))

    def test_resume_key(self) -> None:
        self.assertEqual(
            listing_page_resume_key(
                "https://www.beds.ac.uk/howtoapply/courses/postgraduate/",
                3,
                scope="POSTGRADUATE",
            ),
            "https://www.beds.ac.uk/howtoapply/courses/postgraduate#scope=postgraduate&page=3",
        )

    def test_beds_postgraduate_filter_id(self) -> None:
        ids = beds_listing_level_checkbox_ids(
            "https://www.beds.ac.uk/howtoapply/courses/postgraduate/",
            "POSTGRADUATE",
        )
        self.assertEqual(ids, ["Postgraduate_313908"])


if __name__ == "__main__":
    unittest.main()
