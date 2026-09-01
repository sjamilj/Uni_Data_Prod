# scrape_course_urls.py

## 1. Purpose

Phase 1 of the pipeline: discover course page URLs from university listing pages and write deduplicated CSVs split by study level.

Main responsibilities:

- Load scrape config from `.env`
- Download paginated or A–Z catalogue pages (Playwright)
- Match and filter URLs with regex patterns
- Classify URLs by study level
- Persist progress for resume

---

## 2. Where this file is used

```
Dashboard / CLI
  → ScraperCLI.main()
  → CourseUrlScraper.run()
  → CatalogueUrlExtractor | PaginatedListingExtractor
  → output/course_urls.csv
```

---

## 3. Dependencies

| Dependency | Why |
|------------|-----|
| Playwright | Headless Chromium for live listings |
| `study_level.py` | `UrlLevelMap`, level CSV writers |
| `uni_paths.py` | `code/` and `output/` |
| BeautifulSoup | Parse listing HTML for links |

---

## 4. Main classes

| Class | Role |
|-------|------|
| `ScraperConfig` | Parsed `.env` scrape settings |
| `ConfigLoader` | Loads config from code dir |
| `CourseUrlMatcher` | Path regex + exclusions |
| `CatalogueUrlExtractor` | `STRATEGY=ALL_COURSE` |
| `PaginatedListingExtractor` | `STRATEGY=DEGREE_SCOPED_PAGINATED` |
| `CourseUrlScraper` | Top-level orchestrator |
| `ArtifactStore` | Write CSVs |
| `ProgressStore` | `scrape_progress.json` |
| `ScrapeLogger` | `scrape.log` |
| `ScraperCLI` | argparse entry |

---

## 5. Key methods

### `CourseUrlScraper.run(fresh, append, study_levels)`

**Process:**

1. Load or reset progress
2. Optionally filter `degree_listings` to selected study levels
3. Dispatch to `_run_all_course` or `_run_paginated`
4. Sort and persist URLs + update progress phase to `urls_complete`

### `PaginatedListingExtractor.extract_group()`

Loops `page_index` until:

- Empty page streak exceeded, OR
- `max_pages` reached, OR
- Same URL set repeats (`same_page_streak`)

**Does not stop** when a page has URLs but zero *new* unique URLs (fixes ARU foundation/UG overlap).

### `CourseUrlMatcher.is_course_url(url)`

Applies `COURSE_PATH_PATTERNS`, `EXCLUDED_*`, optional `COURSE_LINK_SELECTOR`.

---

## 6. Important code

```python
STRATEGY_ALL_COURSE = "ALL_COURSE"
STRATEGY_DEGREE_SCOPED_PAGINATED = "DEGREE_SCOPED_PAGINATED"
```

Strategy comes from `STRATEGY` in `.env` — no code change needed to switch universities.

---

## 7. Why it was written this way

- **Class decomposition:** 24 classes in ~2000 lines; each handles one concern (env, URLs, pagination, artifacts).
- **Module aliases:** `resolve_work_dir`, `WORK_DIR` keep older imports working.
- **Filesystem resume:** `listing_completed` and `group_state` per search path avoid re-downloading listing pages.

---

## 8. Artifacts

| Path | Content |
|------|---------|
| `course_urls.csv` | All URLs |
| `foundation_course_urls.csv` | Per-level |
| `undergraduate_course_urls.csv` | … |
| `scrape_progress.json` | Checkpoints |
| `scrape.log` | Run log |

---

## 9. Prerequisites

- Playwright basics
- Regex for URL patterns
- [05-env-and-config.md](../05-env-and-config.md)

---

## 10. Read this next

1. [features/scrape-urls-flow.md](../features/scrape-urls-flow.md)
2. [study_level.md](study_level.md)
3. [PIPELINE.md](../../PIPELINE.md)
