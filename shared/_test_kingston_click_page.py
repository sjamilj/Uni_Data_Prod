"""Quick verify Kingston click pagination for pages 1-3."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scrape_course_urls import (
    BrowserSession,
    CourseUrlMatcher,
    EnvFile,
    ListingResultParser,
    MatchingRulesLoader,
)

env_path = Path(__file__).resolve().parent.parent / "Kingston University" / "code" / ".env"
env = EnvFile(env_path)
matching = MatchingRulesLoader.load(env, env_path)
matcher = CourseUrlMatcher("www.kingston.ac.uk", matching)
base = "https://www.kingston.ac.uk"
url1 = (
    "https://www.kingston.ac.uk/study/course-search"
    "?course_type=1&course_type=2&course_type=14&page=1"
)

with BrowserSession() as browser:
    _title, html1 = browser.download_html(url1, wait_for_results=True)
    urls1 = matcher.extract_from_html(html1, base)
    start1, end1, total1 = ListingResultParser.get_result_info(html1)
    print("page1", len(urls1), (start1, end1, total1), sorted(urls1)[:2])

    first1 = sorted(urls1)[0] if urls1 else None
    _title, html2 = browser.click_next_listing_page(
        expected_start=(end1 or 10) + 1,
        previous_first_href=first1,
    )
    urls2 = matcher.extract_from_html(html2, base)
    start2, end2, _ = ListingResultParser.get_result_info(html2)
    overlap = len(urls1 & urls2)
    print("page2", len(urls2), (start2, end2), "overlap", overlap, browser.is_cloudflare_challenge(_title, html2))
    print(" page2 sample", sorted(urls2)[:2])

    first2 = sorted(urls2)[0] if urls2 else None
    _title, html3 = browser.click_next_listing_page(
        expected_start=(end2 or 20) + 1,
        previous_first_href=first2,
    )
    urls3 = matcher.extract_from_html(html3, base)
    start3, end3, _ = ListingResultParser.get_result_info(html3)
    print("page3", len(urls3), (start3, end3), "overlap12", len(urls2 & urls3), browser.is_cloudflare_challenge(_title, html3))
    print(" page3 sample", sorted(urls3)[:2])
    if len(urls1) >= 8 and len(urls2) >= 8 and overlap == 0 and start2 == 11:
        print("OK click pagination works")
    else:
        raise SystemExit("FAIL click pagination")
