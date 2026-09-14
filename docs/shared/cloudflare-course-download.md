# Cloudflare and course page download

When a university site shows **“Verifying you are human”** or **“Just a moment”** during automated download, normal browsing may work once while **Playwright-launched** Chrome/Edge/Brave often **loops forever**. Use **CDP** (attach to your real browser with remote debugging).

**MMU copy-paste steps:** [Manchester Metropolitan University/code/CLOUDFLARE-CDP.md](../../Manchester%20Metropolitan%20University/code/CLOUDFLARE-CDP.md)

---

## Quick start — two workflows (example: MMU)

Replace `{University}` with your folder name. Run from **repo root**.

### Required `.env` (CDP)

```env
COURSE_DOWNLOAD_USE_DEVICE_PROFILE=false
COURSE_DOWNLOAD_CDP_URL=http://127.0.0.1:9222
COURSE_DOWNLOAD_CLOUDFLARE_WARMUP=false
COURSE_DOWNLOAD_CLOUDFLARE_AUTO_CLICK=false
COURSE_DOWNLOAD_HEADLESS=false
```

For **paginated listing**, also:

```env
COURSE_LISTING_FETCH=browser
```

---

### Workflow A — Re-scrape URLs with pagination

Uses listing seeds such as `UNDERGRADUATE_COURSE_LISTING_PAGE_1` in `.env`. The scraper walks `?page=1,2,3…` using “Displaying X–Y of Z results”.

1. Close all Brave windows (Task Manager if needed).

2. Start Brave with debugging:

```powershell
& "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" --remote-debugging-port=9222
```

3. Open the **same URL as `PAGE_1`** (course search) in that window and pass Cloudflare once.

4. Run:

```powershell
python -u shared/scrape_course_urls.py --code-dir "Manchester Metropolitan University/code" --fresh
```

5. When `output/course_urls.csv` looks good, continue with **Workflow B** in the **same** Brave window (CDP stays in `.env`).

---

### Workflow B — Download + clean course pages

1. Close all other Brave windows (skip if continuing from **A** in the same session).

2. Start Brave with debugging:

```powershell
& "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" --remote-debugging-port=9222
```

3. Open a **course detail URL** and wait until the real course page loads (not “Verifying you are human”).

4. Run (leave Brave open):

```powershell
python -u shared/download_and_clean_course_pages.py --code-dir "Manchester Metropolitan University/code"
```

Download progress resumes from `output/scrape_progress.json` unless you pass `--fresh`.

---

## Symptoms

| What you see | Likely cause |
|--------------|--------------|
| Course search / listing returns **0 URLs** in headed Playwright | Cloudflare on paginated search pages |
| Playwright window stuck on **“Verifying you are human. This may take a few seconds.”** | Bot check never completes under automation |
| You pass CF once in **your** browser, but the **script’s** browser keeps asking | Copied cookies are not enough; Playwright fingerprint is flagged |
| `Retry … Page.goto: Timeout` then reload and CF again | Retries reloaded the page and reset Turnstile (mitigated in code; use CDP) |
| `Permission denied` on `Network/Cookies` during profile sync | Real browser still running — quit all instances before refresh |

---

## Listing modes

| Mode | `.env` | Notes |
|------|--------|--------|
| **Browser pagination + CDP** | `COURSE_LISTING_FETCH=browser` + `COURSE_DOWNLOAD_CDP_URL=…` | Live search pages; same debugging browser as download |
| **Swiftype HTTP** | `COURSE_LISTING_FETCH=swiftype` + `SWIFTYPE_ENGINE_KEY` | No browser; fast; may miss courses vs live search |

---

## Browser paths (Windows)

| Browser | Typical path |
|---------|----------------|
| Brave | `C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe` |
| Brave (user install) | `%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe` |
| Edge | `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` |
| Chrome | `C:\Program Files\Google\Chrome\Application\chrome.exe` |

```powershell
Test-Path "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
```

Other browsers: same `--remote-debugging-port=9222`; keep `COURSE_DOWNLOAD_CDP_URL` in sync.

---

## Fallback: device profile

Works for some unis (e.g. Kingston + Edge), often **not** for strict MMU Cloudflare:

```env
COURSE_DOWNLOAD_USE_DEVICE_PROFILE=true
COURSE_DOWNLOAD_BROWSER=edge
COURSE_DOWNLOAD_REFRESH_DEVICE_PROFILE=true
```

Quit browser completely, refresh profile once, then set `REFRESH` back to `false`. If CF loops, use **CDP** instead.

---

## Environment variables (reference)

| Variable | Purpose |
|----------|---------|
| `COURSE_DOWNLOAD_CDP_URL` | e.g. `http://127.0.0.1:9222` |
| `COURSE_LISTING_FETCH` | `browser` (pagination + CDP) or `swiftype` |
| `COURSE_DOWNLOAD_USE_DEVICE_PROFILE` | `false` when using CDP |
| `COURSE_DOWNLOAD_CLOUDFLARE_WARMUP` | `false` for CDP |
| `COURSE_DOWNLOAD_CLOUDFLARE_AUTO_CLICK` | keep `false` if CF reloads |
| `COURSE_DOWNLOAD_CLOUDFLARE_WAIT_SECONDS` | max wait for manual verify (MMU often `300`) |

Implementation: `shared/scrape_course_urls.py` (`BrowserSession`), `shared/browser_device_profile.py`.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `brave.exe` not recognized | Full path under `Program Files` (see table above) |
| `No browser tab at http://127.0.0.1:9222` | Start debugging browser first; open a tab |
| Port in use | `--remote-debugging-port=9223` and update `COURSE_DOWNLOAD_CDP_URL` |
| CF clears in manual Brave but script fails | Use only the **9222** debugging window |
| `Just a moment.html` in `course_pages/` | Remove bad HTML; fix `scrape_progress.json`; retry |
| Listing 0 URLs without CDP | Use Swiftype or **Workflow A** with CDP |

---

## Security

- Do not commit `.env` secrets or `.device-profile-*`.
- CDP allows local control of your browser — trusted PC only while scraping.

---

## Read next

1. [download_and_clean_course_pages.md](download_and_clean_course_pages.md)
2. [features/download-clean-flow.md](../features/download-clean-flow.md)
3. [scrape_course_urls.md](scrape_course_urls.md)
