# main_window.py

## 1. Purpose

Main dashboard UI: university status table, phase buttons, run mode, study-level checkboxes, live terminal, and job progress.

**Does not** run pipeline logic inline — builds subprocess commands only.

---

## 2. Where this file is used

```
main.py → MainWindow(repo_root, config)
```

---

## 3. Dependencies

| Import | Why |
|--------|-----|
| PySide6 widgets | Table, buttons, layout |
| `status_loader.load_status` | Refresh table data |
| `TaskRunner` | Background subprocess |
| `TerminalWidget` | Log pane |

---

## 4. Main class: `MainWindow`

### UI sections built in `_build_ui()`

- Summary label (uni counts)
- Filter combo (URLs not started / done / incomplete)
- `QTableWidget` — 9 columns per [dashboard.md](../../dashboard.md)
- Phase buttons 1–5 + Run remaining + Open folder + Cancel
- Study level checkboxes + Full/Number radio
- `TerminalWidget`

### Key methods

| Method | Role |
|--------|------|
| `refresh_status()` | Reload rows from `pipeline_status` |
| `_fill_table()` | Apply colours from `STATUS_COLORS` |
| `_on_selection()` | Enable buttons from `can_*` flags |
| `_run_phase(phase_id)` | Validate + start job |
| `_phase_args(phase_id)` | Map run mode → CLI flags |
| `_phase_command()` | Build `[python, script, --code-dir, ...]` |
| `_start_command()` | Create `TaskRunner`, connect signals |
| `_update_job_progress()` | Poll extraction progress during LLM |
| `_sync_level_checks()` | Checkbox labels with URL counts |

---

## 5. Phase mapping

```python
PHASES = {
    "scrape_urls": "shared/scrape_course_urls.py",
    "uni_clean": "shared/download_and_clean_course_pages.py",
    "presetup": "shared/run_course_pipeline.py",
    ...
}
```

`code_dir = repo_root / university / "code"` — always the `code` subfolder.

---

## 6. Run modes

| `_run_mode()` | `_phase_args` effect |
|---------------|---------------------|
| Resume | Default; `--resume` on LLM phases |
| Fresh | `--fresh` + confirmation dialog |
| Append URLs | `--append-urls` on scrape only |

---

## 7. LLM guard

`_ollama_ok(host)` before Presetup LLM and Execute — HTTP GET `/api/tags`.

---

## 8. Why it was written this way

- **Subprocess not import:** Playwright + Qt event loops conflict; subprocess matches manual CLI.
- **Timer refresh:** Filesystem is source of truth; no push notifications from pipeline.
- **Study levels on Scrape + Execute:** Same checkboxes, different validation (Execute requires ≥1).

---

## 9. Read this next

1. [task_runner.md](task_runner.md)
2. [shared/pipeline_status.md](../shared/pipeline_status.md)
3. [features/dashboard-ui-flow.md](../features/dashboard-ui-flow.md)
