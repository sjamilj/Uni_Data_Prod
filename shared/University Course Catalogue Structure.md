# University Course Catalogue Structure Taxonomy

This document defines the six catalogue shapes used to **discover course URLs**.

**Master Sheet.csv cannot map these six types.** Use `.env` with `STRATEGY=<TECHNICAL_NAME>` and the strategy-specific listing URL variables. Per-strategy university lists and env templates live under [`catalogue-strategies/`](catalogue-strategies/README.md).

---

## How we collect course URLs (config contract)

```
Classify catalogue type (this doc / CSV)
        ↓
Copy catalogue-strategies/<STRATEGY>/.env → university folder
        ↓
Set STRATEGY + listing URL variables
        ↓
scrape_courses.py --urls-only   (when wired to STRATEGY)
        ↓
course_urls.csv  (unique course page URLs)
```

### Six strategies (env)

| `STRATEGY` | Folder | Primary env URL keys |
|------------|--------|----------------------|
| `ALL_COURSE` | [`catalogue-strategies/ALL_COURSE/`](catalogue-strategies/ALL_COURSE/) | `COURSE_CATALOGUE_URL` |
| `DEGREE_SCOPED_ALL_COURSE` | [`…/DEGREE_SCOPED_ALL_COURSE/`](catalogue-strategies/DEGREE_SCOPED_ALL_COURSE/) | `LISTING_PROGRAMME`, `COURSE_CATALOGUE_URL` |
| `PAGINATED_COURSE` | [`…/PAGINATED_COURSE/`](catalogue-strategies/PAGINATED_COURSE/) | `COURSE_LISTING_PAGE_1`, `COURSE_LISTING_PAGE_2` |
| `DEGREE_SCOPED_PAGINATED` | [`…/DEGREE_SCOPED_PAGINATED/`](catalogue-strategies/DEGREE_SCOPED_PAGINATED/) | `LISTING_PROGRAMME`, `COURSE_LISTING_PAGE_1`, `COURSE_LISTING_PAGE_2` |
| `DEGREE_SCOPED_ALPHABETICAL` | [`…/DEGREE_SCOPED_ALPHABETICAL/`](catalogue-strategies/DEGREE_SCOPED_ALPHABETICAL/) | `LISTING_PROGRAMME`, `COURSE_LETTER_INDEX_URL` |
| `HIERARCHICAL_PROGRAMME` | [`…/HIERARCHICAL_PROGRAMME/`](catalogue-strategies/HIERARCHICAL_PROGRAMME/) | `LISTING_PROGRAMME`, `COURSE_CATEGORY_ROOT_URL`, `COURSE_LEAF_LISTING_URLS` |

Optional shared keys: `UNIVERSITY_BASE_URL`, `COURSE_CATALOGUE_HTML`, `PAGINATION_PARAM`, `LETTER_URL_MODE`, `LETTER_QUERY_PARAM`, `LETTER_RANGE`.

### Shared pagination behaviour (paginated strategies)

1. Put **two consecutive listing URLs** in `COURSE_LISTING_PAGE_1` / `COURSE_LISTING_PAGE_2` so page param + step can be inferred.
2. Download listing HTML with Playwright (JS-rendered results).
3. Extract course URLs; merge into a unique set → `course_urls.csv`.
4. Build the next listing URL; stop after **5 consecutive empty / failed pages**.

Degree-scoped strategies: run **one** `LISTING_PROGRAMME` at a time, then change `.env` and append unique URLs.

### Today’s runtime note

Root `scrape_courses.py` still uses Master Sheet listing columns / A–Z HTML; CCCU uses `COURSE_LISTING_1` / `COURSE_LISTING_2` in `.env`. The `STRATEGY=…` keys above are the **target config contract** for mapping all six types — see each strategy folder’s `.env`. No scraper code change in this documentation pass.

---



## 1. ALL Course



### Technical name

`ALL_COURSE`

### Context

One catalogue surface lists every course. No pagination, no degree split, no letter index required for discovery.

### Example

```text
All Courses
├── Accounting and Finance
├── Computer Science
├── Business Management
├── Engineering
├── Law
└── Psychology
```



### CSV examples

- Aston University → A–Z all courses (`courses-atoz`)
- Brunel (large `pageSize` single results page)
- Teesside, Derby, Edinburgh Napier (single catalogue / high page size)



### Scraper strategy (current approach)

**Use AtoZListingStrategy (Master Sheet).**

1. Save the all-courses / A–Z HTML into the university folder (browser Save As, or one-off download).
2. Master Sheet:
  - `Course URL` = listing page URL
  - `Course Page HTML` = saved filename
  - `Course Listing 1`… leave **empty**
3. Run: `python scrape_courses.py "University Name" --urls-only`
4. Scraper reads saved HTML → extracts course links → unique `course_urls.csv`.

If the “all courses” page is actually a search URL with one huge page, you may instead put that single URL in `Course Listing 1` and use paginated download once (still one page of results).

**Status:** Implemented (Aston-style A–Z).

---



## 2. Degree-Scoped ALL Course



### Technical name

`DEGREE_SCOPED_ALL_COURSE`

### Context

Courses are split by study level (Foundation / Undergraduate / Postgraduate). Each level page lists **all** courses for that level (no pagination).

### Example

```text
Courses
├── Foundation
│   ├── Foundation in Business
│   └── Foundation in Computing
├── Undergraduate
│   ├── Accounting and Finance BSc
│   └── Computer Science BSc
└── Postgraduate
    ├── Accounting MSc
    └── MBA
```



### CSV examples

- Keele, LSBU, Ravensbourne, Hull, Greenwich (level → full list)
- Roehampton may mix degree scope with pagination — classify by the live site



### Scraper strategy (current approach)

**Multiple listing seeds → extract → merge unique URLs.**

**Option A — Master Sheet listings (no auto page increment needed)**  
Put each degree-level “all courses” URL in `Course Listing 1`, `Course Listing 2`, …  
Paginated strategy will download each seed once. If there is no next page / no step, it stops after seeds (or empty-page limit).

**Option B —** `.env` **one level at a time (CCCU-style)**  
Even when a level is not paginated, you can set:

```env
LISTING_PROGRAMME=undergraduate
COURSE_LISTING_1=https://example.ac.uk/undergraduate-courses
```

Run `--urls-only --fresh`, then swap programme and `--append-urls` so `course_urls.csv` accumulates unique URLs across levels.

**Rule:** always append/merge and keep URLs unique across degree runs.

**Status:** Pattern supported via multiple seeds or env + append; configure per university.

---



## 3. Paginated Course Catalogue



### Technical name

`PAGINATED_COURSE`

### Context

One catalogue for all courses, split across pages (`?page=`, `start_rank=`, etc.).

### Example

```text
All Courses
Page 1  → Accounting, Business, Computer Science
Page 2  → Engineering, Finance, Law
Page 3  → Marketing, Psychology, Sociology
```



### Typical URL pattern

```text
/courses?page=1
/courses?page=2
/search?...&start_rank=1
/search?...&start_rank=11
```



### CSV examples

- Birmingham City University (`page=`)
- University of Essex (`start_rank=`)
- Cardiff Met, Kingston, Huddersfield, University of Law, UWL, …



### Scraper strategy (current approach)

**Use PaginatedListingStrategy (Master Sheet).**

1. Master Sheet:
  - `Course Listing 1` = first results page URL
  - `Course Listing 2` = second page (same filters; page/rank advanced)
  - Leave A–Z `Course Page HTML` empty unless you also need it for something else
2. Scraper:
  - Infers param + step from Listing 1 vs 2 (e.g. `page` step `1`, or `start_rank` step `10`)
  - Playwright downloads listing HTML → extract course URLs
  - Builds next URL; continues until **5 consecutive empty/failed pages**
3. Output: unique `course_urls.csv`
4. Run: `python scrape_courses.py "University Name" --urls-only`

**Status:** Implemented (Essex, BCU, and other Master Sheet paginated unis).

---



## 4. Degree-Scoped Paginated Catalogue



### Technical name

`DEGREE_SCOPED_PAGINATED`

### Context

Each degree/study level has its **own** paginated search (UG pages 1…n, PG pages 1…n, …).

### Example

```text
Undergraduate
├── Page 1 → …
├── Page 2 → …
└── Page 3 → …

Postgraduate
├── Page 1 → …
└── Page 2 → …
```



### Typical URL pattern

```text
/search/undergraduate-courses?pageIndex=1
/search/undergraduate-courses?pageIndex=2
/search/postgraduate-taught-courses?pageIndex=1
```



### CSV examples

- Canterbury Christ Church University (`pageIndex` per programme)
- ARU (level + filters + `page=`)
- Beds / UEL / Surrey / Suffolk (level-scoped search)



### Scraper strategy (current approach)

**Same pagination engine as §3, scoped per degree.**

#### Preferred for CCCU-like sites (custom page param or one programme per run)

1. Copy `.env.example` → `.env`
2. Set one programme:

```env
LISTING_PROGRAMME=undergraduate
COURSE_LISTING_1=.../undergraduate-courses?pageIndex=1
COURSE_LISTING_2=.../undergraduate-courses?pageIndex=2
```

1. From the university folder:

```text
python scrape_courses.py --urls-only --fresh
```

1. Edit `.env` for postgraduate / foundation, then:

```text
python scrape_courses.py --urls-only --fresh --append-urls
```

1. Unique URLs accumulate in `course_urls.csv`.



#### Alternative when root params work (`page`, `start_rank`, …)

Put UG page1/page2 (and optionally more levels) into Master Sheet `Course Listing *`, or run separate Master Sheet configs / listing batches and merge CSVs carefully.

**Do not** mix unrelated programmes in one `.env` pair: Listing 1 and 2 must share the same search path so step inference stays valid.

**Status:** Implemented for CCCU (env + append). Root Master Sheet covers degree-scoped pagination when the page param is supported.

---



## 5. Degree-Scoped Alphabetical Index



### Technical name

`DEGREE_SCOPED_ALPHABETICAL`

### Context

Degree/study level first, then A–Z (or letter filter) within each level.

### Example

```text
Undergraduate
├── A → …
├── B → …
└── C → …

Postgraduate
├── A → …
└── B → …
```



### Typical URL pattern

```text
/courses/?courseStudyType=undergraduate&courseName=c
/courses/undergraduate/a
/courses/postgraduate/b
```



### CSV examples

- Middlesex University (`courseStudyType` + `courseName=letter`)
- Manchester Metropolitan University (`/study/courses/a`)



### Scraper strategy (current approach)

**Degree seeds × letter walk → extract → merge unique.**

1. Decide degree keys (UG / PG / Foundation) — store in `.env` or a small URL list.
2. For each degree, generate or discover letter URLs (`a`…`z`, or site-specific query).
3. Download each letter listing HTML → extract course URLs → merge unique.
4. Switch degree (env or next seed batch) and repeat with append/merge.

Practical setup today:

- **Env loop** (like CCCU programmes): one `courseStudyType` + letter seed pair per run, or scripted letter list; append into one `course_urls.csv`.
- **Master Sheet**: only if you can express consecutive seeds the paginated helper understands — letter indexes often need an explicit A–Z URL list rather than `page+=1`.

**Status:** Documented pattern; Middlesex-style needs letter URL generation (not a single generic root mode yet).

---



## 6. Hierarchical Programme Catalogue



### Technical name

`HIERARCHICAL_PROGRAMME`

### Context

Multi-level navigation: degree → subject / school → programme cluster → course links. You cannot land on one flat “all courses” HTML without walking the tree.

### Example

```text
Courses
└── Undergraduate
    └── Business
        └── Accounting
            ├── Accounting BSc
            ├── Accounting and Finance BSc
            └── Accounting with Placement BSc
```



### Typical URL pattern

```text
/courses/undergraduate-courses
/courses/undergraduate/business
/courses/undergraduate/business/accounting
```



### CSV examples

- University of Hertfordshire (`/courses/undergraduate-courses` entry)



### Scraper strategy (current approach)

**Precompute the tree, then scrape leaf listings** (not a blind recursive clicker in root `scrape_courses.py`).

1. Manually or with a one-off crawl: from the degree root, collect subject / programme listing URLs.
2. Save that URL list (Master Sheet `Course Listing *`, a CSV of listing seeds, or `.env` batches).
3. For each leaf listing URL: download HTML → extract course links → unique merge (same as paginated/all seeds).
4. If a leaf is itself paginated, use §3 / §4 pagination on that leaf.

Do **not** rely on unbounded recursive “click every subject” in production until a dedicated hierarchical strategy exists; prefer a reviewed seed list of listing pages.

**Status:** Taxonomy + seed-list approach; Hertfordshire-style full auto-walk not in root scraper yet.

---



## Mapping: taxonomy → `.env` (not Master Sheet)


| # | `STRATEGY` | Primary env keys | Universities folder |
| - | ---------- | ---------------- | ------------------- |
| 1 | `ALL_COURSE` | `COURSE_CATALOGUE_URL` | [catalogue-strategies/ALL_COURSE](catalogue-strategies/ALL_COURSE/) |
| 2 | `DEGREE_SCOPED_ALL_COURSE` | `LISTING_PROGRAMME`, `COURSE_CATALOGUE_URL` | […/DEGREE_SCOPED_ALL_COURSE](catalogue-strategies/DEGREE_SCOPED_ALL_COURSE/) |
| 3 | `PAGINATED_COURSE` | `COURSE_LISTING_PAGE_1`, `COURSE_LISTING_PAGE_2` | […/PAGINATED_COURSE](catalogue-strategies/PAGINATED_COURSE/) |
| 4 | `DEGREE_SCOPED_PAGINATED` | `LISTING_PROGRAMME`, `COURSE_LISTING_PAGE_1`, `COURSE_LISTING_PAGE_2` | […/DEGREE_SCOPED_PAGINATED](catalogue-strategies/DEGREE_SCOPED_PAGINATED/) |
| 5 | `DEGREE_SCOPED_ALPHABETICAL` | `LISTING_PROGRAMME`, `COURSE_LETTER_INDEX_URL` | […/DEGREE_SCOPED_ALPHABETICAL](catalogue-strategies/DEGREE_SCOPED_ALPHABETICAL/) |
| 6 | `HIERARCHICAL_PROGRAMME` | `COURSE_CATEGORY_ROOT_URL`, `COURSE_LEAF_LISTING_URLS` | […/HIERARCHICAL_PROGRAMME](catalogue-strategies/HIERARCHICAL_PROGRAMME/) |


---



## Adding a new university (URL collection only)

1. Open the live course finder; classify it using sections 1–6 (mark the matching column in `University Course Catalogue Structure.csv`).
2. Open `catalogue-strategies/<STRATEGY>/` — copy `.env` into the university folder and fill URL variables.
3. Confirm a **sample course URL** shape so extraction filters stay correct.
4. Run `--urls-only` (limit / spot-check a few URLs) once the scraper reads `STRATEGY`.
5. Only then run `--download-only` for course HTML.

---



## Related files


| File | Role |
| ---- | ---- |
| `University Course Catalogue Structure.csv` | Per-university classification + example listing URLs |
| `catalogue-strategies/*/README.md` | Universities for that `STRATEGY` |
| `catalogue-strategies/*/.env` | Env template (`STRATEGY` + URL keys) |
| `{University}/.env` | Per-uni runtime listing config (target: copy from strategy template) |
| `scrape_courses.py` | Current root URL collector (Master Sheet–based today) |
| `Canterbury Christ Church University/scrape_courses.py` | Env paginated + `--append-urls` |
| `how it works.md` | Current Master Sheet + Playwright behaviour |


