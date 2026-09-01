# run_course_pipeline.py

## 1. Purpose

Orchestrates **Presetup**, **Presetup LLM**, and **Execute** — the phases that tie download, clean, LLM, normalize, and export together.

Human-in-the-loop design: Presetup stops after 10 courses for review before scaling.

---

## 2. Where this file is used

```
Dashboard buttons 3, 4, 5
  → PipelineOrchestrator
  → subprocess / direct calls to download_and_clean + llm_extract + normalize + export
```

---

## 3. Dependencies

| Module | Why |
|--------|-----|
| `download_and_clean_course_pages` | HTML + MD |
| `llm_extract` | `run_extraction`, `configure_code_dir` |
| `study_level` | Stratified sample, level URLs |
| `uni_paths` | Paths |
| `subprocess` | Normalize + export steps |

---

## 4. Main classes

### `PipelineOrchestrator`

| Method | CLI flag |
|--------|----------|
| `run_presetup()` | `--presetup` |
| `run_presetup_llm()` | `--presetup-llm` |
| `run_execute()` | `--execute` |

### `PipelineCLI`

argparse + dispatches to orchestrator.

---

## 5. Key methods

### `run_presetup()`

1. Load URLs from level CSVs
2. `sample_urls_stratified()` → 10 courses
3. Save `presetup_sample.json`
4. Call download/clean into `pre_setup_course/`

### `run_presetup_llm()`

1. Check Ollama reachable
2. `configure_code_dir()`
3. `run_extraction()` on presetup markdown only

### `run_execute()`

1. Build URL list from `--study-level` + `--all` or `--limit`
2. Save `execute_selection.json`
3. **For each URL sequentially:**
   - Download + clean one course
   - LLM extract one course
   - Respect `--resume` skip
4. Run normalize + export subprocesses at end

**Why one-at-a-time:** Resume granularity, lower memory, easier failure isolation.

---

## 6. Important code

```python
EXECUTE_SELECTION_JSON = "execute_selection.json"
```

Dashboard progress bar reads this + `extraction_progress.json` to show `LLM extract: 3/25 done`.

---

## 7. Why it was written this way

Single orchestrator avoids operators chaining 4 scripts manually. Subprocess for normalize/export keeps those CLIs independently runnable.

---

## 8. Artifacts

| File | Phase |
|------|-------|
| `presetup_sample.json` | Presetup |
| `execute_selection.json` | Execute |
| `extraction_progress.json` | LLM |
| `dev_courses_*.csv` | End of Execute |

---

## 9. Prerequisites

- [features/presetup-and-execute-flow.md](../features/presetup-and-execute-flow.md)
- Ollama running for LLM phases

---

## 10. Read this next

1. [study_level.md](study_level.md)
2. [llm_extract.md](llm_extract.md)
3. [download_and_clean_course_pages.md](download_and_clean_course_pages.md)
