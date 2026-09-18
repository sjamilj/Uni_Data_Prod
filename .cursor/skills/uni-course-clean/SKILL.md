---
name: uni-course-clean
description: >-
  COURSE_CLEAN_BLOCKS and course_markdown_cleanup so cleaned markdown has intake, duration,
  tuition fee, IELTS for Stage 1. Use for course-details.html, missing fee/duration/intake
  on cleaned pages, empty stage1_parsed intakeInfo or tuitionFee, COURSE_CLEAN_BLOCKS tuning.
---

# Course page clean (Stage 1–ready markdown)

Git: [git-for-operator.md](../git-for-operator.md).

## Goal

Produce `output/clean/pre_setup_course/{level}/*.md` (or `clean/courses/`) whose text matches the parser contract in [stage1-contract.md](stage1-contract.md) so `stage1_parsed.json` gets `intakeInfo`, `courseDuration`, `tuitionFee`, `currency` without relying on the LLM for those fields.

## Inputs

- `{University}/course_detail/course-details.html` (or per-programme samples)
- Template references: `_university_template/code/ENV.MD`, `_university_template/code/course_markdown_cleanup.py`

## Configure `code/.env` and `code/ENV.MD` (same keys)

| Key | Purpose |
|-----|---------|
| `COURSE_PAGE_TITLE_SELECTOR` | `h1` for course title |
| `COURSE_CLEAN_ENGINE` | `generic` (default), `utopian` (ARU), or `plugin` |
| `COURSE_CLEAN_BLOCKS` | `Heading :: css-selector` per block (overview, entry, fees) |
| `COURSE_CLEAN_STRIP_WITHIN` | `script`, `noscript`, `nav`, etc. |
| `COURSE_CLEAN_EXPAND_TABS` | `true` when fees/entry are in tabs |
| `COURSE_MARKDOWN_REMOVE_SECTIONS` | `level :: heading` — see [docs/shared/course_markdown_cleanup.md](../../docs/shared/course_markdown_cleanup.md) |

Syntax for removals: `4 :: *part-time*`, `3 :: UK students`, etc.

## Workflow

1. Inspect HTML: find selectors for overview/key facts, entry requirements, fees (international/overseas).
2. Update `COURSE_CLEAN_BLOCKS` and related keys in `.env` and `ENV.MD`.
3. Run download/clean (presetup or limit):

```powershell
python shared/run_course_pipeline.py --code-dir "{University}/code" --presetup --sample-size 5
```

Or:

```powershell
python shared/download_and_clean_course_pages.py --code-dir "{University}/code" --limit 5
```

4. Open resulting `.md` and check against [stage1-contract.md](stage1-contract.md).
5. If `.env` cannot express a rewrite, edit `{University}/code/course_markdown_cleanup.py` → `cleanup_course_markdown_uni()`. Napier IS1 foundation handling is the reference for conditional HTML/markdown rules.

## Second pass

`EXTRA_CLEAN_REMOVE_SECTIONS` in `.env` plus:

```powershell
python shared/extra_clean_courses.py --code-dir "{University}/code"
```

## Division of labour

| Data | Source |
|------|--------|
| Intake, duration, international fee, course-page IELTS | Course markdown (this skill) |
| Bangladesh/HSC entry grades | `output/clean/uni/bangladesh-entry.md` (**uni-req-json**) |
| English table by programme | `output/clean/uni/english-requirements.md` |
| Deposit | `output/clean/uni/deposit.md` |
| Scholarships | `output/clean/uni/scholarships.md` |

## Next

**uni-req-json** then **uni-presetup**. If LLM presetup shows empty parser-owned fields, return here.
