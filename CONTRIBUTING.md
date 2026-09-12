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

## Shared infrastructure baseline

`shared/` is used by all ~34 universities. Treat it like a **library**: one stable baseline on `main`, then uni-specific work on a branch.

| What | Value |
|------|-------|
| Tag | `shared/v1.0.0` |
| Commit | `d5f7088` |
| Message | `(chore) Shared infra in general` |

### Start work on a new university

```powershell
git fetch origin
git switch main
git pull

# optional: branch per uni
git switch -c dev/kingston

# only touch that university folder (+ shared/ when the pipeline needs it)
# Presetup → review HTML/MD → tune code/.env and code/course_markdown_cleanup.py
```

### Reset `shared/` to the baseline

Use this when finishing one uni and starting another, or when local `shared/` edits should not carry over:

```powershell
git restore --source shared/v1.0.0 -- shared
# or detached pin:
git checkout shared/v1.0.0 -- shared
```

Stay on your branch; only `shared/` is replaced. University folders are unchanged.

### Commit rules for `shared/`

| Situation | How |
|-----------|-----|
| Shared change needed **for one uni** (presetup, cleanup, extract) | `.\scripts\commit-uni.ps1 -Pick keele -Type wip -IncludeShared` |
| Shared change is **general** (fixes all unis) | `.\scripts\commit-uni.ps1 -Pick infra -Type chore -Summary "..."` then tag `shared/v1.0.1` |
| Never | Two university folders in one commit |

After a general shared commit, bump the tag:

```powershell
git tag -a shared/v1.0.1 -m "shared: describe what changed"
```

List baselines: `git tag -l "shared/*"`

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
.\scripts\checkout-uni.cmd -Pick aston
.\scripts\checkout-uni.cmd -Pick aru -StudyLevel foundation
.\scripts\checkout-uni.cmd -Pick unit-02 -Version 1.0.0
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

### Shared version tags (`shared/v*`)

University tags (`uni/…`) mark a **university export** snapshot. **Shared** changes get their own tag when `shared/` gains new behaviour (audit CSV, export rules, inference helpers, etc.) — usually after a `chore(shared): …` commit or a university commit that included `-IncludeShared`.

| Tag | When |
|-----|------|
| `shared/v1.0.0` | Pipeline baseline |
| `shared/v1.1.0` | Audit CSV export, degreeName LLM inference, `studyLevel` column, foundation/UG as separate export rows |

```powershell
# List shared tags
git tag -l "shared/*"

# Tag current HEAD after shared work is committed (bump minor for new tools, patch for fixes)
git tag -a shared/v1.1.0 -m "shared: audit CSV, degreeName inference, studyLevel export"

# Push when ready
git push origin shared/v1.1.0

# Check out shared code at a tag
git checkout shared/v1.1.0 -- shared/
```

Bump **minor** (`v1.1.0` → `v1.2.0`) for new shared modules or export behaviour; bump **patch** (`v1.1.0` → `v1.1.1`) for fixes only. Tag **after** tests pass and at least one university has been re-exported with the new shared code.

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

After `output/dev_courses_{University}_reviewed.csv` exists (from export / `validate_dev_courses.py`):

- **Automatic:** `export_dev_courses.py` (pipeline Phase 5) also writes `output/missing_field_report.txt`.
- **Audit CSV:** flatten extracted audit JSON beside reviewed CSV rows to debug why a field is empty (`minGpa`, `degreeName`, `ieltsMinOverall`, etc.):

```powershell
python shared\export_extracted_audit_csv.py `
  --university "Keele University" `
  --missing-field minGpa `
  --json entry_requirement_parsed.json `
  --json stage1_parsed.json `
  --json english_requirements_parsed.json `
  --output "Keele University\output\extracted_audit_minGpa.csv" `
  --force
```

Missing `degreeName` — infer from clean course markdown with LLM, then patch extracted JSON:

```powershell
python shared\export_extracted_audit_csv.py `
  --university "Keele University" `
  --missing-field degreeName `
  --json stage1_parsed.json `
  --include-markdown `
  --infer-degree `
  --apply-degree `
  --output "Keele University\output\extracted_audit_degreeName.csv" `
  --force

python shared\export_dev_courses.py --code-dir "Keele University/code"
python shared\missing_field_stats.py "Keele University" --force
```

- **Review handoff:** copy variant CSV + reviewed CSV + report into `REVIEW/`:

```powershell
python shared\package_review_output.py "Anglia Ruskin University - ARU"
# or:
package_review.bat "Anglia Ruskin University - ARU"
# PowerShell: .\package_review.bat "Anglia Ruskin University - ARU"
```

Creates (gitignored):

```
REVIEW/
  {University Name}/
    {Variant}.csv                    # root variant CSV, e.g. DegreeScopedPaginated.csv
    dev_courses_{University}_reviewed.csv
    missing_field_report.txt
    clean/uni/*.md                   # cleaned requirement markdown
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
