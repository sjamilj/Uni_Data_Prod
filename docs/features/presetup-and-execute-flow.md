# Presetup and Execute flow

The most important human-in-the-loop path: validate on 10 courses, then scale.

---

## Why Presetup exists

Downloading and LLM-processing every course is slow and expensive. Presetup:

1. Picks **10 stratified** courses across available study levels
2. Downloads HTML + cleans to markdown **only for those 10**
3. **Stops** for human review of `.env` and cleanup rules
4. Runs LLM on those 10 (`--presetup-llm`)
5. Execute processes the full catalogue **one course at a time**

---

## Presetup flow

```
course_urls.csv + level CSVs
        ↓
run_course_pipeline.py --presetup
        ↓
PresetupSampler.sample_urls_stratified() → 10 URLs
        ↓
save presetup_sample.json
        ↓
download_and_clean_course_pages (subset)
        ↓
clean/pre_setup_course/{level}/*.md
        ↓
[STOP — human reviews HTML + markdown + .env]
        ↓
run_course_pipeline.py --presetup-llm --resume
        ↓
llm_extract on 10 courses only
        ↓
extracted/pre_setup_course_extracted/{level}/{slug}/
```

---

## Execute flow

```
User selects study levels + Full or Limit N
        ↓
run_course_pipeline.py --execute --study-level ... --all|--limit N
        ↓
save execute_selection.json
        ↓
FOR EACH course URL (sequential):
    download HTML
    clean → clean/courses/{level}/{slug}.md
    llm_extract → extracted/{level}/{slug}/
        ↓
normalize_admission_data (batch at end)
        ↓
export_dev_courses.py → dev_courses_*.csv
```

---

## Step table — Presetup

| Step | File / class | What happens |
|------|--------------|--------------|
| 1 | `PipelineOrchestrator.run_presetup()` | Entry point |
| 2 | `sample_urls_stratified()` | Picks 10 across levels |
| 3 | `save_presetup_sample()` | Writes `presetup_sample.json` |
| 4 | `download_and_clean_course_pages()` | Subset download to `pre_setup_course` |
| 5 | Operator | Reviews files, edits config |

---

## Step table — Execute

| Step | File / class | What happens |
|------|--------------|--------------|
| 1 | `PipelineOrchestrator.run_execute()` | Parses levels, limit, resume |
| 2 | `_save_execute_selection()` | `execute_selection.json` |
| 3 | Loop per URL | Download → clean → `run_extraction()` |
| 4 | `_already_extracted()` | Skips if resume + slug in progress |
| 5 | `normalize` subprocess | All `output.json` → `normalized.json` |
| 6 | `export_dev_courses` subprocess | Final CSV |

---

## Dashboard buttons

| Button | CLI equivalent |
|--------|----------------|
| 3 Presetup | `--presetup` (+ `--fresh` if Fresh mode) |
| 4 Presetup LLM | `--presetup-llm --resume` |
| 5 Execute | `--execute --study-level ... --all` or `--limit N` |

Execute requires study-level checkboxes ticked in UI.

---

## Progress files

| File | Tracks |
|------|--------|
| `presetup_sample.json` | Which 10 URLs |
| `scrape_progress.json` | `downloaded_urls` during presetup |
| `extraction_progress.json` | LLM completed slugs |
| `execute_selection.json` | Full execute scope |

---

## Read this next

1. [shared/run_course_pipeline.md](../shared/run_course_pipeline.md)
2. [shared/study_level.md](../shared/study_level.md)
3. [llm-extraction-flow.md](llm-extraction-flow.md)
4. [PIPELINE.md](../../PIPELINE.md) — review checklist
