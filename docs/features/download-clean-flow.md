# Download and clean flow

End-to-end flow for downloading course HTML and converting to markdown.

---

## Complete flow

```
course_urls.csv (or presetup/execute selection)
        ↓
download_and_clean_course_pages.py
        ↓
CoursePagesPipeline / CleaningOrchestrator
        ↓
Playwright → raw HTML (course_pages/ or in-memory)
        ↓
CourseMarkdownBuilder → engine (generic / utopian / plugin)
        ↓
course_markdown_cleanup.py (optional per-uni rules)
        ↓
output/clean/courses/{level}/{slug}.md
        ↓
clean/manifest.json updated
```

Uni-only path (`--clean-uni-only`):

```
uni_req/*.html → UniReqPagesCleaner → clean/uni/*.md
```

---

## Step table

| Step | File / class | What happens |
|------|--------------|--------------|
| 1 | `CoursePagesCLI` | Parses `--clean-uni-only`, `--code-dir` |
| 2 | `CleaningOrchestrator` | Chooses uni vs course clean path |
| 3 | `CoursePagesCleaner` | Downloads HTML for URL list |
| 4 | `CourseMarkdownBuilder` | Selects engine from `COURSE_CLEAN_ENGINE` |
| 5 | `engines/generic.py` or `utopian.py` | Extracts CSS blocks → markdown |
| 6 | `CourseMarkdownCleanupBridge` | Runs `course_markdown_cleanup.py` |
| 7 | `ManifestWriter` | Updates `clean/manifest.json` |
| 8 | `CleanWarningsWriter` | Optional `clean_warnings.csv` |

---

## Engine selection

```
COURSE_CLEAN_ENGINE=generic  → GenericMarkdownBuilder
COURSE_CLEAN_ENGINE=utopian  → Utopian engine (tabs, ARU CMS)
COURSE_CLEAN_ENGINE=plugin   → University course_html_builder.py
```

---

## Artifacts

| Path | When |
|------|------|
| `clean/uni/*.md` | Phase 2 uni clean |
| `clean/courses/{level}/*.md` | Execute / full download |
| `clean/pre_setup_course/{level}/*.md` | Presetup sample |
| `clean/manifest.json` | Always after clean |
| `course_page_map.csv` | URL → local HTML map (if saved) |

---

## Human review point

After Presetup, operators open:

- Raw HTML in `course_detail/` or browser
- `clean/pre_setup_course/**/*.md`

Then edit `COURSE_CLEAN_BLOCKS` and `course_markdown_cleanup.py` before Presetup LLM.

---

## Read this next

1. [shared/download_and_clean_course_pages.md](../shared/download_and_clean_course_pages.md)
2. [shared/engines.md](../shared/engines.md)
3. [shared/course_markdown_cleanup.md](../shared/course_markdown_cleanup.md)
