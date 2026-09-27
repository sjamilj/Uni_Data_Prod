# LSBU — Cloudflare + CDP (Microsoft Edge)

LSBU course pages show **“Verifying you are human”** under Playwright-launched browsers. Attach the downloader to **Edge** with remote debugging.

**Shared reference:** [docs/shared/cloudflare-course-download.md](../../docs/shared/cloudflare-course-download.md)

**Already in `code/.env`:**

```env
COURSE_DOWNLOAD_USE_DEVICE_PROFILE=false
COURSE_DOWNLOAD_BROWSER=edge
COURSE_DOWNLOAD_CDP_URL=http://127.0.0.1:9222
COURSE_DOWNLOAD_CLOUDFLARE_WARMUP=false
COURSE_DOWNLOAD_CLOUDFLARE_AUTO_CLICK=false
COURSE_DOWNLOAD_HEADLESS=false
COURSE_DOWNLOAD_CLOUDFLARE_WAIT_SECONDS=300
```

LSBU uses **ALL_COURSE** (saved listing HTML) — you only need **download + presetup** with CDP, not live listing pagination.

Run commands from **repo root** (`Uni_Data_Prod`).

---

## Presetup (dashboard or CLI)

1. **Start Edge with CDP** (from repo root). The script stops any running Edge and uses a **dedicated profile** (`code/.cdp-edge-profile`) — required on Windows or port **9222 never listens**.

```powershell
powershell -ExecutionPolicy Bypass -File "London South Bank University\code\start-edge-cdp.ps1"
```

Wait until it prints **`CDP OK: Edg/...`**. If it exits with an error, do not run presetup yet.

Manual equivalent:

```powershell
$profile = "D:\DATA SCOL\TEMP 2\Uni_Data_Prod\London South Bank University\code\.cdp-edge-profile"
Get-Process msedge -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --remote-debugging-address=127.0.0.1 --user-data-dir="$profile" --remote-allow-origins=* "https://www.lsbu.ac.uk/study/course-finder/msc-cyber-security"
```

3. Confirm CDP is listening (should print browser version):

```powershell
Invoke-RestMethod http://127.0.0.1:9222/json/version
```

4. In **that Edge window only**, pass Cloudflare on the course page if needed:

`https://www.lsbu.ac.uk/study/course-finder/building-services-engineering-with-foundation-year`

Wait until you see the real course page (title, tabs) — not “Verifying you are human”.

5. **Leave Edge open** and run presetup:

```powershell
cd "D:\DATA SCOL\TEMP 2\Uni_Data_Prod"
python -u shared/run_course_pipeline.py --code-dir "London South Bank University/code" --presetup --fresh
```

Or download only:

```powershell
python -u shared/download_and_clean_course_pages.py --code-dir "London South Bank University/code" --fresh
```

6. Review `output/clean/pre_setup_course/`, then:

```powershell
python -u shared/run_course_pipeline.py --code-dir "London South Bank University/code" --presetup-llm --resume
```

---

## Full catalogue download

Same CDP Edge session as above:

```powershell
python -u shared/download_and_clean_course_pages.py --code-dir "London South Bank University/code"
```

(Omit `--fresh` to resume from `output/scrape_progress.json`.)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Same Cloudflare error | Use only the **9222** debugging Edge window; pass CF on a **course** URL first |
| `Could not connect to http://127.0.0.1:9222` | Start Edge with `--remote-debugging-port=9222`; keep at least one tab open |
| `msedge.exe` not found | Run `Test-Path` on both paths above; install Edge or fix the path in your shortcut |
| Port in use | `--remote-debugging-port=9223` and set `COURSE_DOWNLOAD_CDP_URL=http://127.0.0.1:9223` |
| Bad HTML in `course_pages/` | Remove bad files, fix `scrape_progress.json`, retry with CDP |

---

## Security

Do not commit `.env`. CDP gives local control of your browser — use on a trusted PC only while scraping.
