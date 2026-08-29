# RUN — all pipeline commands

Quick reference for the university course pipeline on **any PC**.

> **Config:** `{University}/code/.env` (catalogue HTML paths are relative: `../course_listing/...`)  
> **Outputs:** `{University}/output/` (not `code/`)

Clone the repo, then work from that folder (do not hard-code `D:\...`):

```powershell
Set-Location <path-to-UK_Uni_Data>
```

```cmd
cd /d <path-to-UK_Uni_Data>
```

Replace `Anglia Ruskin University - ARU` with any university folder name below.

---

## One-time setup

```powershell
pip install -r shared/requirements.txt
playwright install chromium
```

Phase 3+ also needs **Ollama** running locally (`http://localhost:11434`).

---

## Universities

| Folder name |
|-------------|
| Anglia Ruskin University - ARU |
| Aston University |
| Birmingham City University |
| Brunel University London |
| Buckinghamshire New University |
| Canterbury Christ Church University |
| Cardiff Metropolitan University |
| Keele University |
| Kingston University |
| University of Birmingham |
| University of Essex |
| University of Greenwich |
| University of Huddersfield |
| University of Hull |
| University of Law |

Set your active university:

```powershell
$UNI = "Anglia Ruskin University - ARU"
```

---

## Quick run — scrape, uni clean, Presetup

From the repo root (any PC):

```powershell
$UNI = "Anglia Ruskin University - ARU"

python shared/scrape_course_urls.py --code-dir "$UNI/code"
python shared/download_and_clean_course_pages.py --code-dir "$UNI/code" --clean-uni-only
python shared/run_course_pipeline.py --code-dir "$UNI/code" --presetup
```

Then open `$UNI/output/course_pages/` and `$UNI/output/clean/pre_setup_course/`, check HTML and markdown, and edit `$UNI/code/.env` plus `$UNI/code/course_markdown_cleanup.py` if needed.

```powershell
python shared/run_course_pipeline.py --code-dir "$UNI/code" --presetup-llm --resume
python shared/run_course_pipeline.py --code-dir "$UNI/code" --execute --study-level foundation --all --resume
python shared/run_course_pipeline.py --code-dir "$UNI/code" --execute --study-level foundation undergraduate --limit 25 --resume
```

`--fresh` on `--presetup` draws a new random sample. Resume skips URLs already downloaded and courses already extracted.

---

## Quick run — LLM after Presetup / Execute

Requires Ollama. Prefer `--presetup-llm` and `--execute` (per-course). The batch helper still exists:

```powershell
python shared/run_llm_to_dev_csv.py --university $UNI --resume
python shared/run_llm_to_dev_csv.py --university $UNI --limit 5 --resume
python shared/run_llm_to_dev_csv.py --university $UNI --presetup --extract-only --resume
python shared/run_llm_to_dev_csv.py --university $UNI --extract-only --resume
python shared/run_llm_to_dev_csv.py --university $UNI --skip-extract
python shared/run_llm_to_dev_csv.py --university $UNI --resume --model llama3.1:8b --host http://localhost:11434
```

### `shared/run_llm_to_dev_csv.py` flags

| Flag | Effect |
|------|--------|
| `--university` | University folder name |
| `--code-dir` | Path to `{University}/code` |
| `--resume` | Skip completed courses |
| `--limit N` | First N courses only |
| `--build-index` | Force rebuild `output/courses.csv` |
| `--skip-extract` | Skip Phase 3; run normalize + export only |
| `--skip-normalize` | Skip Phase 4 |
| `--extract-only` | Phase 3 only |
| `--skip-stage1` | Reuse cached `stage1_parsed.json` |
| `--presetup` | Extract only URLs in `output/presetup_sample.json` |
| `--study-level LEVEL` | Repeatable. Restrict extract to a study level |
| `--model` | Ollama model name |
| `--host` | Ollama host URL |

**Resume file:** `{University}/output/extracted/extraction_progress.json`

---

## Full pipeline — scrape through Execute

```powershell
$UNI = "Anglia Ruskin University - ARU"

python shared/scrape_course_urls.py --code-dir "$UNI/code"
python shared/download_and_clean_course_pages.py --code-dir "$UNI/code" --clean-uni-only
python shared/run_course_pipeline.py --code-dir "$UNI/code" --presetup
python shared/run_course_pipeline.py --code-dir "$UNI/code" --presetup-llm --resume
python shared/run_course_pipeline.py --code-dir "$UNI/code" --execute --study-level foundation --all --resume
```

---

## Phase 1 — Scrape URLs

**Script:** `shared/scrape_course_urls.py`  
**Output:** `output/course_urls.csv`, `output/scrape_progress.json`, `output/scrape.log`

```powershell
python shared/scrape_course_urls.py" --code-dir "$UNI/code"

# Re-extract all URLs from scratch
python shared/scrape_course_urls.py" --code-dir "$UNI/code" --fresh

# Merge new URLs into existing course_urls.csv
python shared/scrape_course_urls.py" --code-dir "$UNI/code" --append-urls
```

Resume: re-run without `--fresh`. Progress in `output/scrape_progress.json`.

---

## Presetup + Execute (recommended)

**Script:** `shared/run_course_pipeline.py`

After scrape + uni clean, do **not** download the full catalogue. Sample 10 mixed-level courses, review cleanup, then Execute per course.

```powershell
python shared/run_course_pipeline.py --code-dir "$UNI/code" --presetup
python shared/run_course_pipeline.py --code-dir "$UNI/code" --presetup-llm --resume
python shared/run_course_pipeline.py --code-dir "$UNI/code" --execute --study-level foundation --all --resume
python shared/run_course_pipeline.py --code-dir "$UNI/code" --execute --study-level foundation --limit 25 --resume
```

Human pause after `--presetup`: check `output/course_pages/` and `output/clean/pre_setup_course/{level}/`, then edit `code/.env` and `code/course_markdown_cleanup.py`.

---

## Phase 2 — Download + clean (bulk / power user)

**Script:** `shared/download_and_clean_course_pages.py`  
**Outputs:** `output/course_pages/`, `output/clean/courses/`, `output/clean/uni/`, `output/clean/manifest.json`, `output/clean_warnings.csv`

```powershell
# Download all course pages + clean to markdown (default)
python shared/download_and_clean_course_pages.py" --code-dir "$UNI/code"

# Test first 5 courses
python shared/download_and_clean_course_pages.py" --code-dir "$UNI/code" --limit 5

# Re-download all URLs (clears download progress)
python shared/download_and_clean_course_pages.py" --code-dir "$UNI/code" --fresh

# Download HTML only (skip clean)
python shared/download_and_clean_course_pages.py" --code-dir "$UNI/code" --download-only

# Clean existing course HTML only (skip download)
python shared/download_and_clean_course_pages.py" --code-dir "$UNI/code" --clean-only

# Clean uni_req/*.html -> clean/uni/ only
python shared/download_and_clean_course_pages.py" --code-dir "$UNI/code" --clean-uni-only

# Clean both courses + uni_req (no download)
python shared/download_and_clean_course_pages.py" --code-dir "$UNI/code" --clean-all
```

Resume download: re-run default command without `--fresh`. Skips URLs in `downloaded_urls` inside `scrape_progress.json`.

**uni_req files (save manually once):**

| File | Clean output |
|------|----------------|
| `uni_req/bangladesh-entry.html` | `output/clean/uni/bangladesh-entry.md` |
| `uni_req/english-requirements.html` | `output/clean/uni/english-requirements.md` |
| `uni_req/scholarships.html` | `output/clean/uni/scholarships.md` |
| `uni_req/deposit.html` | `output/clean/uni/deposit.md` |

---

## Phase 3 — LLM extract

**Script:** `shared/llm_extract.py`  
**Requires:** Ollama running  
**Outputs:** `output/extracted/{slug}/`, `output/courses.csv`

```powershell
# Full extract (Stage 1 + entry, English, scholarship, deposit)
python shared/llm_extract.py" "$UNI/code"

# Test first 5 courses
python shared/llm_extract.py" "$UNI/code" --limit 5

# Resume after interruption
python shared/llm_extract.py" "$UNI/code" --resume

# Rebuild course index only
python shared/llm_extract.py" "$UNI/code" --build-index

# One course by markdown filename
python shared/llm_extract.py" "$UNI/code" --md-file study-postgraduate-accounting-and-finance.md

# One course by index (1-based)
python shared/llm_extract.py" "$UNI/code" --course-index 3

# Re-run Stage 2 only (reuse cached stage1_parsed.json)
python shared/llm_extract.py" "$UNI/code" --skip-stage1

# Custom Ollama model / host
python shared/llm_extract.py" "$UNI/code" --model llama3.1:8b --host http://localhost:11434
```

---

## Phase 4 — Normalize

**Script:** `shared/normalize_admission_data.py`  
**Output:** `output/extracted/{slug}/normalized.json`

```powershell
python shared/normalize_admission_data.py" "$UNI/code"
```

---

## Phase 5 — Export dev CSV

**Script:** `shared/export_dev_courses.py`  
**Output:** `output/dev_courses_{UNIVERSITY_NAME}.csv`

```powershell
python shared/export_dev_courses.py" "$UNI/code"
```

---

## Resume after power cut

| Stopped during | Command |
|----------------|---------|
| Phase 1 (URL scrape) | `.\run_upto_llm_extract.ps1 -University $UNI -Resume` or re-run Phase 1 without `--fresh` |
| Phase 2 (download) | `.\run_upto_llm_extract.ps1 -University $UNI -Resume` |
| Phase 2 (clean only) | `.\run_upto_llm_extract.ps1 -University $UNI -Resume -SkipScrape -CleanOnly` |
| Phase 3 (LLM) | `python shared/llm_extract.py" "$UNI/code" --resume` |

Check progress:

```powershell
Get-Content (Join-Path (Get-Location) "$UNI\output\scrape_progress.json") | ConvertFrom-Json | Select-Object phase, @{n='downloaded';e={$_.downloaded_urls.Count}}, @{n='urls';e={$_.course_urls.Count}}
```

---

## Per-university examples

### Anglia Ruskin University - ARU

```powershell
$UNI = "Anglia Ruskin University - ARU"

.\run_upto_llm_extract.ps1 -University $UNI -Resume
python shared/llm_extract.py" "$UNI/code" --resume
python shared/normalize_admission_data.py" "$UNI/code"
python shared/export_dev_courses.py" "$UNI/code"
```

ARU uses `COURSE_CLEAN_ENGINE=utopian` in `code/.env`.

### Aston University

```powershell
$UNI = "Aston University"
.\run_upto_llm_extract.ps1 -University $UNI -Limit 5
```

### Birmingham City University

```powershell
$UNI = "Birmingham City University"
.\run_upto_llm_extract.ps1 -University $UNI
```

### Brunel University London

```powershell
$UNI = "Brunel University London"
.\run_upto_llm_extract.ps1 -University $UNI
```

### Buckinghamshire New University

```powershell
$UNI = "Buckinghamshire New University"
.\run_upto_llm_extract.ps1 -University $UNI
```

### Canterbury Christ Church University

```powershell
$UNI = "Canterbury Christ Church University"
.\run_upto_llm_extract.ps1 -University $UNI
```

### Cardiff Metropolitan University

```powershell
$UNI = "Cardiff Metropolitan University"
.\run_upto_llm_extract.ps1 -University $UNI
```

### Keele University

```powershell
$UNI = "Keele University"
.\run_upto_llm_extract.ps1 -University $UNI
```

### Kingston University

```powershell
$UNI = "Kingston University"
.\run_upto_llm_extract.ps1 -University $UNI
```

### University of Birmingham

```powershell
$UNI = "University of Birmingham"
.\run_upto_llm_extract.ps1 -University $UNI
```

### University of Essex

```powershell
$UNI = "University of Essex"
.\run_upto_llm_extract.ps1 -University $UNI
```

### University of Greenwich

```powershell
$UNI = "University of Greenwich"
.\run_upto_llm_extract.ps1 -University $UNI
```

### University of Huddersfield

```powershell
$UNI = "University of Huddersfield"
.\run_upto_llm_extract.ps1 -University $UNI
```

### University of Hull

```powershell
$UNI = "University of Hull"
.\run_upto_llm_extract.ps1 -University $UNI
```

### University of Law

```powershell
$UNI = "University of Law"
.\run_upto_llm_extract.ps1 -University $UNI
```

---

## Other scripts

```powershell
# Split master UK Course.csv into per-university portal CSVs (repo root)
python shared/export_portal_courses.py"

# Rebuild courseName → programmeName dictionary (only if UK Course.csv changes)
python shared/programme_name_dictionary.py

# Bootstrap a new university folder
python shared/bootstrap_university.py" "New University - SHORT"

# Analyse a saved listing HTML (debug selectors)
python shared/analyze_catalogue_html.py" "path\to\listing.html"
```

---

## Output layout

```
{University}/
  code/
    .env
    course_markdown_cleanup.py   # optional per-uni markdown rules
  uni_req/                       # 4 fixed HTML files (manual save)
  course_listing/                # listing HTML for Phase 1
  output/
    course_urls.csv
    scrape_progress.json
    course_pages/
    clean/
      courses/*.md
      uni/*.md
      manifest.json
    extracted/
    dev_courses_*.csv
```

---

## Related docs

- [PIPELINE.md](PIPELINE.md) — architecture and phase details
- [scrape_course_urls_CMD.md](scrape_course_urls_CMD.md) — Phase 1 CMD commands (this PC)
- [README.md](README.md) — HTML clean engines (`COURSE_CLEAN_ENGINE`)
