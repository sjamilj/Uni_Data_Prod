# engines/

## 1. Purpose

Pluggable HTML→markdown engines selected by `COURSE_CLEAN_ENGINE` in `.env`.

| Engine | File | When |
|--------|------|------|
| `generic` | `generic.py` | Most universities — CSS block list |
| `utopian` | `utopian.py` | ARU and Utopian CMS — tabs, structured IDs |
| `plugin` | `{Uni}/code/course_html_builder.py` | Custom hooks |

---

## 2. Where used

`CourseMarkdownBuilder` in `download_and_clean_course_pages.py` dispatches via `engines/__init__.py` loader.

---

## 3. generic.py

**`GenericCourseHtmlEngine`** (or equivalent class):

1. Parse HTML with BeautifulSoup
2. For each `COURSE_CLEAN_BLOCKS` entry (`Label :: selector`), extract inner HTML
3. Convert to markdown via `markdown_converter.py`
4. Strip tags listed in `COURSE_CLEAN_STRIP_WITHIN`

**Why default:** Works for any site where course content lives in stable CSS selectors.

---

## 4. utopian.py

**Utopian-specific behaviour:**

- `COURSE_CLEAN_EXPAND_TABS=true` — click tab panels before extract
- Targets IDs like `#utopian-course-overview`, `#entry_requirements`, `#fees_and_funding`

**Why separate engine:** Tabbed CMS layout breaks generic single-pass extraction; ARU was the reference implementation.

---

## 5. plugin engine

If `COURSE_CLEAN_ENGINE=plugin`, loads `course_html_builder.py` from university `code/` dir.

**Why:** Rare CMS layouts without merging into shared utopian/generic.

---

## 6. _helpers.py

`CourseHtmlEngineHelpers` — shared soup utilities, strip scripts/images, normalize whitespace.

---

## 7. Why engine pattern

Avoids `if university == "ARU"` scattered in downloader. New CMS = new engine file or plugin, not fork of 2000-line downloader.

---

## 8. Configuration

All engines read `CleanConfig` from `clean_config.py` (loaded from `.env`).

---

## 9. Prerequisites

- BeautifulSoup
- CSS selectors
- [download_and_clean_course_pages.md](download_and_clean_course_pages.md)

---

## 10. Read this next

1. [README.md](../../README.md) — engine table
2. [05-env-and-config.md](../05-env-and-config.md)
3. Aston/ARU `code/ENV.MD` examples
