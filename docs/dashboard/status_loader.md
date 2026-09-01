# status_loader.py

## 1. Purpose

Thin adapter between the dashboard and `shared/pipeline_status.py`. One function: load all university rows + summary counts.

---

## 2. Where this file is used

```python
# main_window.py
from app.core.status_loader import load_status

self.rows, summary = load_status(self.repo_root)
```

---

## 3. Implementation

```python
def load_status(repo_root: Path) -> tuple[list[dict], dict]:
    rows = scan_all_universities(repo_root)
    return rows, summarize(rows)
```

Adds `shared/` to `sys.path` if not already present.

---

## 4. Return shape

**`rows`:** list of dicts per university (name, setup, urls, can_execute, level_counts, …)

**`summary`:** aggregates for header label:

- `universities`
- `urls_done`
- `download_done`
- `csv_done`

---

## 5. Why a separate file

Keeps `main_window.py` smaller and makes it obvious where to mock status in tests.

---

## 6. Read this next

1. [shared/pipeline_status.md](../shared/pipeline_status.md)
2. [main_window.md](main_window.md)
