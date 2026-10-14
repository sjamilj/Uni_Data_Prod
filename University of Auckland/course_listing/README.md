# course_listing/

Save browser snapshots of course listing / catalogue pages.

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
