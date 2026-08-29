# Universities registry

Fixed unit numbers (alphabetical by folder). Use these in git scopes: `feat(unit-03/bcu): ...`

Find later:

```powershell
git log --oneline --all --grep="unit-03"
git log --oneline -- "Birmingham City University/code"
git tag -l "uni/bcu/*"
```

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

Fill **tag** / **commit** when you run [`scripts/tag-unit-complete.ps1`](scripts/tag-unit-complete.ps1) after merging a completion commit to `main`. Do not mix two universities in one commit.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the commit message format.
