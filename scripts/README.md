# Scripts

PowerShell helpers for **git command lines**, **version tags**, and **checkout by tag**.

Run from the repo root:

```powershell
cd "D:\DATA SCOL\UK_Uni_Data"
```

## Portable PC / restricted PowerShell

On laptops or work PCs where `running scripts is disabled`, **do not use `.ps1` directly**. Use the **`.cmd`** wrappers — no admin rights or `Set-ExecutionPolicy` needed:

```powershell
.\scripts\checkout-uni.cmd -Pick bcu
.\scripts\commit-uni.cmd -Pick aru -Type feat -StudyLevel foundation
.\scripts\tag-uni.cmd -Pick aru -StudyLevel foundation
```

| Wrapper | Runs |
|---------|------|
| `checkout-uni.cmd` | sparse-checkout one university at a tag |
| `commit-uni.cmd` | print `git add` + `git commit` lines |
| `tag-uni.cmd` | create version tags |
| `tag-unit-complete.cmd` | legacy full-uni tag helper |

**Your machine:** `.\scripts\checkout-uni.ps1` will fail. Use `.\scripts\checkout-uni.cmd` instead.

Optional (home PC only): `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` then `.ps1` works too.

University names and scopes come from [UNIVERSITIES_REGISTRY.md](../UNIVERSITIES_REGISTRY.md). Full workflow: [CONTRIBUTING.md](../CONTRIBUTING.md).

---

## Pick a university

`-Pick` accepts any of these for the same uni:


| Form        | Example (ARU)                    |
| ----------- | -------------------------------- |
| Unit        | `unit-01`                        |
| Slug        | `aru`                            |
| Scope       | `unit-01/aru`                    |
| Folder name | `Anglia Ruskin University - ARU` |


List all entries:

```powershell
. .\scripts\Get-UniRegistry.ps1
Get-UniRegistry | Format-Table Unit, Slug, Folder, Status
```

---

## Scripts


| Script                  | Purpose                                                                |
| ----------------------- | ---------------------------------------------------------------------- |
| `Get-UniRegistry.ps1`   | Load unit/slug/folder from the registry (dot-sourced by other scripts) |
| `commit-uni.ps1` / `.cmd` | **Print** `git add` + `git commit` commands (does not run git)     |
| `tag-uni.ps1` / `.cmd`  | Tag the current commit with a version (`v1.0.0`, `v1.0.1`, …)          |
| `checkout-uni.ps1` / `.cmd` | Sparse-checkout one university at a tag                            |
| `tag-unit-complete.ps1` / `.cmd` | Legacy wrapper → `tag-uni.ps1` (full university only)           |


---

## 1. Commit commands (`commit-uni.ps1`)

Pass the university (or `infra` for scripts/docs). **Omit `-Paths`** to auto-read unstaged files from `git status`.

For university commits, the script reads **git tags + git log** for that scope and study level, picks the next version (`v1.0.0` first feat, then `v1.0.1` for fixes), and adds it to the commit message.

**Versions go in commit messages and tags** (same version for both).

### Examples

```powershell
# Auto-detect unstaged files under the university folder only
.\scripts\commit-uni.ps1 -Pick aru -Type feat -StudyLevel foundation

# University folder + shared/ together (ENV.MD + shared/*.py)
.\scripts\commit-uni.ps1 -Pick aru -Type feat -StudyLevel postgraduate -IncludeShared
# same flag, shorter alias:
.\scripts\commit-uni.ps1 -Pick aru -Type feat -StudyLevel postgraduate -WithShared

# Auto-detect repo infra (scripts/, CONTRIBUTING.md, UNIVERSITIES_REGISTRY.md, …)
.\scripts\commit-uni.ps1 -Pick infra -Type chore -Summary "add commit and tag helper scripts"

.\scripts\commit-uni.cmd -Pick infra -Type chore -Summary "add commit and tag helper scripts"
# Manual paths (optional)
.\scripts\commit-uni.ps1 -Pick aru -Type feat -StudyLevel foundation -Paths "code/.env,readme.md"

# Fix with auto-detected files
.\scripts\commit-uni.ps1 -Pick bcu -Type fix -Summary "correct foundation URL patterns"
```



If you omit `-IncludeShared` but `shared/` has changes, the script prints a hint listing those files and the command to include them.

### Output (copy and run)

```powershell
# Anglia Ruskin University - ARU
# scope: unit-01/aru | type: feat | levels: foundation
# files from git status:
#   Anglia Ruskin University - ARU/code/.env
#   Anglia Ruskin University - ARU/readme.md

git add -- "Anglia Ruskin University - ARU/code/.env" "Anglia Ruskin University - ARU/readme.md"
git commit -m "feat(unit-01/aru): complete foundation pipeline v1.0.0"

# then tag (same version):
.\scripts\tag-uni.ps1 -Pick aru -StudyLevel foundation -Version 1.0.0
```

### Version rules (from git history)


| Situation                               | Next version                                             |
| --------------------------------------- | -------------------------------------------------------- |
| First `feat` for this uni + study level | `v1.0.0`                                                 |
| `fix` / `wip` after `v1.0.0`            | `v1.0.1`, `v1.0.2`, …                                    |
| Sources checked                         | `uni/{slug}/.../v*` tags + `git log --grep=unit-NN/slug` |


### Pick values


| `-Pick`                                 | Files from `git status`                                               |
| --------------------------------------- | --------------------------------------------------------------------- |
| `aru`, `unit-01`, folder name           | Under that university folder only                                     |
| same + `-IncludeShared` / `-WithShared` | University folder **and** `shared/`                                   |
| `infra` / `repo` / `chore` / `docs`     | Everything **except** university folders (scripts/, root `.md`, etc.) |


### Generated messages


| Command                                | Message                                                             |
| -------------------------------------- | ------------------------------------------------------------------- |
| `-Type feat` (all levels)              | `feat(unit-02/aston): complete pipeline and export dev_courses CSV` |
| `-StudyLevel foundation`               | `feat(unit-01/aru): complete foundation pipeline`                   |
| `-StudyLevel foundation,undergraduate` | `feat(unit-01/aru): complete foundation and undergraduate pipeline` |
| `-Type fix -Summary "..."`             | `fix(unit-01/aru): ...`                                             |


Study level aliases: `ug` → undergraduate, `pg` → postgraduate, `pgr` → postgraduate_research.

### File paths


| You pass                                   | Resolved as                              |
| ------------------------------------------ | ---------------------------------------- |
| `code/.env`                                | `{University}/code/.env`                 |
| `Anglia Ruskin University - ARU/code/.env` | as-is from repo root                     |
| `shared/foo.py`                            | `shared/foo.py` (needs `-IncludeShared`) |


`output/` is gitignored — do not pass output files.

---

## 2. Tag (`tag-uni.ps1`)

Tag **after** you run the commit commands and verify the work.

```powershell
.\scripts\tag-uni.ps1 -Pick aston
.\scripts\tag-uni.ps1 -Pick aru -StudyLevel foundation
.\scripts\tag-uni.ps1 -Pick aru -StudyLevel foundation -BumpPatch
.\scripts\tag-uni.ps1 -Pick aston -ListTags
```

### Tag naming


| Scope           | Tag                                       |
| --------------- | ----------------------------------------- |
| All levels      | `uni/aston/v1.0.0` + `unit-02`            |
| Foundation only | `uni/aru/foundation/v1.0.0`               |
| Foundation + UG | `uni/aru/foundation-undergraduate/v1.0.1` |


---

## 3. Checkout (`checkout-uni.cmd`)

Resolves a **tag** first, then falls back to the latest matching **commit** from git history (`feat(unit-NN/slug): ... v1.0.0`).

```powershell
# Latest tag, or latest matching commit in git history
.\scripts\checkout-uni.cmd -Pick bcu
.\scripts\checkout-uni.cmd -Pick aston

# Study level or version (matches tag or commit message)
.\scripts\checkout-uni.cmd -Pick aru -StudyLevel foundation
.\scripts\checkout-uni.cmd -Pick bcu -Version 1.0.0

# List tags + history commits
.\scripts\checkout-uni.cmd -Pick bcu -ListTags

# Explicit override
.\scripts\checkout-uni.cmd -Pick aston -Tag "uni/aston/v1.0.0"
.\scripts\checkout-uni.cmd -Pick bcu -Commit abc1234

# Preview only (no git changes)
.\scripts\checkout-uni.cmd -Pick bcu -Commit af92caa -DryRun
```

---

## Typical flow

```powershell
# 1. See unstaged files
git status -- "Anglia Ruskin University - ARU"

# 2. Get add + commit commands (auto from git status)
.\scripts\commit-uni.ps1 -Pick aru -Type feat -StudyLevel foundation

# 3. Copy/paste the printed git add and git commit lines

# 4. Tag
.\scripts\tag-uni.ps1 -Pick aru -StudyLevel foundation
```

## Restore foundation config from an old commit (safe)

**Do not** `git checkout <old-commit> -- shared/*.py` — that replaces the whole file with an old version and breaks the dashboard.

The foundation fixes from `8866faf` are already in current `shared/` on `HEAD`. Only restore **university config**:

```powershell
# ARU foundation URL patterns + markdown cleanup (ENV.MD only)
git show 8866faf:"Anglia Ruskin University - ARU/code/ENV.MD" > "$env:TEMP\aru-env.md"
# Manually merge FOUNDATION_URL_PATTERNS and COURSE_MARKDOWN_REMOVE_SECTIONS into code/ENV.MD
# Keep newer lines from HEAD too (e.g. Full description :: #summary)

# Regenerate .env after editing ENV.MD
python shared\build_env.py --code-dir "Anglia Ruskin University - ARU\code"
```


| File                       | Safe to restore from old commit?                          |
| -------------------------- | --------------------------------------------------------- |
| `{University}/code/ENV.MD` | Yes (merge manually)                                      |
| `shared/*.py`              | No — use current `HEAD`; old patches are already included |


