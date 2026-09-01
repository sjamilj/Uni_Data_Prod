# University template

Copy this folder when adding a new university to the F1 pipeline.

```powershell
Copy-Item -Recurse "_university_template" "New University Name - SHORT"
# or:
python "shared\bootstrap_university.py" "New University Name - SHORT"
```

**Recommended:** fill `Template.csv`, then generate `code/.env` and the variant CSV:

```powershell
python shared\build_university_from_template.py --university "New University Name - SHORT" --bootstrap
```

Or, if the folder already exists:

```powershell
python shared\build_university_from_template.py --template-csv "New University Name - SHORT\Template.csv"
```

Then save HTML from the browser (uni_req, course_listing, course_detail) and tune path patterns in `.env`.

## Template.csv → `.env` workflow

`Template.csv` is the single intake sheet. Row 1 column B names the variant schema; rows 2–3 set university identity; rows 5–9 hold listing and requirement URLs.

| Row | Purpose |
|-----|---------|
| 1 | Strategy hint — one of `ALL_COURSE.csv`, `Paginated.csv`, `DegreeScopedALLCourse.csv`, `DegreeScopedPaginated.csv` |
| 2 | `Uni Name` → `UNIVERSITY_NAME` |
| 3 | `Uni Link` → `UNIVERSITY_BASE_URL` |
| 4 | Column headers (shared across variants) |
| 5 `All` | Single-scope university (one listing for all programmes) |
| 6–9 | Per programme: Foundation, Undergraduate, Postgraduate, Postgraduate Research |

The generator (`shared/build_university_from_template.py`) reads `Template.csv`, auto-detects strategy when row 1 is blank or mismatched (with a warning), and writes:

- `code/.env` (and `code/ENV.MD`) — `STRATEGY`, listing keys, `UNI_REQ_SOURCE_URLS`
- `{Variant}.csv` at university root — e.g. `DegreeScopedPaginated.csv`

**Phase 1 does not download HTML.** Operators still browser-save `uni_req/`, `course_listing/`, and `course_detail/` manually.

### Strategy matrix

| Variant CSV | Rows used | `STRATEGY` in `.env` | Listing env keys |
|-------------|-----------|----------------------|------------------|
| `ALL_COURSE.csv` | Row 5 `All` only | `ALL_COURSE` | `COURSE_CATALOGUE_URL`, `COURSE_CATALOGUE_HTML` |
| `Paginated.csv` | Row 5 `All` only | `DEGREE_SCOPED_PAGINATED` | `COURSE_LISTING_PAGE_1/2` |
| `DegreeScopedALLCourse.csv` | Rows 6–9 | `ALL_COURSE` | `{SCOPE}_COURSE_CATALOGUE_*` |
| `DegreeScopedPaginated.csv` | Rows 6–9 | `DEGREE_SCOPED_PAGINATED` | `{SCOPE}_COURSE_LISTING_PAGE_*` |

Schema-only variant CSVs live in `_university_template/` as column references. Examples: ARU → `DegreeScopedPaginated.csv`; Essex → `Paginated.csv`; Aston → `ALL_COURSE.csv`; Hull → `DegreeScopedALLCourse.csv`.

After generation, optionally merge `code/env/*.env` fragments:

```powershell
python shared\build_env.py --code-dir "New University Name - SHORT\code"
```

## Folder layout

```
{University Name - SHORT}/
  code/
    .env                              # secrets + config (copy from ENV.MD; never commit)
    ENV.MD                            # committed config template
    download_and_clean_course_pages.py  # thin wrapper → shared/
    course_markdown_cleanup.py          # thin wrapper → shared/
  uni_req/                            # university-wide requirement pages (fixed filenames)
  course_listing/                     # saved listing/catalogue pages (all_course or per programme)
  course_detail/                      # saved sample course pages (per programme + layout probe)
  DegreeScopedPaginated.csv           # generated from Template.csv (or legacy master sheet)
  Template.csv                        # intake sheet → run build_university_from_template.py
  Claude_Output/                      # scratch / experiments (gitignored)
  output/                             # generated artifacts (created by pipeline)
```

## Naming rules

### University folder + `.env`

| Item | Format | Example |
|------|--------|---------|
| Folder name | `{Full Name} - {SHORT}` | `Anglia Ruskin University - ARU` |
| `UNIVERSITY_NAME` | Same as folder name | `Anglia Ruskin University - ARU` |
| `UNIVERSITY_BASE_URL` | `https://www.{domain}` | `https://www.aru.ac.uk` |

`UNIVERSITY_NAME` is required in `code/.env` only.

### `uni_req/` — fixed filenames (do not rename)

Save each page from the browser using **exactly** these names:

| File | Purpose |
|------|---------|
| `bangladesh-entry.html` | Country / South Asia entry requirements |
| `english-requirements.html` | English language requirements |
| `scholarships.html` | International scholarships |
| `deposit.html` | Tuition fee deposit / how to pay |

Cleaned output: `output/clean/uni/{same-stem}.md`

### `course_listing/` — catalogue pages

**Single catalogue (all programmes on one page):**

| File | Use |
|------|-----|
| `all_course.html` | Full course catalogue — use with `STRATEGY=ALL_COURSE` and `COURSE_CATALOGUE_HTML=` |

**Per programme** (degree-scoped catalogues or listing reference):

| Programme | Short filename |
|-----------|----------------|
| Undergraduate | `undergraduate.html` |
| Postgraduate taught | `postgraduate.html` |
| Postgraduate research | `postgraduate-research.html` |
| Foundation | `foundation.html` |

**Paginated strategies** (`Paginated.csv`, `DegreeScopedPaginated.csv`): also keep an optional `pagination.html` — a browser-saved listing page with visible pager controls, for studying pagination markup. Live `*_COURSE_LISTING_PAGE_*` URLs in `.env` drive scraping.

Use **either** short env names **or** browser-save titles. Pick one style per university and stay consistent.

**Style A — short (ALL_COURSE / catalogue HTML paths in `.env`):**

See table above plus `all_course.html` for single-catalogue universities.

**Style B — browser title (ARU example, per programme):**

| Programme | Example filename |
|-----------|------------------|
| Undergraduate | `Undergraduate courses 2026 - ARU.html` |
| Postgraduate taught | `Postgraduate Courses- ARU.html` |
| Foundation | `Foundation Year_courses 2026 - ARU.html` |

If using Style B, set `UNDERGRADUATE_COURSE_CATALOGUE_HTML` etc. in `.env` to the full path of each saved file.

### `course_detail/` — sample course per programme

Save **one real course page per programme** to tune `COURSE_CLEAN_BLOCKS` in `.env`.

**General pattern:**

```
{Course Title} - {Award} - {SHORT}.html
```

| Programme | Example (ARU) |
|-----------|----------------|
| Undergraduate | `Animation and Illustration - BA (Hons) - ARU.html` |
| Postgraduate taught | `Artificial Intelligence - MSc - ARU.html` |
| Postgraduate research | `Postgraduate Research_Allied Health and Social Care - MPhil, PhD - ARU.html` |
| Foundation | `Biomedical Engineering Foundation - BEng (Hons) - ARU.html` |

Template stubs use `sample-*.html` names until you replace them with real browser saves.

Also keep `course-details.html` as a generic layout reference if the site uses one shared course template.

### `DegreeScopedPaginated.csv` (and other variants)

One row per programme scope (for degree-scoped variants). Fill listing URLs, one sample course URL per programme, and uni_req source URLs.

Prefer filling `Template.csv` and running `build_university_from_template.py` — it writes the correct variant file at the university root.

## Pipeline (from `code/`)

```powershell
# 1. Scrape course URLs
python "..\..\shared\scrape_course_urls.py" .

# 2. Download + clean courses (uni_req separate)
python download_and_clean_course_pages.py --limit 5
python download_and_clean_course_pages.py --clean-uni-only

# 3. LLM extract
python "..\..\shared\llm_extract.py" . --limit 5

# 4. Normalize + export dev CSV
python "..\..\shared\normalize_admission_data.py" .
python "..\..\shared\export_dev_courses.py" .
```

## Checklist for a new university

- [ ] Copy `_university_template` → `{University Name - SHORT}` (or `--bootstrap`)
- [ ] Fill `Template.csv` (row 1 variant, rows 2–3 identity, rows 5–9 URLs)
- [ ] Run `python shared/build_university_from_template.py --university "{University Name - SHORT}"`
- [ ] Optionally merge `code/env/*.env` with `build_env.py`
- [ ] Tune `COURSE_PATH_PATTERNS` and `COURSE_CLEAN_BLOCKS` in `.env`
- [ ] Save 4 `uni_req/*.html` pages
- [ ] Save `course_listing/` page per programme offered
- [ ] Save `course_detail/` sample per programme offered
- [ ] Run scrape → download/clean → extract → normalize → export
