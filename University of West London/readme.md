# University of West London (unit-28 / uwl)

| Item | Value |
|------|--------|
| Registry | `unit-28` · slug `uwl` |
| Strategy | `DEGREE_SCOPED_PAGINATED` · `Paginated.csv` |
| Base URL | https://www.uwl.ac.uk |

## Course URLs (scrape)

| File | Count |
|------|------:|
| `output/course_urls.csv` | **197** |
| `output/undergraduate_course_urls.csv` | 81 |
| `output/postgraduate_course_urls.csv` | 81 |
| `output/postgraduate_research_course_urls.csv` | 35 |
| `output/foundation_course_urls.csv` | 63 |

`output/scrape_progress.json` → `phase`: `urls_complete`. Dashboard **URLs** column shows **197**; **Download** shows **0/197** until pages are cleaned.

More detail: `code/CLOUDFLARE-CDP.md`.

## Cloudflare — Edge CDP (PowerShell)

Copy-paste in PowerShell (run **block 1** fully, then **block 2**).

### 1 — Start Edge CDP + check port

```powershell
$repo = "e:\Project Next\UK UNIVERSITIES\UNI\Uni_Data_Prod"
Set-Location $repo
Copy-Item -Force "University of West London\code\ENV.MD" "University of West London\code\.env"
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

If that last line errors, Edge is not in CDP mode — fix that before block 2. Complete Cloudflare in **that** Edge window if it appears.

### 2 — Foundation URLs only

```powershell
Set-Location "e:\Project Next\UK UNIVERSITIES\UNI\Uni_Data_Prod"
python -u shared/scrape_course_urls.py --code-dir "University of West London/code" --study-level foundation --append-urls
```

You should see: `Connected to existing browser via http://127.0.0.1:9222`

**Presetup download/clean:** use block 1 but open a **course detail** URL instead of `$search`, then:

```powershell
python -u shared/run_course_pipeline.py --code-dir "University of West London/code" --presetup
```

## Saved HTML (manual)

| Folder | Purpose |
|--------|---------|
| `uni_req/` | Bangladesh entry, English, scholarships (+ save `deposit.html` from after-you-apply when refreshing) |
| `course_listing/` | `paginated_course.html`, `last_page.html` |
| `course_detail/` | Sample course page(s) for clean tuning |

## Next pipeline steps

1. ~~**Course URLs**~~ — done (197; CDP Edge)
2. **Uni req JSON** — refresh `deposit.md` after saving deposit HTML; tune `output/clean/uni/*.md` if needed
3. **5-course presetup** — download/clean trial set, then presetup LLM
