# University of Bedfordshire — Cloudflare + CDP (Brave)

Use when beds.ac.uk shows **“Verifying you are human”** in a Playwright-launched browser, or for reliable **ajax_click** course search scraping.

**Shared reference:** [docs/shared/cloudflare-course-download.md](../../docs/shared/cloudflare-course-download.md)

**Already in `code/.env`:**

```env
COURSE_DOWNLOAD_USE_DEVICE_PROFILE=false
COURSE_DOWNLOAD_CDP_URL=http://127.0.0.1:9222
COURSE_DOWNLOAD_CLOUDFLARE_WARMUP=false
COURSE_DOWNLOAD_CLOUDFLARE_AUTO_CLICK=false
COURSE_DOWNLOAD_HEADLESS=false
LISTING_PAGINATION_MODE=ajax_click
```

Run commands from the **repo root** (`Uni_Data_Prod`).

---

## A. Scrape course URLs (Postgraduate listing)

1. Close all Brave windows (Task Manager → no `brave.exe`).

2. Start Brave with debugging:

```powershell
& "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" --remote-debugging-port=9222
```

3. In Brave, open **one tab** on a beds course-search URL (e.g. undergraduate listing) and pass Cloudflare until you see **Course Search** results (not “Verifying you are human”).  
   Playwright attaches to the **first tab that already shows `beds.ac.uk`**, or the leftmost tab — close extra `about:blank` tabs if needed.

4. Leave Brave open and run:

```powershell
python -u shared/scrape_course_urls.py --code-dir "University of Bedfordshire/code" --fresh
```

For each configured scope the scraper will:

1. **Goto** that scope’s `*_COURSE_LISTING_PAGE_1` URL  
2. **Select** the scope’s level + **Full-time** (`*_LISTING_AJAX_LEVEL_CHECKBOX_IDS` + `*_LISTING_AJAX_MODE_CHECKBOX_IDS`)  
3. **Paginate** in-page (`#scope=…&page=N` progress keys)

Configured in `.env` (comment out any `*_COURSE_LISTING_PAGE_1` to skip that pass):

| Scope | Level filter | Variant | Mode |
|--------|----------------|---------|------|
| `UNDERGRADUATE` | Undergraduate | — | Full-time |
| `POSTGRADUATE` | Postgraduate | — | Full-time |
| `POSTGRADUATE_RESEARCH` | Postgraduate Research Scheme | — | Full-time |
| `FOUNDATION` | Undergraduate | with Foundation Year | Full-time |

Env keys: `{SCOPE}_LISTING_AJAX_LEVEL_CHECKBOX_IDS`, `{SCOPE}_LISTING_AJAX_VARIANT_CHECKBOX_IDS`, `{SCOPE}_LISTING_AJAX_MODE_CHECKBOX_IDS`.

5. Check `output/course_urls.csv` and per-level CSVs.

**Course specification PDF (duration):** During **download**, the scraper fetches the UCIF PDF in the same Brave session, reads **page 1** for duration, stores it in the saved HTML (`#bedsSpecDuration`), then **deletes the PDF** (nothing kept under `output/course_specs/`). Plain `requests` gets **403** on `/media/*.pdf` — use CDP.

---

## B. Download + clean course pages

Same Brave session as **A** (or repeat steps 1–3 with a **course detail** URL open).

```powershell
python -u shared/download_and_clean_course_pages.py --code-dir "University of Bedfordshire/code"
```

---

## Level checkbox ids (other programmes)

| Programme | `LISTING_AJAX_LEVEL_CHECKBOX_IDS` |
|-----------|-----------------------------------|
| Postgraduate | `Postgraduate_313908` |
| Undergraduate | `Undergraduate_313909` |
| Foundation | `Foundation Degrees_-1` |
| Postgraduate research | `Postgraduate Research Scheme_439549` |

Omit the key to auto-infer from the listing URL path when possible.
