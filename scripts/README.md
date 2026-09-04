# Scripts

PowerShell helpers for **git command lines**, **version tags**, and **checkout by tag**.

Run from the repo root:

```powershell
cd "E:\Project Next\UK UNIVERSITIES\UNI\Uni_Data_Prod"
```

University names and scopes come from [UNIVERSITIES_REGISTRY.md](../UNIVERSITIES_REGISTRY.md). Full workflow: [CONTRIBUTING.md](../CONTRIBUTING.md).

---

## Pick a university

`-Pick` accepts any of these for the same uni:

| Form | Example (ARU) |
|------|----------------|
| Unit | `unit-01` |
| Slug | `aru` |
| Scope | `unit-01/aru` |
| Folder name | `Anglia Ruskin University - ARU` |

List all entries:

```powershell
. .\scripts\Get-UniRegistry.ps1
Get-UniRegistry | Format-Table Unit, Slug, Folder, Status
```

---

## Scripts

| Script | Purpose |
|--------|---------|
| `Get-UniRegistry.ps1` | Load unit/slug/folder from the registry (dot-sourced by other scripts) |
| `commit-uni.ps1` | **Print** `git add` + `git commit` commands (does not run git) |
| `tag-uni.ps1` | Tag the current commit with a version (`v1.0.0`, `v1.0.1`, …) |
| `checkout-uni.ps1` | Sparse-checkout one university at a tag |
| `tag-unit-complete.ps1` | Legacy wrapper → `tag-uni.ps1` (full university only) |

---

## 1. Commit commands (`commit-uni.ps1`)

Pass the university (or `infra` for scripts/docs). **Omit `-Paths`** to auto-read unstaged files from `git status`.

For university commits, the script reads **git tags + git log** for that scope and study level, picks the next version (`v1.0.0` first feat, then `v1.0.1` for fixes), and adds it to the commit message.

**Versions go in commit messages and tags** (same version for both).

### Examples

```powershell
# Auto-detect unstaged files under the university folder
.\scripts\commit-uni.ps1 -Pick aru -Type feat -StudyLevel foundation

# Auto-detect repo infra (scripts/, CONTRIBUTING.md, UNIVERSITIES_REGISTRY.md, …)
.\scripts\commit-uni.ps1 -Pick infra -Type chore -Summary "add commit and tag helper scripts"

# Manual paths (optional)
.\scripts\commit-uni.ps1 -Pick aru -Type feat -StudyLevel foundation -Paths "code/.env,readme.md"

# Fix with auto-detected files
.\scripts\commit-uni.ps1 -Pick bcu -Type fix -Summary "correct foundation URL patterns"

# Include shared/ in git status scan
.\scripts\commit-uni.ps1 -Pick aston -Type fix -Summary "foundation URL patterns" -IncludeShared
```

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

| Situation | Next version |
|-----------|--------------|
| First `feat` for this uni + study level | `v1.0.0` |
| `fix` / `wip` after `v1.0.0` | `v1.0.1`, `v1.0.2`, … |
| Sources checked | `uni/{slug}/.../v*` tags + `git log --grep=unit-NN/slug` |

### Pick values

| `-Pick` | Files from `git status` |
|---------|-------------------------|
| `aru`, `unit-01`, folder name | Under that university folder only |
| `infra` / `repo` / `chore` / `docs` | Everything **except** university folders (scripts/, root `.md`, etc.) |

### Generated messages

| Command | Message |
|---------|---------|
| `-Type feat` (all levels) | `feat(unit-02/aston): complete pipeline and export dev_courses CSV` |
| `-StudyLevel foundation` | `feat(unit-01/aru): complete foundation pipeline` |
| `-StudyLevel foundation,undergraduate` | `feat(unit-01/aru): complete foundation and undergraduate pipeline` |
| `-Type fix -Summary "..."` | `fix(unit-01/aru): ...` |

Study level aliases: `ug` → undergraduate, `pg` → postgraduate, `pgr` → postgraduate_research.

### File paths

| You pass | Resolved as |
|----------|-------------|
| `code/.env` | `{University}/code/.env` |
| `Anglia Ruskin University - ARU/code/.env` | as-is from repo root |
| `shared/foo.py` | `shared/foo.py` (needs `-IncludeShared`) |

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

| Scope | Tag |
|-------|-----|
| All levels | `uni/aston/v1.0.0` + `unit-02` |
| Foundation only | `uni/aru/foundation/v1.0.0` |
| Foundation + UG | `uni/aru/foundation-undergraduate/v1.0.1` |

---

## 3. Checkout (`checkout-uni.ps1`)

```powershell
# Latest tag for that university (registry tag, or newest uni/{slug}/...)
.\scripts\checkout-uni.ps1 -Pick aru
.\scripts\checkout-uni.ps1 -Pick unit-02

# Study level or version (optional)
.\scripts\checkout-uni.ps1 -Pick aru -StudyLevel foundation
.\scripts\checkout-uni.ps1 -Pick aston -Version 1.0.0

# List tags
.\scripts\checkout-uni.ps1 -Pick aru -ListTags

# Explicit tag override
.\scripts\checkout-uni.ps1 -Pick aston -Tag "uni/aston/v1.0.0"
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
