# download_and_clean_course_pages.py

## 1. Purpose

Downloads course and university requirement HTML, converts selected DOM blocks to markdown, and maintains the clean manifest.

Responsibilities:

- Playwright download of course pages
- Engine dispatch (`generic` / `utopian` / `plugin`)
- Uni req HTML → `clean/uni/*.md`
- Course HTML → `clean/courses/{level}/*.md`
- Bridge to `course_markdown_cleanup.py`

---

## 2. Where this file is used

| Caller | Mode |
|--------|------|
| Dashboard button 2 | `--clean-uni-only` |
| `run_course_pipeline.py` | Presetup + Execute subsets |
| `run_all_download_clean.py` | Batch all universities |
| Direct CLI | Full catalogue download |

---

## 3. Dependencies

| Dependency | Why |
|------------|-----|
| Playwright | Download rendered HTML |
| `engines/` | HTML block extraction |
| `clean_config.py` | Parse `COURSE_CLEAN_*` from env |
| `course_markdown_cleanup.py` | Post-process markdown |
| `study_level.py` | Output path by level |

---

## 4. Main classes

| Class | Role |
|-------|------|
| `CleaningOrchestrator` | Routes uni vs course cleaning |
| `CoursePagesPipeline` | Full download+clean pipeline |
| `CoursePagesCleaner` | Download HTML for URL list |
| `UniReqPagesCleaner` | `uni_req/` → `clean/uni/` |
| `CourseMarkdownBuilder` | Pick engine, build MD |
| `GenericMarkdownBuilder` | Default block extraction |
| `ManifestWriter` | `clean/manifest.json` |
| `CleanWarningsWriter` | Warning CSV |
| `CoursePagesCLI` | argparse |

---

## 5. Key methods

### `CourseMarkdownBuilder.build(html, ...)`

1. Load `CleanConfig` from env
2. Resolve engine name (`COURSE_CLEAN_ENGINE`)
3. Call `engines.generic`, `engines.utopian`, or plugin
4. Return markdown string

### `CleaningOrchestrator.run(...)`

Branches on `--clean-uni-only` vs full course clean vs presetup output subdir.

### `ManifestWriter.merge(...)`

Merges new course entries into existing manifest without dropping prior courses unless `replace_courses`.

---

## 6. Important code

```python
COURSE_CLEAN_BLOCKS="
Course overview :: #utopian-course-overview
Entry requirements :: #entry_requirements
"
```

**Why env-driven blocks:** Each university CMS uses different selectors; shared code stays generic.

---

## 7. Why it was written this way

- **Engine pattern:** ARU Utopian CMS needs tab expansion; most unis use generic CSS blocks.
- **Separate uni clean:** `uni_req` pages are static saved HTML — no Playwright needed for phase 2.
- **Cleanup bridge:** Per-uni Python (`course_markdown_cleanup.py`) extends shared rules without forking the downloader.

---

## 8. Artifacts

| Path | Content |
|------|---------|
| `clean/uni/*.md` | Bangladesh entry, English, scholarships, deposit |
| `clean/courses/{level}/*.md` | Course pages |
| `clean/pre_setup_course/{level}/*.md` | Presetup sample |
| `clean/manifest.json` | Index metadata |
| `clean_warnings.csv` | Non-fatal clean issues |

---

## 9. Prerequisites

- CSS selectors
- [engines.md](engines.md)
- [course_markdown_cleanup.md](course_markdown_cleanup.md)

---

## 10. Read this next

1. [features/download-clean-flow.md](../features/download-clean-flow.md)
2. [engines.md](engines.md)
3. [run_course_pipeline.md](run_course_pipeline.md)
