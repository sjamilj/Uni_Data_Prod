# course_listing/

Save browser snapshots of course listing / catalogue pages.

## Bedfordshire: AJAX pagination (URL does not change)

Listing URLs such as [Postgraduate courses](https://www.beds.ac.uk/howtoapply/courses/postgraduate/) stay on the same path while results paginate. Reference save: `pagination.html` (from that URL).

### What happens on page button click

Handled in `pagination_files/coursesearch.js.download`:

```21:25:University of Bedfordshire/course_listing/pagination_files/coursesearch.js.download
    $(document).on('click', '.page-link', function () {
        var requiredPage = $(this).data('page');
        $('#current-page').val(requiredPage);
        submitSearch();
    });
```

Every pagination control uses class `page-link` and `data-page="N"` (numbered buttons and the **Next** arrow with `course-search-page-link`). There is no `?page=` navigation.

`submitSearch()` serializes `#course-search-form` and **POST**s to:

`https://www.beds.ac.uk/umbraco/Surface/CourseSearchResult/DoCourseSearch`

The JSON response body is **HTML**; it replaces `#course-search-results` (course cards + pagination markup). Hidden field `#current-page` / `name="CurrentPage"` carries the page index (`PageSize` is `10` in the saved form).

The form also includes filter checkboxes (`CourseLevels[n].Selected`, `Modes`, locations, etc.), `SearchQuery`, and `__RequestVerificationToken` — the same payload must be replayed when incrementing `CurrentPage`.

### Scrape (shared)

In `code/.env`:

```
LISTING_PAGINATION_MODE=ajax_click
LISTING_AJAX_WAIT_SELECTOR=a.search-results__title__link
LISTING_AJAX_PAGE_BUTTON_SELECTOR=.pagination button.page-link[data-page="{page}"]
UNDERGRADUATE_LISTING_AJAX_LEVEL_CHECKBOX_IDS=Undergraduate_313909
POSTGRADUATE_LISTING_AJAX_LEVEL_CHECKBOX_IDS=Postgraduate_313908
POSTGRADUATE_RESEARCH_LISTING_AJAX_LEVEL_CHECKBOX_IDS=Postgraduate Research Scheme_439549
FOUNDATION_LISTING_AJAX_LEVEL_CHECKBOX_IDS=Undergraduate_313909
FOUNDATION_LISTING_AJAX_VARIANT_CHECKBOX_IDS=with Foundation Year_1519
*_LISTING_AJAX_MODE_CHECKBOX_IDS=Full-time_614
COURSE_LINK_SELECTOR=a.search-results__title__link
```

Each active `*_COURSE_LISTING_PAGE_1` in `.env` runs: **goto → apply level / variant / mode from that scope’s `*_LISTING_AJAX_*` keys → paginate**. Comment out a scope’s `*_PAGE_1` line to skip it. Progress: `#scope=postgraduate_research&page=2`, etc.

**CDP:** see [code/CLOUDFLARE-CDP.md](../code/CLOUDFLARE-CDP.md) — set `COURSE_DOWNLOAD_CDP_URL=http://127.0.0.1:9222` and pass Cloudflare in Brave before scraping.

`shared/scrape_course_urls.py` opens each `*_COURSE_LISTING_PAGE_1` URL once, then clicks the pager (`DoCourseSearch` POST). Progress keys use `#page=N` because the address bar URL stays fixed.

Course detail links: `https://www.beds.ac.uk/courses/{slug}/` (`a.search-results__title__link`).

## Single catalogue (ALL_COURSE)

When one page lists every course (all programmes together):

| File | Use |
|------|-----|
| `all_course.html` | Full university course catalogue |

In `code/.env`:

```
STRATEGY=ALL_COURSE
COURSE_CATALOGUE_URL=https://www.example.ac.uk/courses
COURSE_CATALOGUE_HTML=E:\...\{University}\course_listing\all_course.html
```

## Paginated listings (DEGREE_SCOPED_PAGINATED)

When courses are discovered via paginated search (not a single catalogue page):

| File | Use |
|------|-----|
| `pagination.html` | **Optional reference** — save a listing page that shows pagination controls (page 2+). For studying markup and tuning `COURSE_LINK_SELECTOR`; not loaded from `.env`. |
| `undergraduate.html`, etc. | Per-programme listing saves (same as below) when degree-scoped |

In `code/.env` set live seed URLs (from `Template.csv`):

```
STRATEGY=DEGREE_SCOPED_PAGINATED
COURSE_LISTING_PAGE_1=https://www.example.ac.uk/courses?page=1
COURSE_LISTING_PAGE_2=https://www.example.ac.uk/courses?page=2
# or per scope: UNDERGRADUATE_COURSE_LISTING_PAGE_1=...
```

Save `pagination.html` from the browser when you need a local copy of the pager UI. The scraper follows live URLs; it does not read this file unless you point another key at it.

## Per programme (degree-scoped ALL_COURSE or reference for DEGREE_SCOPED_PAGINATED)

| File | Programme |
|------|-----------|
| `undergraduate.html` | Undergraduate |
| `postgraduate.html` | Postgraduate taught |
| `postgraduate-research.html` | Postgraduate research |
| `foundation.html` | Foundation year |

Set `UNDERGRADUATE_COURSE_CATALOGUE_HTML=`, `POSTGRADUATE_COURSE_CATALOGUE_HTML=`, etc. in `.env` when using degree-scoped catalogues.

## Browser-save titles (alternative)

Example ARU style (per programme, not `all_course.html`):

- `Undergraduate courses 2026 - SHORT.html`
- `Postgraduate Courses- SHORT.html`
- `Foundation Year_courses 2026 - SHORT.html`

Omit files for programmes the university does not offer.
