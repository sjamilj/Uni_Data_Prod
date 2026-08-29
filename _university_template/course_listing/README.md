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
