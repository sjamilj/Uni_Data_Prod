# Anglia Ruskin University — ARU

F1 pipeline configuration for [Anglia Ruskin University](https://www.aru.ac.uk).

| Field | Value |
|-------|-------|
| **Folder** | `Anglia Ruskin University - ARU` |
| **Short code** | ARU |
| **Base URL** | `https://www.aru.ac.uk` |
| **Strategy** | `DEGREE_SCOPED_PAGINATED` |
| **CMS / layout** | Sitecore **Utopian** course templates (`#utopian-course-overview`, tabs, accordions) |
| **Portal CSV** | `Anglia Ruskin University - ARU_portal.csv` |

Full pipeline reference: [`../PIPELINE.md`](../PIPELINE.md)

---

## Navigate here

```powershell
Set-Location "e:\Project Next\UK UNIVERSITIES\F1\Anglia Ruskin University - ARU"
Set-Location ".\code"   # run all pipeline commands from here
```

---

## Folder layout

```
Anglia Ruskin University - ARU/
  code/
    .env                              # live config (gitignored — copy from ENV.MD)
    ENV.MD                            # committed template / documentation
    download_and_clean_course_pages.py
    course_markdown_cleanup.py        # ARU-only markdown post-clean rules
  uni_req/                            # 4 fixed HTML pages (browser save)
  course_listing/                     # paginated listing HTML (Style B filenames)
  course_detail/                      # sample course pages per programme
  DegreeScopedPaginated.csv           # master sheet: listing + sample URLs
  Anglia Ruskin University - ARU_portal.csv
  output/                             # generated artifacts
  Claude_Output/                      # scratch (gitignored)
```

---

## Strategy: `DEGREE_SCOPED_PAGINATED`

ARU uses **four programme scopes** in one scrape run. Listing URLs live in `code/.env`:

| Programme | Listing pages |
|-----------|---------------|
| Undergraduate | `UNDERGRADUATE_COURSE_LISTING_PAGE_1` / `_PAGE_2` |
| Postgraduate taught | `POSTGRADUATE_COURSE_LISTING_PAGE_1` / `_PAGE_2` |
| Postgraduate research | `POSTGRADUATE_RESEARCH_COURSE_LISTING_PAGE_1` / `_PAGE_2` |
| Foundation year | `FOUNDATION_COURSE_LISTING_PAGE_1` / `_PAGE_2` |

Saved listing HTML uses **browser-title filenames** (Style B), e.g.:

| Programme | Example file in `course_listing/` |
|-----------|----------------------------------|
| Undergraduate | `Undergraduate courses 2026 - ARU.html` |
| Postgraduate taught | `Postgraduate Courses- ARU.html` |
| Foundation | `Foundation Year_courses 2026 - ARU.html` |

Sample course pages in `course_detail/` follow:

```
{Course Title} - {Award} - ARU.html
```

Examples: `Artificial Intelligence - MSc - ARU.html`, `Animation and Illustration - BA (Hons) - ARU.html`.

---

## Course URL patterns

ARU course pages are **one slug** under `/study/`:

```
https://www.aru.ac.uk/study/undergraduate/architecture
https://www.aru.ac.uk/study/postgraduate/accounting-and-finance
```

Configured in `.env`:

```ini
COURSE_PATH_PATTERNS="
^/study/(?:undergraduate|postgraduate)/[a-z0-9][a-z0-9\-]*$
"
```

Excluded hub pages (not courses): `/study/undergraduate`, `/study/postgraduate`, clearing, how-to-apply, etc. — see `EXCLUDED_COURSE_PATHS` and `EXCLUDED_PATH_PREFIXES` in `code/ENV.MD`.

---

## ARU-specific quirks

### Azure staging URL in downloaded HTML

Live pages are fetched from `www.aru.ac.uk`, but HTML `<link rel="canonical">` often points to:

```
https://aru-sc104-prod-uksouth-cd.azurewebsites.net/study/...
```

`download_and_clean_course_pages.py` may write that into `source_url` in clean markdown frontmatter.  
**Fix at export:** `export_dev_courses.py` rewrites `courseUrlExternal` using `UNIVERSITY_BASE_URL=https://www.aru.ac.uk`.

### Dual-track postgraduate courses

Many MSc pages list **two variants** on one page:

- `#### MSc` — standard (1 year)
- `#### Professional Experience` — 2-year with placement

`course_markdown_cleanup.py` keeps the **standard MSc track only**.

### International fees only

Fee sections split `### UK students` and `### International students`.  
Cleanup removes UK blocks; pipeline targets **international** tuition and deposit.

### Fixed £4,000 deposit

International course pages and `uni_req/deposit.html` state a **£4,000** CAS deposit. Stage 2d (`prompt_2_initialDeposit.md`) + `enrich_deposit_parsed()` extract this.

---

## `code/.env` — course cleaning

Active selectors (from `.env`; template in `ENV.MD`):

```ini
COURSE_PAGE_TITLE_SELECTOR=#course-page-title

COURSE_CLEAN_BLOCKS="
Course overview :: #utopian-course-overview
Entry requirements :: #entry_requirements
Fees and funding :: #fees_and_funding
"

COURSE_CLEAN_STRIP_WITHIN="
script
noscript
.hero-image
img
"

COURSE_CLEAN_EXPAND_TABS=true
```

`download_and_clean_course_pages.py` includes **ARU Utopian helpers**:

- `aru_find_block()` — fallback selectors per section (`#utopian-course-overview`, `#entry_requirements`, `#fees_and_funding`)
- `utopian_tabs_to_markdown()` — MSc / Professional Experience tabs
- `utopian_block_to_markdown()` — accordions inside entry requirements

Tune blocks using saved pages in `course_detail/`.

---

## `code/course_markdown_cleanup.py`

Runs automatically after HTML → markdown, before writing `output/clean/courses/*.md`.

| Rule | When | Action |
|------|------|--------|
| Professional Experience | Both `#### MSc` and `#### Professional Experience` exist | Remove PE sections + `### Professional Experience modules` |
| UK fees | `### UK students` heading present | Remove entire UK fee block |
| Tagline | `Professional Experience option available` | Strip line |

```python
def cleanup_course_markdown(markdown: str) -> str:
    cleaned = strip_professional_experience_variant(markdown)
    cleaned = strip_uk_student_fee_sections(cleaned)
    return cleaned
```

Per-uni cleanup pattern: `shared/course_markdown_cleanup.md`

---

## `uni_req/` — requirement pages

Save from browser with **exact filenames**:

| File | Source URL | Clean output |
|------|------------|--------------|
| `bangladesh-entry.html` | https://www.aru.ac.uk/international/south-asia | `output/clean/uni/bangladesh-entry.md` |
| `english-requirements.html` | https://www.aru.ac.uk/international/entry-requirements | `output/clean/uni/english-requirements.md` |
| `scholarships.html` | https://www.aru.ac.uk/student-life/preparing-for-study/help-with-finances/scholarships | `output/clean/uni/scholarships.md` |
| `deposit.html` | https://www.aru.ac.uk/international/how-to-apply/step-4---receive-our-decision-on-your-application | `output/clean/uni/deposit.md` |

```powershell
python download_and_clean_course_pages.py --clean-uni-only
```

**Status:** `output/clean/uni/` complete (4 files).

---

## Pipeline commands (from `code/`)

```powershell
# 1 — scrape course URLs (~320 courses)
python "..\..\shared\scrape_course_urls.py" .

# 2 — download HTML + clean courses
python download_and_clean_course_pages.py
python download_and_clean_course_pages.py --limit 5          # test

# 3 — LLM extract (Ollama required)
python "..\..\shared\llm_extract.py" .
python "..\..\shared\llm_extract.py" . --limit 5

# 4 — normalize
python "..\..\shared\normalize_admission_data.py" .

# 5 — export dev CSV
python "..\..\shared\export_dev_courses.py" .
```

### Useful flags

| Command | Flag | Purpose |
|---------|------|---------|
| `scrape_course_urls.py` | `--fresh` | Re-extract all URLs |
| `download_and_clean_course_pages.py` | `--clean-only` | Re-clean existing HTML |
| `download_and_clean_course_pages.py` | `--clean-uni-only` | Uni pages only |
| `llm_extract.py` | `--resume` | Skip completed slugs |
| `llm_extract.py` | `--skip-stage1` | Re-run Stage 2 only |

---

## Key outputs

| Path | Phase |
|------|-------|
| `output/course_urls.csv` | 1 |
| `output/course_pages/*.html` | 2 |
| `output/clean/courses/*.md` | 2 |
| `output/clean/uni/*.md` | 2 (uni) |
| `output/extracted/{slug}/output.json` | 3 |
| `output/extracted/{slug}/normalized.json` | 4 |
| `output/dev_courses_Anglia Ruskin University - ARU.csv` | 5 |

---

## Config files

| File | Purpose |
|------|---------|
| `code/.env` | Live secrets + selectors (do not commit) |
| `code/ENV.MD` | Committed template; copy to `.env` when setting up |
| `DegreeScopedPaginated.csv` | Human reference: listing URLs + sample course per programme |

When changing scrape URLs or clean selectors, update **both** `.env` and `ENV.MD` (keep them in sync).

---

## Checklist

- [x] `UNIVERSITY_NAME`, `UNIVERSITY_BASE_URL`, `STRATEGY` in `.env`
- [x] `COURSE_PATH_PATTERNS` + exclusions for ARU URL shape
- [x] `COURSE_CLEAN_BLOCKS` for Utopian sections
- [x] 4 `uni_req/*.html` saved + `clean/uni/` built
- [x] `course_listing/` saved per programme
- [x] `course_detail/` samples per programme
- [x] `course_markdown_cleanup.py` (PE + UK fee strip)
- [ ] Full pipeline run (Phase 1–5) on all courses
- [ ] Review `dev_courses_*.csv` against portal

---
## Foundation Url clean, html - .md
python "..\..\shared\download_and_clean_course_pages.py" --code-dir "D:\DATA SCOL\output\UK_Uni_Data\Anglia Ruskin University - ARU\code" --clean-only --study-level foundation
## Related docs

| Doc | Topic |
|-----|-------|
| [`../PIPELINE.md`](../PIPELINE.md) | Full F1 pipeline + Mermaid flowcharts |
| [`../scrape_course_urls_CMD.md`](../scrape_course_urls_CMD.md) | Phase 1 CMD commands (this PC) |
| [`../shared/course_markdown_cleanup.md`](../shared/course_markdown_cleanup.md) | Cleanup module contract |
| [`../_university_template/README.md`](../_university_template/README.md) | Generic university template |
