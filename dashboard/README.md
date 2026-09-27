# University Data Pipeline Dashboard

Double-click `START.bat` on Windows, or run `START.sh` on macOS/Linux. No machine-specific paths.

The window lists every university folder that has `code/ENV.MD` and shows pipeline status from files on disk. Phase buttons run `shared/*.py` with `--code-dir`.

When you **select a university row**, the dashboard runs `scripts/checkout-uni.cmd -Pick <unit> -Commit <sha> -IncludeShared` from `UNIVERSITIES_REGISTRY.md`, then copies `code/ENV.MD` → `code/.env`. Toggle with `"activate_on_select": false` in `pipeline_config.json`. **aru** / **aston** skip checkout (study-level only); in-progress unis without a commit only sync `.env`.

Full wiring guide: [`../docs/dashboard.md`](../docs/dashboard.md)

## Run mode

Use the **Run mode** dropdown before clicking a phase button:

| Mode | What it does |
|------|----------------|
| **Resume** | Keep progress. Skip URLs / HTML / LLM courses already done. Default. |
| **Fresh** | Start that step over (asks for confirmation). Presetup rebuilds from presetup_urls.csv (or resamples 10 from full catalogue). |
| **Append URLs** | Scrape only: merge new URLs into `course_urls.csv`. |

| Button | Script |
|--------|--------|
| (1) Scrape URLs | `shared/scrape_course_urls.py` (`--fresh` / `--append-urls`) |
| (2) Presetup Scrape | `shared/scrape_course_urls.py --presetup` |
| (3) Presetup download_and_clean | `shared/run_course_pipeline.py --presetup` |
| (4) Presetup LLM | `shared/run_course_pipeline.py --presetup-llm --resume` |
| (5) Run Full Pipeline with One Course | `precalc_e2e_pins.py --uni` then `e2e_one_course.py` (one course). Needs (1) and Ollama. |
| (6) Execute | `shared/run_course_pipeline.py --execute` plus study-level checkboxes and Full / Number |
| **Pick Shared** | `git restore --source <tag> -- shared` — tag is the **Current reset baseline** row in `UNIVERSITIES_REGISTRY.md` (e.g. `shared/v1.2.2`), or set `shared_baseline_tag` in `pipeline_config.json` |
| **Restore HEAD** | `git switch main`, then `git restore --staged --worktree --source=HEAD` and `git clean -fd` on `shared/` and **every university folder** (default `back_to_main_restore_all_unis`: true). Discards uncommitted and untracked changes there; `dashboard/` is left as-is. Optional `back_to_main_source`: `origin/main` and `back_to_main_fetch_origin`: true. |

After Presetup download_and_clean, open the university folder and check HTML + markdown, then edit `.env` / cleanup code before Presetup LLM.

Execute downloads, cleans, and sends **one course at a time** to the LLM. Tick study levels (Foundation, Undergraduate, Postgraduate, PGR) and choose Full or a number.

LLM needs **Ollama** at `http://localhost:11434`.

Cloudflare-blocked sites (University of South Wales, University of Wales Trinity Saint David, University of West London) may fail a headless scrape. Check `output/scrape.log`.

## Manual start

From the repo root:

```powershell
Set-Location dashboard
python main.py
```

## Status CLI

From the repo root:

```powershell
python shared/pipeline_status.py
```
