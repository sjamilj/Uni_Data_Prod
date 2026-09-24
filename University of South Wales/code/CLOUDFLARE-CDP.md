# University of South Wales — Cloudflare + CDP (Brave)

Use when listing or course pages show **“Verifying you are human”** in Playwright, or URL scrape fails with Cloudflare retries.

**Shared reference:** [docs/shared/cloudflare-course-download.md](../../docs/shared/cloudflare-course-download.md)

**Required in `code/.env`:** (already set — do not use legacy `COURSE_LISTING_PAGE_1`; use `UNDERGRADUATE_*` / `POSTGRADUATE_*` listing keys.)

Run from **repo root** (`Uni_Data_Prod`).

---

## A. Re-scrape course URLs (paginated listings)

1. Close all Brave windows (Task Manager → no `brave.exe`).

2. Start Brave with remote debugging:

```powershell
& "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" --remote-debugging-port=9222
```

3. In **that** window, open the same URL as `UNDERGRADUATE_COURSE_LISTING_PAGE_1` in `.env`:

`https://www.southwales.ac.uk/courses/?courselevel=undergraduate&coursemode=full-time&page=1`

Pass Cloudflare once. Wait until course result links appear (not the challenge page).

4. Leave Brave open and run:

```powershell
python -u shared/scrape_course_urls.py --code-dir "University of South Wales/code" --fresh
```

You should see **three** listing scopes in the log (`undergraduate`, `postgraduate`, and optionally foundation catalogue) — not a single scope named `courses`.

5. Check `University of South Wales/output/course_urls.csv`.

---

## B. Download + clean course pages

Same CDP Brave as **A** (or restart Brave on 9222 and open any USW course URL from `course_urls.csv`).

```powershell
python -u shared/download_and_clean_course_pages.py --code-dir "University of South Wales/code"
```

---

## Tips

| Issue | Fix |
|-------|-----|
| Script tab is not the tab you verified | Complete CF on the tab Playwright navigates (often leftmost CDP tab). |
| Retries too fast | `COURSE_DOWNLOAD_CLOUDFLARE_WAIT_SECONDS=300` is set; solve CF during the wait. |
| Edge/Chrome instead of Brave | Change `COURSE_DOWNLOAD_BROWSER=` and start that browser with `--remote-debugging-port=9222`. |
| Still scope `courses` in log | `.env` still has `COURSE_LISTING_PAGE_1` — remove it; use degree-scoped `*_COURSE_LISTING_PAGE_*` keys from `ENV.MD`. |
