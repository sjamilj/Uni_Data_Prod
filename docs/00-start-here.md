# Start here — learning the codebase

This `/docs` tree is a **guided course** for understanding `shared/` (pipeline) and `dashboard/` (desktop UI). It supplements operational runbooks — it does not replace them.

| Need | Read |
|------|------|
| Run the pipeline step-by-step | [PIPELINE.md](../PIPELINE.md) |
| Dashboard buttons and status columns | [dashboard.md](../dashboard.md) |
| **Understand why the code is shaped this way** | This folder |

---

## How the docs are organised

```
Project (Level 1)     → 01–07 overview docs
       ↓
Features (Level 2)    → docs/features/*.md — end-to-end flows
       ↓
Code (Level 3)        → docs/shared/*.md, docs/dashboard/*.md
       ↓
Utilities (Level 4)   → one-line index in docs/shared/README.md
```

Trace any question: **Project → Feature → File → Method**.

---

## Recommended reading order (first visit)

### Day 1 — big picture (30–45 min)

1. [01-project-overview.md](01-project-overview.md) — what the system does
2. [02-architecture.md](02-architecture.md) — modules and design rules
3. [04-data-flow.md](04-data-flow.md) — files on disk between phases
4. [features/presetup-and-execute-flow.md](features/presetup-and-execute-flow.md) — the most important human-in-the-loop path

### Day 2 — run something (20 min)

5. [07-how-to-run.md](07-how-to-run.md) — CLI + dashboard
6. [features/dashboard-ui-flow.md](features/dashboard-ui-flow.md) — how the UI launches scripts

### Day 3 — core pipeline code (pick one track)

**Track A — scraping**

7. [shared/uni_paths.md](shared/uni_paths.md)
8. [shared/scrape_course_urls.md](shared/scrape_course_urls.md)
9. [features/scrape-urls-flow.md](features/scrape-urls-flow.md)

**Track B — cleaning**

7. [shared/download_and_clean_course_pages.md](shared/download_and_clean_course_pages.md)
8. [shared/engines.md](shared/engines.md)
9. [features/download-clean-flow.md](features/download-clean-flow.md)

**Track C — LLM extraction**

7. [06-llm-and-ollama.md](06-llm-and-ollama.md)
8. [shared/llm_extract.md](shared/llm_extract.md)
9. [features/llm-extraction-flow.md](features/llm-extraction-flow.md)

### Day 4 — orchestration and export

10. [shared/run_course_pipeline.md](shared/run_course_pipeline.md)
11. [shared/normalize_admission_data.md](shared/normalize_admission_data.md)
12. [features/normalize-export-flow.md](features/normalize-export-flow.md)

---

## Prerequisites (concepts used everywhere)

| Concept | Used for |
|---------|----------|
| Python `pathlib.Path` | All path resolution via `uni_paths.py` |
| `argparse` + `--code-dir` | Every pipeline script targets one university |
| JSON checkpoint files | Resume after crash (`scrape_progress.json`, `extraction_progress.json`) |
| Playwright | Headless browser for listing/course HTML |
| Ollama HTTP API | Local LLM for structured extraction |
| PySide6 signals/slots | Dashboard background jobs without freezing UI |

---

## Full doc index

| Level | Folder |
|-------|--------|
| Project | `docs/01`–`07` |
| Features | [docs/features/](features/) |
| Shared code | [docs/shared/](shared/) |
| Dashboard code | [docs/dashboard/](dashboard/) |
| Template for new docs | [templates/code-file-template.md](templates/code-file-template.md) |

---

## Tests

Unit tests live in `shared/test_entry_requirements.py`. Run from repo root:

```powershell
python -m unittest shared.test_entry_requirements -q
```

Tests document expected behaviour for entry requirements, fee parsing, and uni-clean validation — useful when reading `llm_extract.py` and `normalize_admission_data.py`.
