# study_level.py

## 1. Purpose

Study-level classification and path conventions for foundation, undergraduate, postgraduate, and postgraduate research (PGR).

Used by URL scrape (level CSVs), clean output paths, presetup sampling, and execute selection.

---

## 2. Where this file is used

| Caller | Usage |
|--------|-------|
| `scrape_course_urls.py` | `UrlLevelMap`, `write_level_csvs` |
| `run_course_pipeline.py` | `sample_urls_stratified`, `urls_for_levels` |
| `download_and_clean_course_pages.py` | `clean_courses_root`, path helpers |
| `llm_extract.py` | Extraction dir per level |
| `pipeline_status.py` | Level counts for dashboard checkboxes |

---

## 3. Main classes

| Class | Role |
|-------|------|
| `StudyLevelClassifier` | Match URL against `*_URL_PATTERNS` from env |
| `UrlLevelMap` | URL → level mapping with merge/persist |
| `StudyLevelPathResolver` | `extracted/{level}/{slug}` paths |
| `PresetupSampler` | Stratified 10-course sample |

---

## 4. Key functions

### `parse_study_levels(tokens)`

Parses CLI `--study-level foundation undergraduate` into canonical level names.

### `sample_urls_stratified(urls_by_level, size=10)`

Picks roughly proportional courses across available levels for Presetup.

### `urls_for_levels(all_urls, url_levels, study_levels)`

Filters execute URL list to ticked dashboard levels.

### `is_resume_completed(completed, study_level, slug)`

Progress key format: `{level}/{slug}`.

---

## 5. Path constants

| Constant | Value |
|----------|-------|
| `CLEAN_COURSES_SUBDIR` | `courses` |
| `PRESETUP_CLEAN_SUBDIR` | `pre_setup_course` |
| `PRESETUP_SAMPLE_SIZE` | `10` |

---

## 6. Why it was written this way

Universities like ARU share `/study/undergraduate/...` paths between foundation and UG — level comes from **which listing** seeded the URL and pattern rules, not path alone. `UrlLevelMap` persists that provenance in `scrape_progress.json`.

---

## 7. Artifacts

| File | Content |
|------|---------|
| `foundation_course_urls.csv` | Level-split URLs |
| `presetup_sample.json` | Sample with `study_level` per course |
| `scrape_progress.json` → `url_levels` | URL classification map |

---

## 8. Prerequisites

- [05-env-and-config.md](../05-env-and-config.md) — `*_URL_PATTERNS`
- [features/scrape-urls-flow.md](../features/scrape-urls-flow.md)

---

## 9. Read this next

1. [scrape_course_urls.md](scrape_course_urls.md)
2. [run_course_pipeline.md](run_course_pipeline.md)
3. [features/presetup-and-execute-flow.md](../features/presetup-and-execute-flow.md)
