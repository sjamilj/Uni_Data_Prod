# Folder structure

## Repo root

```
UK_Uni_Data/
├── docs/                    # Learning documentation (this tree)
├── shared/                  # Shared pipeline Python + prompts
├── dashboard/               # PySide6 desktop UI
├── _university_template/    # Copy for new universities
├── PIPELINE.md              # Operational runbook
├── dashboard.md             # Dashboard wiring guide
├── README.md
└── {University Name}/       # One folder per university
```

Skipped by scanners: `shared`, `dashboard`, `_university_template`, dot-folders.

---

## University folder layout

```
Anglia Ruskin University - ARU/
├── code/
│   ├── ENV.MD               # Committed config template (source of truth for git)
│   ├── .env                 # Generated/local runtime config (gitignored)
│   ├── env/
│   │   ├── common.env       # Optional fragments merged by build_env.py
│   │   └── foundation.env
│   ├── course_markdown_cleanup.py   # Optional per-uni MD rules
│   └── course_html_builder.py       # Optional plugin engine
├── uni_req/                 # Saved HTML: entry, English, scholarships, deposit
├── course_listing/          # Optional saved listing HTML (ALL_COURSE strategy)
├── course_detail/           # Optional saved sample course HTML (debugging)
└── output/                  # ALL generated artifacts (never in code/)
    ├── course_urls.csv
    ├── foundation_course_urls.csv
    ├── scrape_progress.json
    ├── scrape.log
    ├── clean/
    │   ├── uni/*.md
    │   ├── courses/{level}/*.md
    │   └── pre_setup_course/{level}/*.md
    ├── extracted/{level}/{slug}/
    ├── presetup_sample.json
    ├── execute_selection.json
    └── dev_courses_{UNIVERSITY_NAME}.csv
```

---

## `code/` vs `output/`

| Folder | Purpose | Git |
|--------|---------|-----|
| `code/` | Configuration, optional hooks | `ENV.MD` yes; `.env` no |
| `output/` | Everything produced by scripts | Mostly gitignored (large/regenerated) |

Resolution logic lives in `shared/uni_paths.py`:

- `--code-dir` points at `{University}/code`
- `resolve_output_dir(code_dir)` → `{University}/output`

**Why sibling layout:** Operators edit config in `code/` without mixing generated HTML/JSON into the same tree. Scripts always receive `--code-dir` so they work from any working directory.

---

## `shared/` layout

```
shared/
├── scrape_course_urls.py           # Phase 1: URLs
├── download_and_clean_course_pages.py
├── run_course_pipeline.py          # Presetup + Execute
├── llm_extract.py
├── normalize_admission_data.py
├── export_dev_courses.py
├── pipeline_status.py
├── study_level.py
├── uni_paths.py
├── course_markdown_cleanup.py
├── build_env.py
├── engines/
│   ├── generic.py
│   └── utopian.py
├── prompt_1.md                     # LLM prompt templates
├── prompt_2_*.md
└── test_entry_requirements.py
```

---

## `dashboard/` layout

```
dashboard/
├── main.py
├── pipeline_config.json    # Ollama host, phase metadata
├── START.bat / START.sh
├── requirements.txt        # PySide6
└── app/
    ├── core/
    │   ├── status_loader.py
    │   └── task_runner.py
    └── ui/
        ├── main_window.py
        └── terminal_widget.py
```

---

## Path resolution rules (`uni_paths.py`)

```python
# code_dir = .../University/code
if code.name == "code":
    output = code.parent / "output"   # .../University/output
else:
    output = code / "output"          # fallback if code_dir is uni root
```

**Why the branch:** Dashboard and CLI always pass `.../code`, but some scripts may pass the university root; both must resolve to the same `output/`.

---

## See also

- Config keys: [05-env-and-config.md](05-env-and-config.md)
- Artifact lifecycle: [04-data-flow.md](04-data-flow.md)
- Code: [shared/uni_paths.md](shared/uni_paths.md)
