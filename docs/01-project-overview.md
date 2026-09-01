# Project overview

## What this project does

**UK Uni Data** is a data pipeline that:

1. **Scrapes** course listing pages from UK university websites (Playwright)
2. **Extracts** course URLs, split by study level (foundation, undergraduate, postgraduate, PGR)
3. **Downloads and cleans** course HTML into markdown
4. **Extracts** international admission data via a local LLM (Ollama): entry requirements, English scores, scholarships, deposits, fees, intakes
5. **Normalizes** records into a consistent schema
6. **Exports** a developer CSV (`dev_courses_{University}.csv`) for downstream use

Each university is a **separate folder** under the repo root with its own `code/.env` configuration and `output/` artifacts.

---

## Who it is for

- Operators running the pipeline on many universities (dashboard or PowerShell scripts)
- Developers onboarding new universities or fixing extraction for one CMS
- Anyone learning how a **filesystem-resumable**, **config-driven** scrape-and-extract system is structured

---

## What it is not

- Not a web app with users, auth, or a database
- Not a single monolithic scraper — logic is shared; config is per university
- Not fully automated end-to-end — **Presetup** deliberately stops for human review of HTML/markdown before full LLM runs

---

## Major components

| Component | Path | Role |
|-----------|------|------|
| Shared pipeline | `shared/` | All business logic (~37 Python modules) |
| Dashboard | `dashboard/` | PySide6 UI to view status and launch phases |
| University folders | `{University Name}/` | `code/` (config), `uni_req/` (HTML), `output/` (generated) |
| Template | `_university_template/` | Bootstrap layout for new universities |

---

## Pipeline phases (high level)

```
Scrape URLs → Clean uni pages → Presetup (10 courses) → [human review]
    → Presetup LLM → Execute (per course) → Normalize → Export CSV
```

The dashboard labels these as buttons 1–5 plus normalize/export at the end of Execute.

---

## Design principles

1. **Config over code** — URL patterns, CSS selectors, and clean blocks live in `code/.env` / `ENV.MD`, not hardcoded per uni in `shared/`.
2. **Resume everywhere** — Progress JSON lets you stop and continue without redoing finished work.
3. **Thin dashboard** — UI only launches `python shared/<script>.py --code-dir ...`; no duplicated pipeline logic.
4. **Study-level split** — URLs and extracted JSON are partitioned by foundation / undergraduate / postgraduate / PGR.
5. **Presetup before scale** — Validate cleanup on 10 mixed courses before running thousands through the LLM.

---

## See also

- Operational workflow: [PIPELINE.md](../PIPELINE.md)
- Architecture detail: [02-architecture.md](02-architecture.md)
- Learning path: [00-start-here.md](00-start-here.md)
