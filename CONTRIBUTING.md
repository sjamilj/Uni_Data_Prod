# Contributing

## One university per commit

Never mix two university folders in the same commit. Shared pipeline changes (`shared/`) ride along with the university that needed them.

## Commit message format

Use Conventional Commits with a **unit scope** from [UNIVERSITIES_REGISTRY.md](UNIVERSITIES_REGISTRY.md):

```
type(unit-NN/slug): short summary
```

Examples:

```
wip(unit-03/bcu): tweak COURSE_CLEAN_BLOCKS for foundation pages

feat(unit-03/bcu): complete pipeline and export dev_courses CSV

fix(unit-02/aston): clear unavailable international fees
```

| Type | When |
|------|------|
| `wip` | In-progress work on a `dev_*` branch (cleanup rules, Presetup, partial Execute) |
| `feat` | University newly completed (`output/dev_courses_*.csv` exists) |
| `fix` | Correction after that university was already marked complete |
| `docs` | Registry, RUN.md, PIPELINE.md, `docs/` learning guides |
| `chore` | Shared infra that is not tied to one uni |

**Scope** is always `unit-NN/slug` (zero-padded). Search later with:

```powershell
git log --oneline --all --grep="unit-03"
git log --oneline -- "Birmingham City University/code"
```

## Branching

| Branch | Role |
|--------|------|
| `main` | Merged university completions + shared infra |
| `dev_sj` (or `dev/{initials}`) | Active WIP |

Squash or reword `wip(...)` commits to `feat(unit-NN/slug): ...` before merging to `main`.

## Tagging a completed university

Only after `output/dev_courses_*.csv` exists:

```powershell
.\scripts\tag-unit-complete.ps1 -University "Aston University" -Unit unit-02 -Slug aston
```

Creates annotated tags `unit-02` and `uni/aston/v1.0.0`. Update the registry row (tag + commit SHA) in the same or a follow-up `docs` commit.

## Check out one university later

```powershell
.\scripts\checkout-uni.ps1 -University "Aston University" -Tag "uni/aston/v1.0.0"
```

## Documentation (`docs/`)

Learning docs for `shared/` and `dashboard/` live under [docs/](docs/). Start at [docs/00-start-here.md](docs/00-start-here.md).

When you change a **Tier 3** module (listed in [docs/shared/README.md](docs/shared/README.md)), update the matching `docs/shared/<module>.md` in the same commit or a follow-up `docs` commit:

- New public class or CLI flag → add to the doc’s “Main classes” / “Key methods”
- Changed artifact paths → update “Artifacts” and [docs/04-data-flow.md](docs/04-data-flow.md) if global
- New pipeline phase or dashboard button → update the relevant `docs/features/*.md`

Use [docs/templates/code-file-template.md](docs/templates/code-file-template.md) for new module docs. Tier 4 utilities only need a one-line row in `docs/shared/README.md`.

Operational runbooks ([PIPELINE.md](PIPELINE.md), [dashboard.md](dashboard.md)) stay separate; `/docs` explains **why**, not step-by-step commands.

---

## New university setup

Use the template generator (Phase 1 — env + variant CSV only; HTML is still manual browser-save):

```powershell
# 1. Fill Template.csv (or copy _university_template and edit in place)
# 2. Bootstrap folder + generate code/.env and variant CSV
python shared\build_university_from_template.py --university "New University - NU" --bootstrap

# 3. Save uni_req/, course_listing/, course_detail/ HTML in the browser
# 4. Tune COURSE_PATH_PATTERNS and COURSE_CLEAN_BLOCKS in code/.env
# 5. Optional: merge code/env/*.env fragments
python shared\build_env.py --code-dir "New University - NU\code"
```

Pick the variant in `Template.csv` row 1 (`ALL_COURSE.csv`, `Paginated.csv`, `DegreeScopedALLCourse.csv`, or `DegreeScopedPaginated.csv`). See [_university_template/README.md](_university_template/README.md) and [docs/05-env-and-config.md](docs/05-env-and-config.md).

**Commit scope:** when the first pipeline run for that uni lands, use its `unit-NN/slug` from [UNIVERSITIES_REGISTRY.md](UNIVERSITIES_REGISTRY.md). Shared generator changes (`shared/build_university_from_template.py`, `_university_template/`) belong in `chore(shared): ...`, not mixed with another university’s folder.

---

## Review handoff (`REVIEW/`)

After `output/dev_courses_{University}_reviewed.csv` exists (from `validate_dev_courses.py` or manual review):

```powershell
python shared\package_review_output.py "Anglia Ruskin University - ARU"
# or:
package_review.bat "Anglia Ruskin University - ARU"
```

Creates (gitignored):

```
REVIEW/
  {University Name}/
    {Variant}.csv                    # root variant CSV, e.g. DegreeScopedPaginated.csv
    dev_courses_{University}_reviewed.csv
```

Use `--force` to overwrite an existing handoff folder. `REVIEW/` is local output only — regenerate anytime; do not commit it.

**Commit scope:** reviewed CSV under `{University}/output/` follows that university’s unit scope (`feat` / `wip` / `fix`). The `package_review_output.py` script itself is `chore(shared): ...`.

---

## Splitting a large working tree

When many files are dirty, stage **one university folder at a time** plus only the shared files that commit needs:

| Commit type | Stage |
|-------------|--------|
| `chore(shared): ...` | `shared/`, `_university_template/`, `package_review.bat`, `.gitignore` — **no** `{University}/` paths |
| `docs: ...` | `docs/`, `README.md`, `CONTRIBUTING.md`, `scrape_course_urls_CMD.md`, `shared/README.md` |
| `wip(unit-NN/slug): ...` | Only that university’s folder |

Restore accidental deletions before committing a `complete` university:

```powershell
git restore "{University}/output/dev_courses_*.csv"
```
