# main.py

## 1. Purpose

Entry point for the PySide6 dashboard application. Boots Qt, resolves repo root, loads config, shows `MainWindow`.

---

## 2. Where this file is used

```
START.bat / START.sh
  → python dashboard/main.py
```

---

## 3. Key functions

### `load_config()`

Reads `dashboard/pipeline_config.json` (Ollama host, phase metadata).

### `main()`

1. `QApplication(sys.argv)`
2. `app.setStyle("Fusion")`
3. `MainWindow(repo_root=REPO_ROOT, config=load_config())`
4. `app.exec()`

---

## 4. Path setup

```python
DASHBOARD_DIR = Path(__file__).resolve().parent
REPO_ROOT = DASHBOARD_DIR.parent
sys.path.insert(0, str(DASHBOARD_DIR))
sys.path.insert(0, str(REPO_ROOT / "shared"))
```

**Why insert `shared`:** Allows future direct imports if needed; status_loader imports `pipeline_status` from shared.

---

## 5. Why it was written this way

Minimal entry file — all UI logic in `main_window.py` for testability and clarity.

---

## 6. Read this next

1. [main_window.md](main_window.md)
2. [features/dashboard-ui-flow.md](../features/dashboard-ui-flow.md)
