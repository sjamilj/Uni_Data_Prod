# course_markdown_cleanup.py

## 1. Purpose

Post-processes course markdown after HTML→MD conversion: remove noisy sections (UK fees, placement years, part-time notes) per university rules from `.env` and optional per-uni Python.

---

## 2. Where this file is used

```
download_and_clean_course_pages.py
  → CourseMarkdownCleanupBridge
  → CourseMarkdownCleaner.clean()
```

Optional override: `{University}/code/course_markdown_cleanup.py`

---

## 3. Main classes

| Class | Role |
|-------|------|
| `EnvFileLoader` | Load `COURSE_MARKDOWN_REMOVE_SECTIONS` from code dir |
| `MarkdownSectionRemover` | Heading-level removal with glob patterns |
| `CourseMarkdownCleaner` | Orchestrates load + remove |

---

## 4. Config format

```
COURSE_MARKDOWN_REMOVE_SECTIONS="
4 :: With placement
4 :: BSc (Hons)
3 :: UK students
5 :: UK students*
"
```

Format: `{heading_level} :: {pattern}` — `*` is glob wildcard.

---

## 5. Key method: `MarkdownSectionRemover.remove_sections(md)`

Walks markdown headings; drops sections whose title matches configured patterns at that level.

**Why heading levels matter:** `3 :: UK students` only removes `### UK students`, not unrelated text containing "UK students".

---

## 6. Why it was written this way

HTML clean captures whole blocks; some noise is easier to strip from markdown (e.g. duplicate degree titles). Env rules cover 80% of unis; Python hook covers edge cases without changing `shared/`.

See also existing [shared/course_markdown_cleanup.md](../../shared/course_markdown_cleanup.md) for operator-focused examples.

---

## 7. Artifacts

Modifies in place: `clean/courses/{level}/*.md`, `clean/pre_setup_course/{level}/*.md`

---

## 8. Prerequisites

- Markdown heading syntax
- [05-env-and-config.md](../05-env-and-config.md)

---

## 9. Read this next

1. [download_and_clean_course_pages.md](download_and_clean_course_pages.md)
2. [features/download-clean-flow.md](../features/download-clean-flow.md)
