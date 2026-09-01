# pipeline_status.py

## 1. Purpose

Scans university folders on disk and returns structured status for the dashboard table and `pipeline_status.py` CLI.

**Read-only** — never runs pipeline phases.

---

## 2. Where this file is used

```
dashboard/status_loader.py  → load_status()
dashboard/main_window.py    → refresh_status() every 5s
CLI: python shared/pipeline_status.py [--json]
```

---

## 3. Main classes

| Class | Role |
|-------|------|
| `PipelineStatusConfig` | Skip folders, Cloudflare uni list, required uni_req files |
| `PipelineStatusIO` | Read JSON, count CSV rows, tail scrape.log |
| `UniversityStatusDetector` | One university → status dict |
| `PipelineStatusScanner` | Scan repo root, filter by `code/ENV.MD` |
| `PipelineStatusCLI` | argparse |
| `StatusLabel` | Map booleans → `done` / `partial` / `not_started` |

---

## 4. Key method: `UniversityStatusDetector.detect()`

Returns dict with keys:

| Key | Detection logic |
|-----|-----------------|
| `setup` | Count of `uni_req` HTML files |
| `urls` | `course_urls.csv` + progress phase |
| `uni_clean` | `clean/uni/*.md` |
| `presetup` | `presetup_sample.json` vs pre_setup markdown |
| `download` | downloaded vs clean course MD |
| `llm` | `extraction_progress.json` completed count |
| `normalize` | `normalized.json` presence |
| `csv` | `dev_courses_*.csv` |
| `level_counts` | Per-level URL counts for checkboxes |
| `can_*` | Button enable flags |

---

## 5. University discovery

```python
SKIP_FOLDERS = {"shared", "dashboard", "_university_template"}
# Include if: (repo_root / name / "code" / "ENV.MD").is_file()
```

**Why ENV.MD gate:** Confirms university is set up for the pipeline, not just an empty folder.

---

## 6. Cloudflare flag

Hardcoded list: South Wales, UWTSD, West London — UI shows tooltip; scrape may need headed browser.

---

## 7. Why it was written this way

Dashboard stays thin by delegating all status logic here. Same scanner powers CLI and UI — one source of truth.

---

## 8. Artifacts read

Everything under `{University}/output/` and `uni_req/` — see [04-data-flow.md](../04-data-flow.md).

---

## 9. Read this next

1. [features/dashboard-ui-flow.md](../features/dashboard-ui-flow.md)
2. [dashboard/status_loader.md](../dashboard/status_loader.md)
3. [dashboard.md](../../dashboard.md)
