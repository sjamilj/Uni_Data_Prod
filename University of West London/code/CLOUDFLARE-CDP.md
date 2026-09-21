# UWL — Cloudflare + CDP (your browser session)

Use when UWL shows **“Verifying you are human”** in Playwright, or when the **device-profile** Edge window keeps looping.

**Shared reference:** [docs/shared/cloudflare-course-download.md](../../../docs/shared/cloudflare-course-download.md)  
**Skill:** [uni-course-urls](../../../.cursor/skills/uni-course-urls/SKILL.md) (CDP section)

**Required in `code/.env` (mirrored in `ENV.MD`):**

```env
COURSE_DOWNLOAD_USE_DEVICE_PROFILE=false
COURSE_DOWNLOAD_CDP_URL=http://127.0.0.1:9222
COURSE_DOWNLOAD_BROWSER=edge
COURSE_DOWNLOAD_HEADLESS=false
COURSE_DOWNLOAD_CLOUDFLARE_WARMUP=false
COURSE_DOWNLOAD_CLOUDFLARE_AUTO_CLICK=false
```

Run all commands from the **repo root** (`Uni_Data_Prod`).

---

## A. Re-scrape course URLs (paginated search)

Uses `COURSE_LISTING_PAGE_1` / `COURSE_LISTING_PAGE_2` in `.env`.

1. **Close all Edge windows** (Task Manager → no `msedge.exe`).

2. **Start Edge with remote debugging** (Windows: you need a **dedicated** profile dir or port 9222 will not listen):

```powershell
$repo = "e:\Project Next\UK UNIVERSITIES\UNI\Uni_Data_Prod"
Set-Location $repo
$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
$profile = Join-Path $repo "University of West London\code\.cdp-edge-profile"
New-Item -ItemType Directory -Force -Path $profile | Out-Null
Get-Process msedge -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
$search = "https://www.uwl.ac.uk/courses/search?q=/courses/search%3Fquery%3D&f%5B0%5D=Mode%3AFull-time&f%5B1%5D=level%3AUndergraduate&f%5B2%5D=refine_results%3A1&query=&page=0"
Start-Process -FilePath $edge -ArgumentList "--remote-debugging-port=9222", "--user-data-dir=$profile", $search
Start-Sleep -Seconds 5
(Invoke-WebRequest "http://127.0.0.1:9222/json/version" -UseBasicParsing).Content
```

Do **not** run the scrape until the last line prints JSON (`"Browser": "Edg/..."`). Pass Cloudflare in that Edge window if needed.

You should see JSON with `"Browser": "Edg/..."`. If the last command fails, Edge is not in CDP mode — do not run the scrape yet.

**Note:** `.cdp-edge-profile` is a separate session (not your daily Edge cookies). Pass Cloudflare once in **this** window; later runs reuse the same folder so you usually only verify once.

3. In **that** Edge window only, open the course search (same as `COURSE_LISTING_PAGE_1`):

`https://www.uwl.ac.uk/courses/search?q=/courses/search%3Fquery%3D&f%5B0%5D=Mode%3AFull-time&query=&page=0`

Pass Cloudflare and accept cookies. Wait until you see course titles (e.g. **219 results found**).

4. Sync `.env` and run scrape (**leave Edge open**):

```powershell
cd "e:\Project Next\UK UNIVERSITIES\UNI\Uni_Data_Prod"
Copy-Item -Force "University of West London\code\ENV.MD" "University of West London\code\.env"
python -u shared/scrape_course_urls.py --code-dir "University of West London/code" --fresh
```

5. Check `University of West London/output/course_urls.csv`.

---

## B. Download + clean course pages

Same CDP Edge session as **A** (or restart Edge with step 2 if needed).

1. In the **9222** Edge window, open a **course detail** URL from `course_urls.csv` and confirm the real page loads (not Cloudflare).

2. Run download (**leave Edge open**):

```powershell
cd "e:\Project Next\UK UNIVERSITIES\UNI\Uni_Data_Prod"
python -u shared/download_and_clean_course_pages.py --code-dir "University of West London/code"
```

Progress resumes from `output/scrape_progress.json` unless you pass `--fresh`.

---

## One session for A and B

Do **A** then **B** without closing Edge: the script re-attaches to `http://127.0.0.1:9222`.

---

## Brave instead of Edge

1. Close all Brave windows.

```powershell
& "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" --remote-debugging-port=9222
```

2. Set `COURSE_DOWNLOAD_BROWSER=brave` in `ENV.MD` / `.env`, then steps 3–4 above.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Could not connect to http://127.0.0.1:9222` | Start Edge/Brave with `--remote-debugging-port=9222` first; keep one tab open |
| Port in use | Use `--remote-debugging-port=9223` and `COURSE_DOWNLOAD_CDP_URL=http://127.0.0.1:9223` |
| CF passes in normal Edge but script fails | Only use the **debugging** window (9222), not a regular Edge launch |
| Still on device-profile Playwright | Set `COURSE_DOWNLOAD_USE_DEVICE_PROFILE=false` and **unset** refresh; use CDP URL |
