---
name: uni-pipeline
description: >-
  Full new-university onboarding router (new-uni-setup → course URLs → course clean →
  uni_req JSON → presetup). Use when the user says uni-pipeline, whole onboarding order,
  all pipeline steps, or full setup for a new uni. Runbook docs/PIPELINE.md.
disable-model-invocation: true
---

# University onboarding pipeline

## Git

Follow [git-for-operator.md](../git-for-operator.md): never run git or chain commit/tag commands; give separate copy-paste blocks with **recommended** `-m` strings (user may edit before running). Scopes and tags: [CONTRIBUTING.md](../../CONTRIBUTING.md), [UNIVERSITIES_REGISTRY.md](../../UNIVERSITIES_REGISTRY.md); scripted add/commit lines: [scripts/README.md](../../scripts/README.md).

Run phases in order. Each phase has its own skill; do not duplicate their full instructions here — open the skill when you reach that step.

| Step | Skill | Outcome |
|------|-------|---------|
| 1 | **new-uni-setup** | `shared/` at `shared/v1.2.0`, variant CSV → `STRATEGY`, `ENV.MD` / `.env` aligned |
| 2 | **uni-course-urls** | `output/course_urls.csv`, exclusions for online/part-time at download time |
| 3 | **uni-course-clean** | `COURSE_CLEAN_*` tuned from `course_detail/`; markdown matches Stage 1 parser contract |
| 4 | **uni-req-json** | `output/clean/uni/*.md` (bangladesh-entry, english-requirements, scholarships, deposit) |
| 5 | **uni-presetup** | 5-course download/clean, human review, then `--presetup-llm` |

## Human checkpoints

- After URL scrape: spot-check `course_urls.csv` for listing/nav junk.
- After course clean: open `output/clean/pre_setup_course/` — fee, intake, duration must be parseable (see **uni-course-clean** / `stage1-contract.md`).
- After uni_req JSON: four files under `output/clean/uni/`.
- After presetup download: fix `.env` / `course_markdown_cleanup.py` before LLM.

## Feedback loop

If `stage1_parsed.json` has empty `intakeInfo`, `courseDuration`, or `tuitionFee` after presetup LLM, return to **uni-course-clean** (not “run LLM again”).

## Operator phrases

Non-technical wording: [README.md](../../README.md) § Working with the agent. Step-by-step commands: [docs/PIPELINE.md](../../docs/PIPELINE.md), [docs/07-how-to-run.md](../../docs/07-how-to-run.md).
