---
name: new-uni-setup
description: Resets shared pipeline code to shared/v1.1.0, picks variant CSV and STRATEGY for a new university folder. Use only when the user explicitly says new-uni-setup or asks to start a brand-new university onboarding from scratch.
disable-model-invocation: true
---

# New university setup

## Git

Follow [git-for-operator.md](../git-for-operator.md). Do not run git in the terminal. Give separate command blocks with recommended commit/tag `-m` text for each git step.

- Shared reset baseline: [CONTRIBUTING.md](../../CONTRIBUTING.md#shared-infrastructure-baseline) (`shared/v1.1.0`).
- University scope for later commits: look up `unit-NN` / slug in [UNIVERSITIES_REGISTRY.md](../../UNIVERSITIES_REGISTRY.md).
- Optional helpers: [scripts/README.md](../../scripts/README.md) (`checkout-uni.cmd`, `commit-uni.cmd` with `-Pick infra` only for repo-wide docs/skills).

## Before anything destructive

Ask the user to run `git status` (or they paste output). List every modified path under `shared/` that would be lost on reset. Do not tell them to run `git checkout shared/v1.1.0 -- shared/` until they confirm.

Per-university behaviour belongs in `{University}/code/.env`, `code/ENV.MD`, and `code/course_markdown_cleanup.py` — never in `shared/`.

## Reset shared pipeline

Give the user (one command block; they run it):

```powershell
cd "E:\Project Next\UK UNIVERSITIES\UNI\Uni_Data_Prod"
git checkout shared/v1.1.0 -- shared/
```

## Pick the university

- Folder name matches `UNIVERSITY_NAME` in `code/ENV.MD` / `code/.env`.
- Operator may point at a variant CSV at university root: `ALL_COURSE.csv`, `Paginated.csv`, `DegreeScopedALLCourse.csv`, or `DegreeScopedPaginated.csv` (templates in `_university_template/`).

## Variant CSV → STRATEGY

| Variant CSV | `STRATEGY` | Listing env keys |
|-------------|------------|------------------|
| `ALL_COURSE.csv` | `ALL_COURSE` | `COURSE_CATALOGUE_URL`, `COURSE_CATALOGUE_HTML` |
| `Paginated.csv` | `DEGREE_SCOPED_PAGINATED` | `COURSE_LISTING_PAGE_1`, `COURSE_LISTING_PAGE_2` (or degree-scoped `*_COURSE_LISTING_PAGE_*`) |
| `DegreeScopedALLCourse.csv` | `ALL_COURSE` | `{SCOPE}_COURSE_CATALOGUE_URL`, `{SCOPE}_COURSE_CATALOGUE_HTML` |
| `DegreeScopedPaginated.csv` | `DEGREE_SCOPED_PAGINATED` | `{SCOPE}_COURSE_LISTING_PAGE_1`, `{SCOPE}_COURSE_LISTING_PAGE_2` |

Scopes: `FOUNDATION`, `UNDERGRADUATE`, `POSTGRADUATE`, `POSTGRADUATE_RESEARCH`.

Reference: [_university_template/README.md](../../_university_template/README.md).

Example: Cardiff Metropolitan University uses `Paginated.csv` and `STRATEGY=DEGREE_SCOPED_PAGINATED` in `Cardiff Metropolitan University/code/ENV.MD`.

## `.env` vs `ENV.MD`

- `code/.env` is gitignored (secrets and local overrides).
- `code/ENV.MD` is committed — mirror the same config keys there whenever you edit scrape/clean settings.

Optional: `python shared/build_university_from_template.py --university "{University Name}"` from `Template.csv`.

## Next phases

After setup, continue with **uni-course-urls** (course link scrape), **uni-course-clean** (course page markdown), **uni-req-json** (uni-wide entry/English/scholarship/deposit), then **uni-presetup**. Full order: invoke **uni-pipeline**.
