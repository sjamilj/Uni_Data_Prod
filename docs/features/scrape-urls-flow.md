# Scrape URLs flow

End-to-end flow for Phase 1: discovering course URLs from listing pages.

---

## Complete flow

```
code/.env (listing URLs, path patterns)
        ↓
scrape_course_urls.py --code-dir Uni/code
        ↓
ConfigLoader → ScraperConfig
        ↓
CourseUrlScraper.run()
        ↓
  STRATEGY_ALL_COURSE → CatalogueUrlExtractor
  STRATEGY_DEGREE_SCOPED_PAGINATED → PaginatedListingExtractor (per scope)
        ↓
Playwright downloads listing pages
        ↓
CourseUrlMatcher filters <a href>
        ↓
UrlLevelMap classifies study level
        ↓
ArtifactStore.persist_urls()
        ↓
output/course_urls.csv + level CSVs + scrape_progress.json
```

---

## Step table

| Step | File / class | What happens |
|------|--------------|--------------|
| 1 | Dashboard `main_window._phase_command()` | Builds `python shared/scrape_course_urls.py --code-dir ...` |
| 2 | `ScraperCLI.main()` | Parses `--fresh`, `--append-urls`, `--study-level` |
| 3 | `ConfigLoader.load(code_dir)` | Reads `.env` into `ScraperConfig` |
| 4 | `CourseUrlScraper.run()` | Loads/resets progress, picks strategy |
| 5 | `PaginatedListingExtractor.extract_group()` | Loops pages until empty or max |
| 6 | `CourseUrlMatcher` | Applies `COURSE_PATH_PATTERNS`, exclusions |
| 7 | `UrlLevelMap` | Tags URL with foundation/UG/PG/PGR |
| 8 | `ArtifactStore` | Writes CSVs, updates `scrape_progress.json` |
| 9 | `ScrapeLogger` | Appends to `scrape.log` |

---

## Dashboard wiring

| Run mode | Extra args |
|----------|------------|
| Resume | (none) |
| Fresh | `--fresh` |
| Append URLs | `--append-urls` |

Study-level checkboxes → repeated `--study-level foundation` etc.

---

## Pagination behaviour

`PaginatedListingExtractor` stops when:

- Page returns no course URLs **and** empty streak hits limit, OR
- Same URL set repeats (`same_page_streak`) — duplicate page detection

**Does not stop** merely because a page adds zero *new* unique URLs (overlap with another level's listing).

---

## Artifacts

| Path | Content |
|------|---------|
| `course_urls.csv` | All unique URLs |
| `foundation_course_urls.csv` | Per-level split |
| `undergraduate_course_urls.csv` | … |
| `scrape_progress.json` | `phase`, `listing_completed`, `group_state`, `url_levels` |
| `scrape.log` | Timestamped run log |

---

## Read this next

1. [shared/scrape_course_urls.md](../shared/scrape_course_urls.md)
2. [shared/study_level.md](../shared/study_level.md)
3. [05-env-and-config.md](../05-env-and-config.md)
