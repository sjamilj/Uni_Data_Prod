# University of Hertfordshire

**Catalogue type:** CourseHub / hierarchical (`HIERARCHICAL_PROGRAMME` in `shared/University Course Catalogue Structure.md`).

| Level | UG | PG (masters) |
|-------|----|----------------|
| Degree hub (save HTML, not scrape) | `course_listing/undergraduate-hub.html` ← https://www.herts.ac.uk/courses/undergraduate-courses | https://www.herts.ac.uk/courses/postgraduate-masters-study |
| Subject listing (one URL per scrape run) | `…/undergraduate-courses/{subject}` | `…/postgraduate-masters-study/{subject}` |
| Course page | `…/courses/undergraduate/{slug}` | `…/courses/postgraduate-masters/{slug}` or `…/courses/research/{slug}` |

## URL scrape (full catalogue)

`STRATEGY=DEGREE_SCOPED_PAGINATED` — listing seeds from `DegreeScopedPaginated.csv` / `code/.env` (`*_COURSE_LISTING_PAGE_1/2`).  
Intake month is the `courseStartDate=` facet (`september` in the CSV template). Set **`COURSE_LISTING_START_DATE`** (or `--listing-start-date`) to switch month without editing every URL.

```powershell
cd "University of Hertfordshire\code"
python "..\..\shared\scrape_course_urls.py" . --fresh
# January intake merge (same .env URLs; overrides month):
python "..\..\shared\scrape_course_urls.py" . --append-urls --listing-start-date january
```

Per-level `*_course_urls.csv` files include **`listing_intake_month`** (`september`, `january`, …). The same `course_url` can appear on **two rows** when it was found on both intake searches. `course_urls.csv` stays **one row per URL** (single download / one LLM pass); course pages should still list all start months in **`intakeInfo`** after extract.

Cloudflare: **[code/CLOUDFLARE-CDP.md](code/CLOUDFLARE-CDP.md)** (copy-paste steps). Shared reference: [docs/shared/cloudflare-course-download.md](../docs/shared/cloudflare-course-download.md).

Legacy manual loop: `code/ug_subject_listings.txt` + `--append-urls` per subject (no longer required when hub URLs are set).

## Manual HTML still needed

- `uni_req/*.html` — fill requirement URLs in `DegreeScopedHierarchical.csv`
- `course_listing/` — hub + one subject page per level
- `course_detail/` — sample UG/PG course pages from `DegreeScopedHierarchical.generated.csv`

**CSV:** `DegreeScopedHierarchical.csv` = intake sheet (CourseHub / hierarchical). After `build_university_from_template.py`, listing export is `DegreeScopedHierarchical.generated.csv` (`STRATEGY` remains `DEGREE_SCOPED_PAGINATED`).
