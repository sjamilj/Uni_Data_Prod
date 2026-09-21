# course_listing/

Save browser snapshots of course listing / catalogue pages.

## UEA: Next-button pagination (URL does not change)

Live listing: [Find your course](https://www.uea.ac.uk/search/courses)

The pager is in-page. Numbered buttons exist, but scraping uses the **Next Page** control (`aria-label="Next Page"`). Visiting `?page=2` is not required.

In `code/.env`:

```
STRATEGY=DEGREE_SCOPED_PAGINATED
COURSE_LISTING_PAGE_1=https://www.uea.ac.uk/search/courses
LISTING_PAGINATION_MODE=click
LISTING_CLICK_NEXT_SELECTOR=button[aria-label="Next Page"]
LISTING_AJAX_WAIT_SELECTOR=a[href*="/course/"]
COURSE_LINK_SELECTOR=a[href*="/course/"]
```

Optional reference save: `pagination.html` (listing page with the pager visible). The scraper follows the live URL; it does not read this file unless you point another key at it.

Optional degree-scoped listing URLs (same Next-button widget):

- Undergraduate: https://www.uea.ac.uk/search/courses/undergraduate
- Postgraduate taught: https://www.uea.ac.uk/search/courses/postgraduate-taught

## Per programme (reference saves)

| File | Programme |
|------|-----------|
| `undergraduate.html` | Undergraduate |
| `postgraduate.html` | Postgraduate taught |
| `postgraduate-research.html` | Postgraduate research |
| `foundation.html` | Foundation year |
| `all_course.html` | Mixed catalogue (same as COURSE_LISTING_PAGE_1) |
