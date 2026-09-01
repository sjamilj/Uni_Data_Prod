# Dashboard UI flow

How the PySide6 dashboard launches pipeline scripts without embedding business logic.

---

## Complete flow

```
User double-clicks START.bat
        ↓
dashboard/main.py
        ↓
MainWindow(repo_root, config)
        ↓
load_status(repo_root) → pipeline_status.scan_all_universities()
        ↓
Table shows one row per university with code/ENV.MD
        ↓
User clicks phase button
        ↓
MainWindow._run_phase(phase_id)
        ↓
_phase_args() → CLI flags from run mode + checkboxes
        ↓
_phase_command() → [python, shared/script.py, --code-dir, Uni/code, ...]
        ↓
TaskRunner(QThread) subprocess, cwd=repo_root
        ↓
stdout/stderr → TerminalWidget
        ↓
On finish → refresh_status() re-scans output/
```

---

## Step table

| Step | File | What happens |
|------|------|--------------|
| 1 | `main.py` | `QApplication`, `MainWindow`, `load_config()` |
| 2 | `status_loader.load_status()` | Calls `scan_all_universities` + `summarize` |
| 3 | `MainWindow.refresh_status()` | Fills table, colours cells |
| 4 | `MainWindow._on_selection()` | Enables/disables buttons from row flags |
| 5 | `MainWindow._run_phase()` | Validates Ollama for LLM phases |
| 6 | `MainWindow._phase_command()` | Maps `PHASES` dict to script path |
| 7 | `TaskRunner.run()` | `Popen` with `PYTHONUNBUFFERED=1` |
| 8 | `TaskRunner._stream_output()` | Threads read stdout/stderr → Qt signals |
| 9 | `MainWindow._update_job_progress()` | Polls `extraction_progress.json` during LLM |

---

## Phase → script mapping

Defined in `main_window.PHASES`:

| phase_id | Script |
|----------|--------|
| `scrape_urls` | `shared/scrape_course_urls.py` |
| `uni_clean` | `shared/download_and_clean_course_pages.py` |
| `presetup` | `shared/run_course_pipeline.py` |
| `presetup_llm` | `shared/run_course_pipeline.py` |
| `execute` | `shared/run_course_pipeline.py` |

---

## Run modes

| UI mode | Effect |
|---------|--------|
| Resume | Default; passes `--resume` where applicable |
| Fresh | `--fresh` on scrape/presetup; confirmation dialog |
| Append URLs | `--append-urls` on scrape only |

---

## Study level checkboxes

Used by:

- **Scrape URLs** — `--study-level` per ticked box
- **Execute** — required; at least one must be ticked

Counts come from `row["level_counts"]` in status scan.

---

## Auto-refresh

`QTimer` every 5s (2s while job running) calls `refresh_status()` to update table from disk.

---

## Why thin UI

The dashboard could have imported `CourseUrlScraper` directly, but subprocess isolation:

- Avoids Qt + Playwright event-loop conflicts
- Same commands as manual CLI (reproducible)
- Crash in pipeline does not kill the UI process

---

## Read this next

1. [dashboard/main_window.md](../dashboard/main_window.md)
2. [dashboard/task_runner.md](../dashboard/task_runner.md)
3. [shared/pipeline_status.md](../shared/pipeline_status.md)
4. [dashboard.md](../../dashboard.md)
