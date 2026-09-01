# task_runner.py

## 1. Purpose

Runs one pipeline command in a background `QThread` so the dashboard UI stays responsive and streams stdout/stderr to the terminal pane.

---

## 2. Where this file is used

```
MainWindow._start_command()
  → TaskRunner(task_id, command, repo_root)
  → runner.start()
```

---

## 3. Main class: `TaskRunner(QThread)`

### Signals

| Signal | When |
|--------|------|
| `started` | Process spawned |
| `stdout_ready` | Line on stdout |
| `stderr_ready` | Line on stderr |
| `finished` | Exit code 0 |
| `failed` | Non-zero exit, timeout, cancel |

---

## 4. Key methods

### `run()`

1. `subprocess.Popen(command, cwd=cwd, stdout=PIPE, stderr=PIPE, text=True)`
2. Set `PYTHONUNBUFFERED=1` for live terminal output
3. `_stream_output()` in daemon threads
4. `wait()` with optional timeout
5. Emit finished/failed

### `stop()`

Sets `_should_stop`, `terminate()` process, `kill()` after 5s timeout.

Connected to Cancel button.

### `_stream_output()`

Two threads read stdout/stderr line-by-line, emit Qt signals to main thread.

**Why threads:** `readline()` blocks; threads avoid freezing Qt while waiting for output.

---

## 5. Important code

```python
env["PYTHONUNBUFFERED"] = "1"
env["PYTHONIOENCODING"] = "utf-8"
```

Without unbuffered Python, operators see no output until the subprocess exits.

---

## 6. Why it was written this way

`QThread` + `Popen` is the standard Qt pattern for long external jobs. Keeps `main_window.py` free of threading details.

---

## 7. Read this next

1. [main_window.md](main_window.md)
2. [07-how-to-run.md](../07-how-to-run.md)
