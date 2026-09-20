# UWL — device profile (fallback)

**Preferred:** attach to your real browser with CDP — **[CLOUDFLARE-CDP.md](CLOUDFLARE-CDP.md)** (same flow as [uni-course-urls](../../../.cursor/skills/uni-course-urls/SKILL.md)).

Use this file only if CDP is not an option. Synced Edge profile + headed Playwright.

See also [docs/shared/cloudflare-course-download.md](../../../docs/shared/cloudflare-course-download.md).

## One-time profile sync

1. Close **all** Edge windows (Task Manager if needed).
2. In `code/.env`, keep `COURSE_DOWNLOAD_REFRESH_DEVICE_PROFILE=true` for this run only.
3. Open Edge normally once, visit https://www.uwl.ac.uk/courses/search and pass Cloudflare + accept cookies.
4. Quit Edge completely again.

## Course URL scrape

```powershell
cd "e:\Project Next\UK UNIVERSITIES\UNI\Uni_Data_Prod"
Copy-Item -Force "University of West London\code\ENV.MD" "University of West London\code\.env"
python -u shared/scrape_course_urls.py --code-dir "University of West London/code" --fresh
```

- A visible Edge window opens (not headless).
- If Cloudflare appears, complete it in that window; the script waits up to `COURSE_DOWNLOAD_CLOUDFLARE_WAIT_SECONDS`.
- After a successful run, set `COURSE_DOWNLOAD_REFRESH_DEVICE_PROFILE=false` in `ENV.MD` / `.env` so later runs do not recopy the profile.

## Download + clean course pages

Same `.env` keys; leave Edge closed except the Playwright window:

```powershell
python -u shared/download_and_clean_course_pages.py --code-dir "University of West London/code"
```

## CDP alternative

If the synced profile still loops on Cloudflare, use Brave/Edge with `--remote-debugging-port=9222`, pass CF manually, set `COURSE_DOWNLOAD_CDP_URL` and `COURSE_DOWNLOAD_USE_DEVICE_PROFILE=false` (see MMU `CLOUDFLARE-CDP.md`).
