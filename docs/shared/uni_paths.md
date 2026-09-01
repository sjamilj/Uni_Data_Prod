# uni_paths.py

## 1. Purpose

Resolves the two directory trees every pipeline script uses:

- **`code/`** — configuration (`.env`, optional hooks)
- **`output/`** — generated artifacts (CSVs, HTML, clean/, extracted/)

Without this module, scripts would guess paths from `cwd()` and create folders in the wrong place.

---

## 2. Where this file is used

Called at the start of nearly every `shared/*.py` CLI:

```
--code-dir University/code
  → resolve_code_dir()
  → resolve_output_dir()
  → read/write under University/output/
```

| Caller | Usage |
|--------|-------|
| `scrape_course_urls.py` | `CourseUrlScraper.__init__` |
| `llm_extract.py` | `configure_code_dir()` |
| `run_course_pipeline.py` | Presetup/Execute paths |
| `export_dev_courses.py` | Output CSV path |

---

## 3. Dependencies

| Dependency | Why |
|------------|-----|
| `pathlib.Path` | Cross-platform paths |

No external packages.

---

## 4. Main class

### `UniPathResolver`

Static methods only; module exposes aliases `resolve_code_dir` and `resolve_output_dir`.

---

## 5. Key methods

### `resolve_code_dir(work_dir=None)`

Returns `(work_dir or Path.cwd()).resolve()`.

**Input:** `--code-dir` from CLI, or current working directory.

### `resolve_output_dir(code_dir=None)`

**Process:**

1. Resolve `code_dir` via `resolve_code_dir`
2. If folder name is `code` → `code.parent / "output"` (sibling of code)
3. Else → `code / "output"` (uni root passed directly)
4. `mkdir(parents=True, exist_ok=True)`

```
resolve_output_dir(.../ARU/code)
  → .../ARU/output

resolve_output_dir(.../UK_Uni_Data)   # repo root by mistake
  → .../UK_Uni_Data/output            # inside repo, not parent/output
```

---

## 6. Important code

```python
if code.name == "code":
    out = code.parent / cls.OUTPUT_DIR_NAME
else:
    out = code / cls.OUTPUT_DIR_NAME
```

**Why two branches:** Dashboard always passes `University/code`. Some legacy scripts pass the university root; both must land on the same `output/` folder.

---

## 7. Why it was written this way

Centralizing path logic prevents the bug where `code.parent / "output"` was used unconditionally — when `cwd` was the repo root, that created `D:\...\output\output` outside the project.

---

## 8. Artifacts

Creates `output/` directory if missing (empty folder until first write).

---

## 9. Prerequisites

- Python `pathlib`
- Folder layout: [03-folder-structure.md](../03-folder-structure.md)

---

## 10. Read this next

1. [05-env-and-config.md](../05-env-and-config.md)
2. [scrape_course_urls.md](scrape_course_urls.md)
