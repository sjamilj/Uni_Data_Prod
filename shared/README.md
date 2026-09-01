# University Course Scraper

Downloads course listing pages, extracts course URLs, and saves fully rendered course page HTML using Playwright.

Each university has its own folder with a `Master Sheet.csv`. The scraper reads that file and picks the workflow automatically.

**New university?** Copy [`Master Sheet.template.csv`](Master%20Sheet.template.csv) and follow the [university-pipeline skill](.cursor/skills/university-pipeline/SKILL.md) (listing URLs, course tab selection, clean selectors).

See also: [how it works.md](how%20it%20works.md) for a detailed walkthrough with Aston University as an example.

---

## Setup

From the project root:

```powershell
pip install -r requirements.txt
python -m playwright install chromium
```

---

## Folder structure

```
AI Driven/
├── scrape_courses.py
├── requirements.txt
├── README.md
├── how it works.md
└── Aston University/
    ├── Master Sheet.csv
    ├── Courses - A to Z _ Aston University.html   # saved A–Z listing (if used)
    ├── course_urls.csv                            # generated
    ├── scrape_progress.json                       # generated (resume checkpoint)
    ├── scrape.log                                 # generated (timestamped run log)
    └── course_pages/                              # generated
```

---

## How it chooses the approach

| Condition | Approach |
|-----------|----------|
| `Course Listing 1` is **empty** | **A–Z listing** — reads saved listing HTML from `Course Page HTML`, optionally fetches remaining A–Z letter pages live |
| `Course Listing 1` is **set** | **Paginated listing** — downloads listing pages from Master Sheet, then auto-continues via **Next Results** / `page=` / `start_rank=` until done |

### University examples

| University | Approach | Notes |
|------------|----------|-------|
| Aston University | A–Z | `Course Page HTML` = saved A–Z HTML file |
| University of Essex | Paginated | Funnelback search with `start_rank=1, 11, 21…` |
| Birmingham City University | Paginated | Course search with `page=1, 2, 3…` (15 pages) |

---

## Commands

Replace `"Aston University"` with your university folder name.

### Full run (extract URLs + download course pages)

```powershell
python scrape_courses.py "Aston University"
```

### Extract course URLs only

Writes `course_urls.csv` without downloading individual course pages.

```powershell
python scrape_courses.py "Aston University" --urls-only
```

### Download course pages only

Uses the existing `course_urls.csv`. Skips pages already in `course_pages/`.

```powershell
python scrape_courses.py "Aston University" --download-only
```

### Start fresh (clear progress, re-extract from beginning)

Clears `scrape_progress.json` only. Existing HTML files in `course_pages/` are kept.

```powershell
python scrape_courses.py "Aston University" --fresh
```

### Using absolute paths

```powershell
python "e:\SCOL\Tools\AI Driven\scrape_courses.py" "e:\SCOL\Tools\AI Driven\Aston University"
```

---

## Resume after crash / power loss

Progress is saved automatically in `scrape_progress.json` inside each university folder.

| Phase | Saved after each… | On re-run |
|-------|-------------------|-----------|
| URL extraction | Listing page | Continues from next listing page; `course_urls.csv` updated with all URLs found so far |
| Course download | Course page | Skips URLs already saved in `course_pages/` |

Re-run the **same command** to continue — no data loss:

```powershell
python scrape_courses.py "Aston University"
```

Failed course page downloads are recorded and **retried** on the next run. Use `--fresh` only when you want to discard progress and start URL extraction over.

### Log file (`scrape.log`)

Each run appends timestamped entries to `scrape.log` inside the university folder:

```
2026-08-04 20:18:00 +0600 [START] mode=download-only fresh=False dir=University of Essex
2026-08-04 20:18:01 +0600 [INFO] Downloading 179 pages (already_done=467 total=646 failed=179)
2026-08-04 20:18:05 +0600 [OK] Course page [1/179]: https://... -> Course Name.html
2026-08-04 20:18:06 +0600 [ERROR] Course page [2/179]: https://... — timeout
2026-08-04 21:30:00 +0600 [END] status=partial duration=4320s total=646 downloaded=467 failed=179
```

Log levels: `START`, `INFO`, `OK`, `ERROR`, `END`.

---

## Output files

| File / folder | Description |
|---------------|-------------|
| `course_urls.csv` | Deduplicated course URLs (tab-separated, Excel-friendly) |
| `scrape_progress.json` | Checkpoint: phase, completed listing pages, downloaded URLs |
| `scrape.log` | Timestamped log of each run (append-only) |
| `course_pages/` | Rendered HTML for each individual course page |

### `course_urls.csv` format

Tab-separated with an Excel `sep=` hint so URLs stay in **column A**:

```
sep=	
course_url
https://www.aston.ac.uk/study/courses/...
```

---

## Master Sheet.csv columns used

| Column | Used for |
|--------|----------|
| **University URL** | University domain |
| **Course URL** | A–Z listing page URL |
| **Course Page HTML** | Filename of saved A–Z listing HTML |
| **Course Listing 1**, **Course Listing 2**, … | Paginated listing page URLs (up to 10) |

Other columns (Bangladesh entry requirements, scholarships, etc.) are **not** used by this scraper.

---

## Behaviour notes

- Course pages are fetched with **headless Chromium** and saved using the page `<title>` as the filename.
- **A–Z**: reads saved HTML first; if letter tabs exist (B–Z), fetches those pages live with Playwright.
- **Paginated**: follows **Next Results** links when present; otherwise increments `page` or `start_rank`.
- Empty `page=` is treated as **page 1** (BCU-style URLs).
- Stops after **5 consecutive** listing pages with no course URLs, or when **Page X of Y** reaches the last page.
- Each listing page is retried up to **5 times** if HTML is not returned.
- Foundation course URLs (`/courses/foundation…`) and single-slug URLs (BCU) are included.
- Essex redirect links (`url=` query param) are resolved automatically.

---

## Quick reference

| Goal | Command |
|------|---------|
| First run | `python scrape_courses.py "University Name"` |
| URLs only | `python scrape_courses.py "University Name" --urls-only` |
| Download only | `python scrape_courses.py "University Name" --download-only` |
| Resume after crash | Same command as before (no extra flag) |
| Start over | `python scrape_courses.py "University Name" --fresh` |


Aston University (A–Z)
# Full run
python "e:\SCOL\Tools\AI Driven\scrape_courses.py" "e:\SCOL\Tools\AI Driven\Aston University"
# URLs only
python "e:\SCOL\Tools\AI Driven\scrape_courses.py" "e:\SCOL\Tools\AI Driven\Aston University" --urls-only
# Download only (resume)
python "e:\SCOL\Tools\AI Driven\scrape_courses.py" "e:\SCOL\Tools\AI Driven\Aston University" --download-only
# Start fresh
python "e:\SCOL\Tools\AI Driven\scrape_courses.py" "e:\SCOL\Tools\AI Driven\Aston University" --fresh
University of Essex (paginated — retry 179 failed)
# Full run
python "e:\SCOL\Tools\AI Driven\scrape_courses.py" "e:\SCOL\Tools\AI Driven\University of Essex"
# URLs only
python "e:\SCOL\Tools\AI Driven\scrape_courses.py" "e:\SCOL\Tools\AI Driven\University of Essex" --urls-only
# Download only — retry failed pages
python "e:\SCOL\Tools\AI Driven\scrape_courses.py" "e:\SCOL\Tools\AI Driven\University of Essex" --download-only
# Start fresh
python "e:\SCOL\Tools\AI Driven\scrape_courses.py" "e:\SCOL\Tools\AI Driven\University of Essex" --fresh
Birmingham City University (paginated)
# Full run
python "e:\SCOL\Tools\AI Driven\scrape_courses.py" "e:\SCOL\Tools\AI Driven\Birmingham City University"
# URLs only
python "e:\SCOL\Tools\AI Driven\scrape_courses.py" "e:\SCOL\Tools\AI Driven\Birmingham City University" --urls-only
# Download only
python "e:\SCOL\Tools\AI Driven\scrape_courses.py" "e:\SCOL\Tools\AI Driven\Birmingham City University" --download-only
# Start fresh
python "e:\SCOL\Tools\AI Driven\scrape_courses.py" "e:\SCOL\Tools\AI Driven\Birmingham City University" --fresh
Shorter form (if already in project root)
cd "e:\SCOL\Tools\AI Driven"
python scrape_courses.py "Aston University"
python scrape_courses.py "University of Essex" --download-only
python scrape_courses.py "Birmingham City University" --urls-only
After each run
Check the log:

Get-Content "e:\SCOL\Tools\AI Driven\University of Essex\scrape.log" -Tail 20
Each run appends [START] / [END] lines with timestamps to <University Folder>\scrape.log.

What to run now
University	Suggested command
Essex (179 failed)
--download-only
Aston (partial download)
--download-only
BCU (289 URLs, likely needs download)
full run or --download-only
