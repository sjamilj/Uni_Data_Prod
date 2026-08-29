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
| `docs` | Registry, RUN.md, PIPELINE.md only |
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
