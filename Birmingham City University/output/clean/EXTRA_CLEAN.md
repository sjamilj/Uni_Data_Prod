# Manual extra clean — Birmingham City University

**Not part of the download/clean pipeline.** Run this after `download_and_clean_course_pages.py` when course markdown still needs folder-specific trimming or a second pass.

## Quick run

Double-click:

```
output/clean/EXTRA_CLEAN.bat
```

Or from repo root:

```cmd
python shared/extra_clean_courses.py --code-dir "Birmingham City University\code" --passes 2
```

## Folder-specific rules

Rules live in `code/.env` (see `code/ENV.MD`):

| Key | Applies to |
|---|---|
| `EXTRA_CLEAN_REMOVE_SECTIONS` | All study-level folders |
| `EXTRA_CLEAN_REMOVE_SECTIONS_FOUNDATION` | `clean/courses/foundation/` |
| `EXTRA_CLEAN_REMOVE_SECTIONS_UNDERGRADUATE` | `clean/courses/undergraduate/` |

Same `level :: heading` syntax as `COURSE_MARKDOWN_REMOVE_SECTIONS`.

Python rules for BCU clearing/CMS noise: `code/course_markdown_cleanup.py` → `extra_clean_course_markdown_uni()`.

## Options

```cmd
REM Foundation only
python shared/extra_clean_courses.py --code-dir "Birmingham City University\code" --level foundation

REM Undergraduate + foundation, two passes
python shared/extra_clean_courses.py --code-dir "Birmingham City University\code" --level foundation undergraduate --passes 2

REM Preview changes
python shared/extra_clean_courses.py --code-dir "Birmingham City University\code" --dry-run
```

## When to use

- After pipeline clean, pages still have Clearing blocks, Open Days, Why Choose Us, etc.
- Foundation and undergraduate pages need different section drops.
- One pass is not enough — use `--passes 2` (default in `EXTRA_CLEAN.bat`).

Updates `cleaned_at` in each file frontmatter. Does **not** re-download HTML or touch `manifest.json`.
