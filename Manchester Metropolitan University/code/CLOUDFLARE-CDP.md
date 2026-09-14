# MMU — Cloudflare + CDP (Brave)

Use this when MMU shows **“Verifying you are human”** in an automated Playwright window, or when you want **paginated course-search** URLs (not Swiftype only).

**Shared reference:** [docs/shared/cloudflare-course-download.md](../../docs/shared/cloudflare-course-download.md)

**Required in `code/.env`:**

```env
COURSE_DOWNLOAD_USE_DEVICE_PROFILE=false
COURSE_DOWNLOAD_CDP_URL=http://127.0.0.1:9222
COURSE_LISTING_FETCH=browser
COURSE_DOWNLOAD_CLOUDFLARE_WARMUP=false
COURSE_DOWNLOAD_CLOUDFLARE_AUTO_CLICK=false
```

Run all commands from the **repo root** (`Uni_Data_Prod`).

---

## A. Re-scrape URLs with pagination

Uses `UNDERGRADUATE_COURSE_LISTING_PAGE_1` (and `_PAGE_2` for page step) in `.env`. Needs **`COURSE_LISTING_FETCH=browser`** and CDP.

1. **Close all Brave windows** (Task Manager → no `brave.exe`).

2. **Start Brave with debugging:**

```powershell
& "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" --remote-debugging-port=9222
```

3. In that window, open the **same URL as `UNDERGRADUATE_COURSE_LISTING_PAGE_1`** (course search page 1) and pass Cloudflare once. Wait until you see search results (e.g. “Displaying 1–10 of …”).

4. **Run URL scrape** (leave Brave open):

```powershell
python -u shared/scrape_course_urls.py --code-dir "Manchester Metropolitan University/code" --fresh
```

5. Check `output/course_urls.csv`. When the count looks right, continue with **B** in the **same** Brave session (do not close the browser).

`--fresh` resets URL extraction progress only; use it when you intentionally re-list all courses.

---

## B. Download + clean course pages

Uses `course_urls.csv` and the same CDP Brave as **A**.

1. **Close all Brave windows** (if you are not continuing from **A**).

2. **Start Brave with debugging:**

```powershell
& "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" --remote-debugging-port=9222
```

3. Open any **MMU course URL** (from `output/course_urls.csv`) and wait until the **real course page** loads (fees/tabs) — not stuck on “Verifying you are human”.

4. **Run download** (leave Brave open):

```powershell
python -u shared/download_and_clean_course_pages.py --code-dir "Manchester Metropolitan University/code"
```

Progress resumes from `output/scrape_progress.json` (no `--fresh` unless you want to re-download everything).

---

## One session for both A and B

You can do **A** then **B** without restarting Brave: pass Cloudflare on **course search** for listing, run scrape, then run download — the script re-attaches to `http://127.0.0.1:9222`.

---

## If `brave.exe` is not found

Try:

```powershell
Test-Path "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
```

Some installs use `%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe` instead.

---

## Swiftype fallback (no browser for listing)

If you cannot use CDP for listing only:

```env
COURSE_LISTING_FETCH=swiftype
SWIFTYPE_ENGINE_KEY=…
```

Faster, but may return fewer URLs than live paginated search (~326 vs ~382 full-time).
