---
name: uni-presetup
description: Runs the 5-course presetup download and clean, human review checkpoint, then presetup-llm extraction. Use for presetup, presetup-llm, or a sample of 5 test courses before full execute.
---

# Presetup (5 courses + LLM)

Git: [git-for-operator.md](../git-for-operator.md).

## Prerequisites

- `output/course_urls.csv` from **uni-course-urls**
- `output/clean/uni/*.md` from **uni-req-json** (for Stage 2 entry/English/scholarship/deposit)
- Course clean config from **uni-course-clean**

## Step 1 — Download and clean 5 courses (no LLM)

From repo root:

```powershell
python shared/run_course_pipeline.py --code-dir "{University}/code" --presetup --sample-size 5 --fresh
```

Use `--fresh` to rebuild `output/presetup_sample.json` when changing the sample.

**Important:** If `output/presetup_urls.csv` already exists (from `scrape_course_urls.py --presetup`), the pipeline uses **every URL in that file** and ignores `--sample-size`. For exactly **5 total** courses:

- Run full URL scrape **without** `--presetup`, then run `--presetup --sample-size 5`, or
- Delete `presetup_urls.csv` before presetup if you do not want per-level scrape samples.

`scrape_course_urls.py --presetup --presetup-per-level 5` keeps 5 URLs **per study level**, not 5 overall.

## Human review (stop)

Check:

- `output/course_pages/`
- `output/clean/pre_setup_course/{level}/*.md`

Fix `code/.env`, `code/ENV.MD`, and `code/course_markdown_cleanup.py` if intake, duration, or fee shapes fail [stage1-contract.md](../uni-course-clean/stage1-contract.md).

## Step 2 — LLM on the same 5

Confirm `presetup_sample.json` lists the intended URLs, then:

```powershell
python shared/run_course_pipeline.py --code-dir "{University}/code" --presetup-llm --resume
```

Outputs: `output/extracted/pre_setup_course_extracted/{level}/{slug}/` (`output.json`, `stage1_parsed.json`, audits).

## Empty Stage 1 fields

If `intakeInfo`, `courseDuration`, or `tuitionFee` are empty in `stage1_parsed.json`, go back to **uni-course-clean** — parser-owned fields are not fixed by re-running LLM alone.

## After presetup passes review

Full catalogue: `python shared/run_course_pipeline.py --code-dir "{University}/code" --execute --study-level ... --all --resume`

See [docs/features/presetup-and-execute-flow.md](../../docs/features/presetup-and-execute-flow.md).
