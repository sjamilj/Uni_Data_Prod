# Universities registry

Fixed unit numbers (alphabetical by folder). Use these in git scopes: `feat(unit-03/bcu): ...`

**Pick a university in scripts** by unit, slug, or folder name:

```powershell
.\scripts\commit-uni.cmd -Pick aston -Type feat -StudyLevel foundation
.\scripts\tag-uni.cmd -Pick unit-02 -StudyLevel foundation -BumpPatch
.\scripts\tag-uni.cmd -Pick aston -ListTags
.\scripts\checkout-uni.cmd -Pick aru
.\scripts\checkout-uni.cmd -Pick unit-02 -StudyLevel foundation
```

Find later:

```powershell
git log --oneline --all --grep="unit-03"
git log --oneline -- "Birmingham City University/code"
git tag -l "uni/bcu/*"
git tag -l "uni/aru/foundation/*"
```

## Version and tag rules

| What | Where | Example |
|------|-------|---------|
| Commit message | **No version** | `feat(unit-02/aston): complete foundation pipeline` |
| Git tag | **Version here** | `uni/aston/foundation/v1.0.0` |
| Fix after tag | New commit + `-BumpPatch` | `v1.0.0` → `v1.0.1` |

| Tag pattern | Meaning |
|-------------|---------|
| `uni/{slug}/v1.0.0` | Full university complete (all study levels) |
| `unit-NN` | Same snapshot as full `uni/{slug}/v1.0.0` |
| `uni/{slug}/foundation/v1.0.0` | Foundation slice only |
| `uni/{slug}/foundation-undergraduate/v1.0.1` | Combined levels; patch bump after a fix |

Study levels: `foundation`, `undergraduate`, `postgraduate`, `postgraduate_research` (aliases: `ug`, `pg`, `pgr`). Commit/tag one level at a time or combine in one step when the university is ready.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full commit + tag workflow.

## Registry

| unit | slug | folder | status | tag | commit |
|------|------|--------|--------|-----|--------|
| unit-01 | aru | Anglia Ruskin University - ARU | complete | | |
| unit-02 | aston | Aston University | complete | | |
| unit-03 | bcu | Birmingham City University | complete | | |
| unit-04 | brunel | Brunel University London | in_progress | | |
| unit-05 | bucks | Buckinghamshire New University | in_progress | | |
| unit-06 | cccu | Canterbury Christ Church University | in_progress | | |
| unit-07 | cardiffmet | Cardiff Metropolitan University | in_progress | | |
| unit-08 | napier | Edinburgh Napier University | in_progress | | |
| unit-09 | keele | Keele University | in_progress | | |
| unit-10 | kingston | Kingston University | in_progress | | |
| unit-11 | lsbu | London South Bank University | in_progress | | |
| unit-12 | ravensbourne | Ravensbourne University London | in_progress | | |
| unit-13 | teesside | Teesside University | in_progress | | |
| unit-14 | birmingham | University of Birmingham | in_progress | | |
| unit-15 | derby | University of Derby | in_progress | | |
| unit-16 | uel | University of East London | in_progress | | |
| unit-17 | essex | University of Essex | in_progress | | |
| unit-18 | greenwich | University of Greenwich | in_progress | | |
| unit-19 | huddersfield | University of Huddersfield | in_progress | | |
| unit-20 | hull | University of Hull | in_progress | | |
| unit-21 | law | University of Law | in_progress | | |
| unit-22 | roehampton | University of Roehampton | in_progress | | |
| unit-23 | salford | University of Salford | in_progress | | |
| unit-24 | usw | University of South Wales | in_progress | | |
| unit-25 | suffolk | University of Suffolk | in_progress | | |
| unit-26 | surrey | University of Surrey | in_progress | | |
| unit-27 | uwtsd | University of Wales Trinity Saint David | in_progress | | |
| unit-28 | uwl | University of West London | in_progress | | |
| unit-29 | winchester | University of Winchester | in_progress | | |

**Status:** `complete` means `output/dev_courses_*.csv` exists. `in_progress` means the university folder has `code/` but the full pipeline export is not done. `not_started` is unused while every listed uni has `code/ENV.MD`.

Fill **tag** / **commit** when you run [`scripts/tag-uni.ps1`](scripts/tag-uni.ps1) after a verified commit. For study-level work, use level-specific tags (`uni/aru/foundation/v1.0.0`) instead of `unit-NN` until the full university is done. Do not mix two universities in one commit.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the commit message format.
