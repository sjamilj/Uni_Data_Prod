# Environment and configuration

How university-specific behaviour is configured without changing `shared/` code.

---

## Config file hierarchy

| File | Role | Git |
|------|------|-----|
| `code/ENV.MD` | Committed template; documents all keys | Yes |
| `code/.env` | Runtime config loaded by scripts | No (gitignored) |
| `code/env/common.env` | Optional fragment: shared keys | Yes |
| `code/env/foundation.env` | Optional fragment: foundation overrides | Yes |

**Build:** `python shared/build_env.py --code-dir "{University}/code"` merges `env/*.env` → `.env` and `ENV.MD`.

**From Template.csv:** `python shared/build_university_from_template.py --university "{University Name - SHORT}"` reads `Template.csv`, sets `STRATEGY`, listing URLs, and `UNI_REQ_SOURCE_URLS`, and writes the variant CSV at the university root. Use `--bootstrap` to create the folder from `_university_template` when missing.

**Why fragments:** Foundation listing URLs differ from undergraduate; splitting `foundation.env` keeps `common.env` readable.

---

## How scripts load config

1. CLI passes `--code-dir "{University}/code"`
2. `resolve_code_dir()` → absolute path to `code/`
3. `EnvFile` / `EnvFileLoader` reads `.env` from that directory
4. `resolve_output_dir()` → sibling `output/`

If `.env` is missing, run `build_university_from_template.py` (from `Template.csv`), `build_env.py`, or copy `ENV.MD` → `.env` (see `Create-EnvFiles.ps1`).

---

## Template.csv strategy matrix

| Variant CSV | Row shape | `STRATEGY` | Listing env block |
|-------------|-----------|------------|-------------------|
| `ALL_COURSE.csv` | Row 5 `All` only | `ALL_COURSE` | `COURSE_CATALOGUE_URL` + `COURSE_CATALOGUE_HTML` |
| `Paginated.csv` | Row 5 `All` only | `DEGREE_SCOPED_PAGINATED` | `COURSE_LISTING_PAGE_1/2` (no scope prefix) |
| `DegreeScopedALLCourse.csv` | Rows 6–9 | `ALL_COURSE` | `{SCOPE}_COURSE_CATALOGUE_*` |
| `DegreeScopedPaginated.csv` | Rows 6–9 | `DEGREE_SCOPED_PAGINATED` | `{SCOPE}_COURSE_LISTING_PAGE_*` |

Programme → scope prefix: Foundation → `FOUNDATION`, Undergraduate → `UNDERGRADUATE`, Postgraduate → `POSTGRADUATE`, Postgraduate Research → `POSTGRADUATE_RESEARCH`.

Requirement URL columns (Bangladesh, English, Scholarship, Deposit) map to `UNI_REQ_SOURCE_URLS` in `.env` (`slug :: url` lines).

See [_university_template/README.md](../_university_template/README.md) for the full Template.csv workflow.

---

## Key variable groups

### Identity and strategy

| Key | Example | Purpose |
|-----|---------|---------|
| `UNIVERSITY_NAME` | `Anglia Ruskin University - ARU` | CSV export filename |
| `STRATEGY` | `DEGREE_SCOPED_PAGINATED` | URL scrape mode |
| `UNIVERSITY_BASE_URL` | `https://www.aru.ac.uk` | Resolve relative links |

### Listing URLs (paginated strategy)

Per study level, seed pages for pagination:

```
UNDERGRADUATE_COURSE_LISTING_PAGE_1=https://...
UNDERGRADUATE_COURSE_LISTING_PAGE_2=https://...
FOUNDATION_COURSE_LISTING_PAGE_1=https://...
POSTGRADUATE_COURSE_LISTING_PAGE_1=https://...
```

Scraper follows `page=` / `pageIndex=` until empty pages.

### URL matching

| Key | Purpose |
|-----|---------|
| `COURSE_PATH_PATTERNS` | Regex: path must match to count as course URL |
| `UNDERGRADUATE_URL_PATTERNS` | Classify URL into study level |
| `FOUNDATION_URL_PATTERNS` | Same for foundation |
| `EXCLUDED_COURSE_PATHS` | Exact paths to drop |
| `EXCLUDED_PATH_PREFIXES` | Prefixes to drop (hub pages, clearing index) |
| `COURSE_LINK_SELECTOR` | Optional CSS filter on listing pages |

### HTML cleaning

| Key | Purpose |
|-----|---------|
| `COURSE_CLEAN_ENGINE` | `generic`, `utopian`, or `plugin` |
| `COURSE_CLEAN_BLOCKS` | `Label :: #css-selector` blocks to extract |
| `COURSE_PAGE_TITLE_SELECTOR` | Course title element |
| `COURSE_CLEAN_STRIP_WITHIN` | Tags to remove inside blocks |
| `COURSE_CLEAN_EXPAND_TABS` | Click tabs before extract (Utopian) |

### Markdown post-processing

| Key | Purpose |
|-----|---------|
| `COURSE_MARKDOWN_REMOVE_SECTIONS` | `level :: heading` patterns to strip |

Optional Python: `code/course_markdown_cleanup.py` for rules too complex for `.env`.

### Uni requirement pages

| Key | Purpose |
|-----|---------|
| `UNI_REQ_SOURCE_URLS` | `slug :: url` for manifest metadata |

---

## Study levels and dashboard

Dashboard checkboxes map to env scopes:

| UI label | Env scope / level |
|----------|-------------------|
| Foundation | `FOUNDATION_*` keys, `foundation` level |
| Undergraduate | `UNDERGRADUATE_*` |
| Postgraduate | `POSTGRADUATE_*` |
| PGR | `POSTGRADUATE_RESEARCH_*` |

Scrape with `--study-level foundation` only processes foundation listing seeds (see `scrape_course_urls.py`).

---

## Example: ARU layout

```
code/
├── ENV.MD              # full merged reference
├── .env                # generated copy
└── env/
    ├── common.env      # UG/PG/PGR + clean config
    └── foundation.env  # foundation listing URLs only
```

Foundation courses share `/study/undergraduate/...` paths with UG — level split relies on **which listing** they came from and `FOUNDATION_URL_PATTERNS`, not path shape alone.

---

## When to edit config vs code

| Change | Edit |
|--------|------|
| New listing URL | `.env` / `env/*.env` |
| Wrong course URLs captured | `COURSE_PATH_PATTERNS`, exclusions |
| Missing HTML section in MD | `COURSE_CLEAN_BLOCKS` |
| CMS-specific tab behaviour | `COURSE_CLEAN_ENGINE` or plugin |
| Strip noisy MD headings | `COURSE_MARKDOWN_REMOVE_SECTIONS` |
| New scrape strategy for all unis | `shared/scrape_course_urls.py` |

---

## See also

- [_university_template/README.md](../_university_template/README.md) — Template.csv workflow
- [shared/build_env.md](shared/build_env.md)
- [features/scrape-urls-flow.md](features/scrape-urls-flow.md)
- [PIPELINE.md](../PIPELINE.md) — Presetup review checklist
