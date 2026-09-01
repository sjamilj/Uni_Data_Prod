# How to run

Quick reference for CLI and dashboard. For full command examples, see [PIPELINE.md](../PIPELINE.md).

---

## Prerequisites (once per machine)

```powershell
pip install -r shared/requirements.txt
python -m playwright install chromium
pip install -r dashboard/requirements.txt   # PySide6, for UI only
```

Ollama for LLM phases: `http://localhost:11434`

---

## Dashboard (recommended for operators)

```powershell
# Windows
dashboard\START.bat

# macOS/Linux
dashboard/START.sh

# Or manual
Set-Location dashboard
python main.py
```

1. Select a university row (must have `code/ENV.MD`)
2. Choose **Run mode**: Resume / Fresh / Append URLs
3. Click phase buttons 1–5
4. For Execute: tick study levels, choose Full or Number

See [dashboard.md](../dashboard.md) and [features/dashboard-ui-flow.md](features/dashboard-ui-flow.md).

---

## CLI — single university

Always pass `--code-dir` pointing at `{University}/code`.

### Phase 1 — Scrape URLs

```powershell
python shared/scrape_course_urls.py --code-dir "Aston University/code"
python shared/scrape_course_urls.py --code-dir "Aston University/code" --study-level foundation
python shared/scrape_course_urls.py --code-dir "Aston University/code" --fresh
python shared/scrape_course_urls.py --code-dir "Aston University/code" --append-urls
```

### Phase 2 — Clean uni pages

```powershell
python shared/download_and_clean_course_pages.py --code-dir "Aston University/code" --clean-uni-only
```

### Phases 3–5 — Presetup / LLM / Execute

```powershell
python shared/run_course_pipeline.py --code-dir "Aston University/code" --presetup
python shared/run_course_pipeline.py --code-dir "Aston University/code" --presetup-llm --resume
python shared/run_course_pipeline.py --code-dir "Aston University/code" --execute --study-level foundation --all --resume
```

### Normalize + export only

```powershell
python shared/normalize_admission_data.py --code-dir "Aston University/code"
python shared/export_dev_courses.py --code-dir "Aston University/code"
```

Or combined:

```powershell
python shared/run_llm_to_dev_csv.py --code-dir "Aston University/code" --resume
```

---

## Status without UI

```powershell
python shared/pipeline_status.py
python shared/pipeline_status.py --json
```

---

## Build `.env` from fragments

```powershell
python shared/build_env.py --code-dir "Anglia Ruskin University - ARU/code"
python shared/build_env.py --all
```

---

## Review handoff

After `dev_courses_{University}_reviewed.csv` exists in `{University}/output/`, package the root variant CSV and reviewed export into `REVIEW/{University}/`:

```powershell
python shared/package_review_output.py "Anglia Ruskin University - ARU"
# or from repo root:
package_review.bat "Anglia Ruskin University - ARU"
```

Output layout:

```
REVIEW/
  Anglia Ruskin University - ARU/
    DegreeScopedPaginated.csv
    dev_courses_Anglia Ruskin University - ARU_reviewed.csv
```

Fails if the university folder, root variant CSV, or reviewed CSV is missing.

---

## PowerShell wrappers (repo root)

| Script | Purpose |
|--------|---------|
| `run_scrape_urls.ps1` | URL scrape |
| `run_uni_clean.ps1` | Uni page clean |
| `run_upto_llm_extract.ps1` | Through LLM |
| `run_llm_to_dev_csv.ps1` | LLM → CSV |

---

## Working directory rules

| Context | CWD | Required arg |
|---------|-----|--------------|
| Dashboard subprocess | Repo root | `--code-dir` auto-built |
| Manual CLI | Repo root (recommended) | `--code-dir` |
| Legacy | `University/code` | optional if cwd is code dir |

**Outputs always go to** `{University}/output/`, never repo root (see `uni_paths.py`).

---

## Logs

| File | Content |
|------|---------|
| `output/scrape.log` | URL scrape + download |
| Dashboard terminal pane | Live stdout/stderr of current job |

---

## See also

- [00-start-here.md](00-start-here.md) — learning path
- [PIPELINE.md](../PIPELINE.md) — detailed workflow
- [dashboard.md](../dashboard.md) — UI reference
