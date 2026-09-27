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

| Tag pattern | Commit | Meaning |
|-------------|--------|---------|
| `shared/v1.0.0` | `d5f7088` | Original shared pipeline baseline |
| `shared/v1.1.0` | `14cc330` | Audit CSV, degreeName LLM inference, studyLevel export rows |
| `shared/v1.2.0` | `f99ad58` | CDP/device-profile download, UG higherDegree mapping, `package_uni_backup.py` |
| `shared/v1.2.1` | `5c43b8f` | degreeName by study level; validate `degreeName` fill; comma `tuitionFee` |
| `shared/v1.2.2` | `c504489` | **Current reset baseline** — `audit_clean_course_markdown.py`; `test_entry_requirements.py`; course-type filter + scrape/llm tweaks; `git restore --source shared/v1.2.2 -- shared/` |
| `infra/onboarding-skills/v1.0.0` | Cursor agent skills under `.cursor/skills/` + README operator guide |
| `infra/onboarding-skills/v1.0.2` | Skill YAML trigger descriptions, `docs/PIPELINE.md` links, shared baseline in skills |
| `uni/{slug}/v1.0.0` | Full university complete (all study levels) |
| `unit-NN` | Same snapshot as full `uni/{slug}/v1.0.0` |
| `uni/{slug}/foundation/v1.0.0` | Foundation slice only |
| `uni/{slug}/foundation-undergraduate/v1.0.1` | Combined levels; patch bump after a fix |

Study levels: `foundation`, `undergraduate`, `postgraduate`, `postgraduate_research` (aliases: `ug`, `pg`, `pgr`). Commit/tag one level at a time or combine in one step when the university is ready.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full commit + tag workflow.

## Registry

| unit | slug | folder | status | tag | commit |
|------|------|--------|--------|-----|--------|
| unit-01 | aru | Anglia Ruskin University - ARU | complete | study-level (below) | — |
| unit-02 | aston | Aston University | complete | uni/aston/foundation-undergraduate-postgraduate/v1.0.0 | a5fc693 |
| unit-03 | bcu | Birmingham City University | complete | uni/bcu/v1.0.1 | 7d392d8 |
| unit-04 | brunel | Brunel University London | complete | uni/brunel/v1.0.1 | e0cb307 |
| unit-05 | bucks | Buckinghamshire New University | complete | uni/bucks/postgraduate/v1.0.0 | c42bc4f |
| unit-06 | cccu | Canterbury Christ Church University | complete | uni/cccu/v1.0.1 | 6539544 |
| unit-07 | cardiffmet | Cardiff Metropolitan University | complete | uni/cardiffmet/v1.0.0 | d0e04c8 |
| unit-08 | napier | Edinburgh Napier University | complete | uni/napier/v1.0.0 | 9d285f2 |
| unit-09 | keele | Keele University | complete | uni/keele/v1.0.1 | 14cc330 |
| unit-10 | kingston | Kingston University | complete | uni/kingston/v1.0.2 | 6c29518 |
| unit-11 | lsbu | London South Bank University | complete | uni/lsbu/v1.0.1 | c504489 |
| unit-12 | ravensbourne | Ravensbourne University London | in_progress | | |
| unit-13 | teesside | Teesside University | complete | uni/teesside/v1.0.0 | 815df48 |
| unit-14 | birmingham | University of Birmingham | complete | uni/birmingham/v1.0.0 | e552c92 |
| unit-15 | derby | University of Derby | complete | uni/derby/v1.0.1 | e116bc6 |
| unit-16 | uel | University of East London | complete | uni/uel/v1.0.1 | ce2a987 |
| unit-17 | essex | University of Essex | complete | uni/essex/v1.0.0 | cc8bdc0 |
| unit-18 | greenwich | University of Greenwich | complete | uni/greenwich/v1.0.0 | d8c9b13 |
| unit-19 | huddersfield | University of Huddersfield | complete | uni/huddersfield/v1.0.1 | 37cd532 |
| unit-20 | hull | University of Hull | complete | uni/hull/v1.0.0 | bfe851c |
| unit-21 | law | University of Law | complete | uni/law/v1.0.1 | 0c18666 |
| unit-22 | roehampton | University of Roehampton | in_progress | | |
| unit-23 | salford | University of Salford | complete | uni/salford/v1.0.0 | e0280de |
| unit-24 | usw | University of South Wales | complete | uni/usw/v1.0.0 | 8f05398 |
| unit-25 | suffolk | University of Suffolk | complete | uni/suffolk/v1.0.0 | 9d9064f |
| unit-26 | surrey | University of Surrey | in_progress | | |
| unit-27 | uwtsd | University of Wales Trinity Saint David | in_progress | | |
| unit-28 | uwl | University of West London | complete | uni/uwl/v1.0.0 | 54722da |
| unit-29 | winchester | University of Winchester | in_progress | | |
| unit-30 | mmu | Manchester Metropolitan University | complete | uni/mmu/v1.0.1 | ed44603 |
| unit-31 | beds | University of Bedfordshire | complete | uni/beds/v1.0.0 | 0af7047 |
| unit-32 | uea | University of East Anglia | complete | uni/uea/v1.0.0 | b1d17ba |
| unit-33 | herts | University of Hertfordshire | complete | uni/herts/v1.0.0 | 6b012aa |

### Study-level releases (aru, aston)

**aru (unit-01)** — separate `feat` commit and tag per study level (no `uni/aru/v*` full-university tag):

| study level | tag | commit |
|-------------|-----|--------|
| foundation | `uni/aru/foundation/v1.0.0` | `c95dc77` |
| undergraduate | `uni/aru/undergraduate/v1.0.1` | `9ac0f0b` |
| postgraduate | `uni/aru/postgraduate/v1.0.1` | `c40fb62` |

**aston (unit-02)** — one combined `feat` for foundation, undergraduate, and postgraduate:

| study levels | tag | commit |
|--------------|-----|--------|
| foundation + undergraduate + postgraduate | `uni/aston/foundation-undergraduate-postgraduate/v1.0.0` | `a5fc693` |

**Status:** `complete` means `output/dev_courses_*.csv` exists (or, for **bucks**, postgraduate-only export — BD scope accepts PG only). **aru** and **aston** are `complete` via study-level tags above, not a single `uni/{slug}/v*` row. `in_progress` means the university folder has `code/` but the full pipeline export is not done. `not_started` is unused while every listed uni has `code/ENV.MD`.

Fill **tag** / **commit** when you run [`scripts/tag-uni.ps1`](scripts/tag-uni.ps1) after a verified commit. For study-level work, use level-specific tags (`uni/aru/foundation/v1.0.0`) instead of `unit-NN` until the full university is done. Do not mix two universities in one commit.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the commit message format.
