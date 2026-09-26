# University of Hertfordshire — Cloudflare + CDP

herts.ac.uk returns **403** to plain HTTP and often blocks **Playwright-launched** browsers on **“Verifying you are human”**. Use **CDP**: attach the scraper to **your** debugging browser after you pass Cloudflare once.

**Shared reference:** [docs/shared/cloudflare-course-download.md](../../docs/shared/cloudflare-course-download.md)

**In `code/.env` (also mirrored in `ENV.MD`):**

```env
COURSE_DOWNLOAD_USE_DEVICE_PROFILE=false
COURSE_DOWNLOAD_CDP_URL=http://127.0.0.1:9222
COURSE_DOWNLOAD_CLOUDFLARE_WARMUP=false
COURSE_DOWNLOAD_CLOUDFLARE_AUTO_CLICK=false
COURSE_DOWNLOAD_HEADLESS=false
COURSE_LISTING_FETCH=browser
COURSE_DOWNLOAD_CLOUDFLARE_WAIT_SECONDS=300
```

Run from **repo root** (`Uni_Data_Prod`).

---

## A. Scrape course URLs (CourseHub)

Hub URLs in `.env`:

- `UNDERGRADUATE_COURSE_LISTING_HUB_URL` → https://www.herts.ac.uk/courses/undergraduate-courses  
- `POSTGRADUATE_COURSE_LISTING_HUB_URL` → https://www.herts.ac.uk/courses/postgraduate-masters-study  

The scraper opens each hub, discovers subject pages (e.g. `…/undergraduate-courses/psychology`), then collects `a.course-card-link` course URLs.

1. Close all Brave/Edge windows used for debugging (Task Manager if needed).

2. Start **Brave** (or Edge) with remote debugging:

```powershell
& "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" --remote-debugging-port=9222
```

Edge alternative:

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222
```

3. Open **one tab** on the UG hub (or any herts.ac.uk course page) and complete Cloudflare until you see real content (subject cards or course cards — not “Verifying you are human”).

4. Leave the browser open and run:

```powershell
python -u shared/scrape_course_urls.py --code-dir "University of Hertfordshire/code" --fresh
```

5. Check `University of Hertfordshire/output/course_urls.csv` and per-level CSVs.

**Headed Playwright without CDP** sometimes works with Edge (`channel=msedge`) for one-off HTML saves; for the full pipeline, prefer CDP.

---

## B. Download + clean course pages

Same debugging session as **A**, or repeat steps 1–3 with a **course detail** tab open (e.g. a URL under `/courses/undergraduate/…`).

```powershell
python -u shared/download_and_clean_course_pages.py --code-dir "University of Hertfordshire/code"
```

Progress resumes from `output/scrape_progress.json` unless you pass `--fresh`.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `launch_course_download_browser` / connect errors | Confirm `COURSE_DOWNLOAD_CDP_URL` and debugging browser is running |
| 0 URLs after scrape | Hub tab must be on `herts.ac.uk` with CF cleared; check `COURSE_PATH_PATTERNS` |
| Script uses wrong tab | Close extra tabs; keep one `herts.ac.uk` tab leftmost |
| Port busy | `--remote-debugging-port=9223` and set `COURSE_DOWNLOAD_CDP_URL=http://127.0.0.1:9223` |

Saved reference HTML (optional): `course_listing/undergraduate-hub.html`, `undergraduate.html`, `postgraduate.html`.
