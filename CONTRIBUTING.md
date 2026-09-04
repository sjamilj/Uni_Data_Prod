# Contributing

## One university per commit

Never mix two university folders in the same commit. Shared pipeline changes (`shared/`) ride along with the university that needed them.

## Commit message format

Use Conventional Commits with a **unit scope** from [UNIVERSITIES_REGISTRY.md](UNIVERSITIES_REGISTRY.md):

```
type(unit-NN/slug): short summary
```

**Versions go in commit messages and tags.** `commit-uni.ps1` reads git tags + git log for that scope/study level and picks the next version (`v1.0.0` first feat, then `v1.0.1` for fixes). See [Study-level commits and tags](#study-level-commits-and-tags).

Examples:

```
wip(unit-03/bcu): tweak COURSE_CLEAN_BLOCKS for foundation pages

feat(unit-03/bcu): complete pipeline and export dev_courses CSV

feat(unit-02/aston): complete foundation pipeline

feat(unit-01/aru): complete foundation and undergraduate pipeline

fix(unit-02/aston): clear unavailable international fees
```

| Type | When |
|------|------|
| `wip` | In-progress work on a `dev_*` branch (cleanup rules, Presetup, partial Execute) |
| `feat` | University newly completed (`output/dev_courses_*.csv` exists) or a study-level slice is done |
| `fix` | Correction after that university or study level was already tagged |
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

## Study-level commits and tags

Universities can be completed **all at once** or **one study level at a time** (foundation, undergraduate, postgraduate, PGR). Use the helper scripts so the university name, scope, and message stay consistent.

### 1. Commit commands (version from git history)

Pass the university and optionally file paths. **Omit `-Paths`** to auto-read unstaged files from `git status`. The script prints `git add` + `git commit` lines — it does not run git.

```powershell
# Auto-detect unstaged files under the university folder
.\scripts\commit-uni.ps1 -Pick aru -Type feat -StudyLevel foundation

# Repo infra (scripts/, CONTRIBUTING.md, …) — use for non-university commits
.\scripts\commit-uni.ps1 -Pick infra -Type chore -Summary "add commit and tag helper scripts"

# Manual paths (optional)
.\scripts\commit-uni.ps1 -Pick bcu -Type fix -Summary "correct foundation study level split" -Paths code/.env
```

Copy and run the printed commands. See [scripts/README.md](scripts/README.md).

### 2. Tag (same version as commit)

Tag **after** you verify the export for that scope. First completion is `v1.0.0`; later fixes are `v1.0.1`, `v1.0.2`, …

```powershell
# Full university — creates uni/aston/v1.0.0 and unit-02
.\scripts\tag-uni.ps1 -Pick aston

# One study level
.\scripts\tag-uni.ps1 -Pick unit-01 -StudyLevel foundation

# Several levels, one tag
.\scripts\tag-uni.ps1 -Pick aru -StudyLevel foundation,undergraduate,postgraduate

# Next patch after a fix commit
.\scripts\tag-uni.ps1 -Pick aston -StudyLevel foundation -BumpPatch

# Explicit version
.\scripts\tag-uni.ps1 -Pick bcu -Version 1.0.1
```

| Scope | Tag examples |
|-------|----------------|
| All levels | `uni/aston/v1.0.0`, `unit-02` |
| Foundation only | `uni/aru/foundation/v1.0.0` |
| Foundation + UG | `uni/aru/foundation-undergraduate/v1.0.1` |

List tags: `.\scripts\tag-uni.ps1 -Pick aston -ListTags`

Update the registry row (tag + commit SHA) in the same or a follow-up `docs` commit.

### 3. Go back to a tagged snapshot

```powershell
.\scripts\checkout-uni.ps1 -Pick aston
.\scripts\checkout-uni.ps1 -Pick aru -StudyLevel foundation
.\scripts\checkout-uni.ps1 -Pick unit-02 -Version 1.0.0
```

### Typical flow (study-level retrofit)

For universities completed before study-level splits, re-run Execute per level, then commit + tag each slice (or combine levels in one commit when the uni allows):

```powershell
# 1. Pipeline work for foundation only …
.\scripts\commit-uni.ps1 -Pick unit-01 -Type feat -StudyLevel foundation -Paths "code/.env,readme.md"
# copy/paste the printed git add + git commit lines
.\scripts\tag-uni.ps1 -Pick unit-01 -StudyLevel foundation

# 2. Later fix
.\scripts\commit-uni.ps1 -Pick unit-01 -Type fix -Summary "reclassify shared /study/ paths" -Paths code/.env
.\scripts\tag-uni.ps1 -Pick unit-01 -StudyLevel foundation -BumpPatch   # → v1.0.1

# 3. Next level
.\scripts\commit-uni.ps1 -Pick unit-01 -Type feat -StudyLevel undergraduate -Paths readme.md
.\scripts\tag-uni.ps1 -Pick unit-01 -StudyLevel undergraduate
```

Legacy wrapper (full uni only): `.\scripts\tag-unit-complete.ps1 -University "Aston University" -Unit unit-02 -Slug aston`

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
