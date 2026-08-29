# University template

Copy this folder when adding a new university to the F1 pipeline.

```powershell
Copy-Item -Recurse "_university_template" "New University Name - SHORT"
# or:
python "shared\bootstrap_university.py" "New University Name - SHORT"
```

Then rename placeholders, fill `code/ENV.MD` → `code/.env`, and save HTML from the browser.

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
  DegreeScopedPaginated.csv           # master sheet: URLs per programme
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

### `DegreeScopedPaginated.csv`

One row per programme scope. Fill listing URLs, one sample course URL per programme, and uni_req source URLs.

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

- [ ] Copy `_university_template` → `{University Name - SHORT}`
- [ ] Set `UNIVERSITY_NAME`, `UNIVERSITY_BASE_URL`, `STRATEGY` in `code/.env`
- [ ] Fill listing URLs / path patterns / clean selectors in `.env`
- [ ] Save 4 `uni_req/*.html` pages
- [ ] Save `course_listing/` page per programme offered
- [ ] Save `course_detail/` sample per programme offered
- [ ] Complete `DegreeScopedPaginated.csv`
- [ ] Run scrape → download/clean → extract → normalize → export
