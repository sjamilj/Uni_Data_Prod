# University of Salford

Registry: **unit-23 / salford** (`feat(unit-23/salford): …`)

## Strategy

`DEGREE_SCOPED_PAGINATED` — one international full-time [course search](https://www.salford.ac.uk/search/courses) listing; study level from URL path (`/courses/undergraduate/`, `/courses/postgraduate/`, `/courses/postgraduate-researchdoctorate/`).

Operator CSV: `Template.csv`, `Paginated.csv`.

## Samples

| Folder | Purpose |
|--------|---------|
| `course_listing/paginated_course.html` | Saved search results (international + full-time) |
| `course_detail/course-details.html` | Sample PGT course (`#overview`, `#requirement`, `#fees`) |
| `uni_req/` | Bangladesh, English requirements HTML |

## Commands (from repo root)

```powershell
python shared/scrape_course_urls.py --code-dir "University of Salford/code" --fresh
python shared/run_course_pipeline.py --code-dir "University of Salford/code" --presetup
python shared/validate_uni_clean.py --code-dir "University of Salford/code"
```

Commit: `.\scripts\commit-uni.cmd -Pick salford -Type feat -WithShared`
