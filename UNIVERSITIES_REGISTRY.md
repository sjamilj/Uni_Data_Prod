# Universities registry

Fixed unit numbers (alphabetical by folder). Use these in git scopes: `feat(unit-01/slug): ...`

**Pick a university in scripts** by unit, slug, or folder name:

```powershell
.\scripts\commit-uni.cmd -Pick <slug> -Type feat -StudyLevel foundation
.\scripts\tag-uni.cmd -Pick unit-01 -StudyLevel foundation -BumpPatch
.\scripts\tag-uni.cmd -Pick <slug> -ListTags
.\scripts\checkout-uni.cmd -Pick <slug>
.\scripts\checkout-uni.cmd -Pick unit-01 -StudyLevel foundation
```

Find later:

```powershell
git log --oneline --all --grep="unit-01"
git log --oneline -- "<University Folder>/code"
git tag -l "uni/<slug>/*"
git tag -l "uni/<slug>/foundation/*"
```

## Version and tag rules

| What | Where | Example |
|------|-------|---------|
| Commit message | **No version** | `feat(unit-01/example): complete foundation pipeline` |
| Git tag | **Version here** | `uni/example/foundation/v1.0.0` |
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

Add the first row when you scaffold a university from `_university_template/` (alphabetical order by folder name). Example: `unit-01 | example-uni | Example University | not_started | | |`.

**Status:** `complete` means `output/dev_courses_*.csv` exists for the intended study levels. `in_progress` means the university folder has `code/` but the full pipeline export is not done. `not_started` means the folder exists but pipeline work has not begun.

Fill **tag** / **commit** when you run [`scripts/tag-uni.ps1`](scripts/tag-uni.ps1) after a verified commit. For study-level work, use level-specific tags (`uni/{slug}/foundation/v1.0.0`) instead of `unit-NN` until the full university is done. Do not mix two universities in one commit.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the commit message format.
