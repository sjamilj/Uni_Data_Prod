# University Data Pipeline Dashboard

Double-click `START.bat` on Windows, or run `START.sh` on macOS/Linux. No machine-specific paths.

The window lists every university folder that has `code/ENV.MD` and shows pipeline status from files on disk. Phase buttons run `shared/*.py` with `--code-dir`.

Full wiring guide: [`../dashboard.md`](../dashboard.md)

## Run mode

Use the **Run mode** dropdown before clicking a phase button:

| Mode | What it does |
|------|----------------|
| **Resume** | Keep progress. Skip URLs / HTML / LLM courses already done. Default. |
| **Fresh** | Start that step over (asks for confirmation). Presetup draws a new random sample of 10. |
| **Append URLs** | Scrape only: merge new URLs into `course_urls.csv`. |

| Button | Script |
|--------|--------|
| 1 Scrape URLs | `shared/scrape_course_urls.py` (`--fresh` / `--append-urls`) |
| 2 Clean Uni Pages | `shared/download_and_clean_course_pages.py --clean-uni-only` |
| 3 Presetup (10 mixed) | `shared/run_course_pipeline.py --presetup` |
| 4 Presetup LLM | `shared/run_course_pipeline.py --presetup-llm --resume` |
| 5 Execute | `shared/run_course_pipeline.py --execute` plus study-level checkboxes and Full / Number |

After Presetup, open the university folder and check HTML + markdown, then edit `.env` / cleanup code before Presetup LLM.

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
