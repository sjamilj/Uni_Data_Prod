---
name: uni-course-urls
description: Derives COURSE_PATH_PATTERNS from saved course_listing HTML, runs scrape_course_urls.py, configures online and part-time URL exclusions, and switches to Cloudflare CDP when bot challenges appear. Use when finding course URLs, path patterns, scrape, bot challenge, or Cloudflare blocks listing download.
---

# Course URL scrape

Git: [git-for-operator.md](../git-for-operator.md) (user runs git; separate cmds only).

## Prompt and HTML

Follow [Prompt extract course URLs and env from a saved html.md](../../Prompt%20extract%20course%20URLs%20and%20env%20from%20a%20saved%20html.md).

Short loop:

1. Open saved HTML in `{University}/course_listing/`.
2. Confirm domain: `<!-- saved from url=(...) -->`, `<link rel="canonical">`, or `<base href>`.
3. Sample real course-detail `<a href>` paths (not nav, footer, apply pages).
4. Set `COURSE_PATH_PATTERNS` as anchored regexes (`^...$`) in `code/.env` and `code/ENV.MD`.
5. Set `UNIVERSITY_BASE_URL`, `EXCLUDED_COURSE_PATHS`, `EXCLUDED_PATH_PREFIXES` for lookalikes.
6. Point catalogue/listing keys per `STRATEGY` (see **new-uni-setup**).

## Run scrape

From repo root:

```powershell
python shared/scrape_course_urls.py --code-dir "{University}/code" --fresh
```

Sanity-check `output/course_urls.csv` count and a sample of URLs.

## Online and part-time

| Mechanism | When it applies |
|-----------|-----------------|
| `COURSE_EXCLUDE_URL_PATTERNS` | **Download and clean only** (`CourseTypeFilter` in `shared/course_type_filter.py`). Part-time/online URLs can still appear in `course_urls.csv`. |
| `COURSE_MARKDOWN_REMOVE_SECTIONS` e.g. `*part-time*` | Strips part-time **sections** inside a kept full-time page markdown. |
| `COURSE_EXCLUDE_LINK_TEXT_PATTERNS` | Documented in some `ENV.MD` files (e.g. Napier) but **not implemented** in `shared/` — do not rely on it. |

Use path patterns that match the site’s real slugs. Include both `*parttime*` and `*part-time*` when the catalogue uses both spellings.

Example block (adjust per site):

```ini
COURSE_EXCLUDE_URL_PATTERNS="
*postgraduate-parttime*
*postgraduate-part-time*
*postgraduate-online-learning*
*undergraduate-parttime*
*undergraduate-part-time*
*undergraduate-online-learning*
"
```

## Bot challenge

If listing or download shows **Verifying you are human** or **Just a moment**, use [docs/shared/cloudflare-course-download.md](../../docs/shared/cloudflare-course-download.md) (Brave/Edge CDP on port 9222). Do not loop headed Playwright alone.

## Next

Tune course page cleaning: **uni-course-clean**.
