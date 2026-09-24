# University of East Anglia (unit-32 / uea)

| Item | Value |
|------|--------|
| Registry | `unit-32` · slug `uea` |
| Strategy | `DEGREE_SCOPED_PAGINATED` · `Paginated.csv` |
| Pagination | `LISTING_PAGINATION_MODE=click` (Next button; listing URL does not change) |
| Cloudflare | None — normal Playwright |
| Base URL | https://www.uea.ac.uk |

## Listing

Course finder: [Find your course](https://www.uea.ac.uk/search/courses). Results load in-page. Clicking **Next Page** (`button[aria-label="Next Page"]`) replaces the course cards; the address bar stays on `/search/courses`.

| Programme | Listing URL |
|-----------|-------------|
| All (used) | https://www.uea.ac.uk/search/courses |
| Undergraduate (optional) | https://www.uea.ac.uk/search/courses/undergraduate |
| Postgraduate taught (optional) | https://www.uea.ac.uk/search/courses/postgraduate-taught |

Course detail paths: `/course/undergraduate/{slug}` and `/course/postgraduate/{slug}`.

Save `course_listing/pagination.html` when tuning the Next-button markup.

## Next (operator)

1. Save `uni_req/*.html` from the URLs in `code/ENV.MD`
2. Save sample `course_detail/*.html` (UG + PG)
3. Scrape course URLs, then 5-course presetup

```powershell
python shared/scrape_course_urls.py --code-dir "University of East Anglia/code" --fresh
```
