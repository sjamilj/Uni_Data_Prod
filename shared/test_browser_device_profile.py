#!/usr/bin/env python3
"""Tests for shared/browser_device_profile.py (CDP + device profile config)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from browser_device_profile import (  # noqa: E402
    CourseDownloadBrowserConfig,
    is_cloudflare_challenge_page,
)


class CourseDownloadBrowserConfigTests(unittest.TestCase):
    def test_cdp_url_takes_precedence_over_device_profile_flag(self) -> None:
        config = CourseDownloadBrowserConfig.from_env(
            {
                "COURSE_DOWNLOAD_CDP_URL": "http://127.0.0.1:9222",
                "COURSE_DOWNLOAD_USE_DEVICE_PROFILE": "true",
            }
        )
        self.assertEqual(config.cdp_url, "http://127.0.0.1:9222")
        self.assertTrue(config.use_device_profile)

    def test_headless_and_cloudflare_wait_from_env(self) -> None:
        config = CourseDownloadBrowserConfig.from_env(
            {
                "COURSE_DOWNLOAD_HEADLESS": "false",
                "COURSE_DOWNLOAD_CLOUDFLARE_WAIT_SECONDS": "300",
            }
        )
        self.assertFalse(config.headless)
        self.assertEqual(config.cloudflare_wait_seconds, 300)


class CloudflareDetectionTests(unittest.TestCase):
    def test_detects_title_marker(self) -> None:
        self.assertTrue(
            is_cloudflare_challenge_page("Just a moment...", "<html></html>")
        )

    def test_normal_course_page(self) -> None:
        self.assertFalse(
            is_cloudflare_challenge_page(
                "BSc Accounting",
                "<html><body>Entry requirements</body></html>",
            )
        )


if __name__ == "__main__":
    unittest.main()
