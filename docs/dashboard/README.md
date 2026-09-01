# Dashboard — code documentation index

Level 3 docs for the PySide6 desktop UI. Operational guide: [dashboard.md](../../dashboard.md).

---

## Files

| Doc | File | Role |
|-----|------|------|
| [main.md](main.md) | `main.py` | App entry point |
| [main_window.md](main_window.md) | `app/ui/main_window.py` | Main UI, phase buttons, table |
| [task_runner.md](task_runner.md) | `app/core/task_runner.py` | Background subprocess thread |
| [status_loader.md](status_loader.md) | `app/core/status_loader.py` | Status scan wrapper |

### Short reference

**`app/ui/terminal_widget.py`** — `TerminalWidget(QTextEdit)` with timestamped coloured log lines (`append_stdout`, `append_stderr`, `append_info`). No pipeline logic.

**`pipeline_config.json`** — `ollama_host` and phase metadata; UI phase mapping is in `main_window.PHASES`.

---

## Feature flow

[features/dashboard-ui-flow.md](../features/dashboard-ui-flow.md)

---

## Read order

1. [main.md](main.md)
2. [main_window.md](main_window.md)
3. [task_runner.md](task_runner.md)
4. [shared/pipeline_status.md](../shared/pipeline_status.md)
