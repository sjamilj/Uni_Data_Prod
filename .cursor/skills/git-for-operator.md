# Git — operator runs everything

You run all git commands. The agent **never** runs git in the terminal.

## Never

- Run `git commit`, `git push`, `git tag`, `git restore`, `git checkout`, `git add`, or any other git command in the terminal.
- Chain git steps into one line (e.g. `restore --staged` + `commit` + `tag` + `show` in a single paste block).
- Use placeholder messages like `your message here` or `your tag message here` without a real suggestion.
- Add `--trailer`, `Co-authored-by`, or similar unless you explicitly request it.

## Always

- Give **separate** copy-paste commands, **one logical step per block**.
- Use repo root as cwd, or a single `cd` to repo root in its own block before other commands.
- **Recommend a concrete commit message** for the change (you may edit before `-m`). Match [CONTRIBUTING.md](../../CONTRIBUTING.md): scopes such as `chore(infra):`, `feat(unit-NN/slug):`, `docs:`, `chore(shared):`.
- **Recommend a concrete tag annotation** for every `git tag -a` (you may edit before `-m`). Match existing tag style in CONTRIBUTING / UNIVERSITIES_REGISTRY.

Pipeline Python commands (`python shared/...`) are fine for the agent to run when you want automation; **git is never automated**.

## Canonical repo docs

| Doc | Use when |
|-----|----------|
| [CONTRIBUTING.md](../../CONTRIBUTING.md) | Commit scopes (`feat(unit-NN/slug): …`), `shared/v1.2.0` baseline, `chore(shared):`, **infra tags** (`infra/onboarding-skills/v*`) |
| [docs/PIPELINE.md](../../docs/PIPELINE.md) | Operational runbook (phases, artifacts) — not git mechanics |
| [UNIVERSITIES_REGISTRY.md](../../UNIVERSITIES_REGISTRY.md) | Unit numbers, slugs, tag naming table, `git log --grep=unit-NN` |
| [scripts/README.md](../../scripts/README.md) | `commit-uni.cmd`, `tag-uni.cmd`, `checkout-uni.cmd`; `-Pick infra` for skills/registry/scripts-only commits |
| [README.md](../../README.md) | Operator phrases (“Working with the agent”) — not git mechanics |

**Infra commit (skills + registry + contributing + scripts docs, no university folder):**

```powershell
.\scripts\commit-uni.cmd -Pick infra -Type chore -Summary "add Cursor uni onboarding skills and operator git rules"
```

Copy the printed `git add` / `git commit` lines (paths should include `.cursor/skills/`, root `README.md`, `CONTRIBUTING.md`, `UNIVERSITIES_REGISTRY.md`, `scripts/README.md`, and `.gitignore` skills exception if changed).

## Suggested message patterns

| Change | Example commit `-m` | Example tag `-m` (if tagging) |
|--------|---------------------|-------------------------------|
| Cursor onboarding skills + README + `.gitignore` skills exception | `chore(infra): add Cursor uni onboarding skills and operator git rules` | `infra: Cursor uni onboarding skills and README operator guide` → `infra/onboarding-skills/v1.0.0` |
| Skills cross-links + registry/contributing/scripts doc tweaks (no behaviour change) | `docs(infra): link onboarding skills to CONTRIBUTING, registry, and scripts README` | `infra: onboarding skills doc cross-links` → `infra/onboarding-skills/v1.0.1` |
| Skill YAML descriptions / doc paths only (`.cursor/skills/`) | `docs(infra): refresh Cursor skill triggers and docs/PIPELINE links` | `infra: onboarding skill descriptions v1.0.2` → `infra/onboarding-skills/v1.0.2` |
| Registry / CONTRIBUTING tag table only (no skills) | `docs: update shared v1.2.0 baseline in CONTRIBUTING` | (usually no tag) |
| General `shared/` behaviour (all unis) | `chore(shared): describe the behaviour change in one line` | `shared: same one-line summary as commit` → tag name `shared/v1.2.0` or patch bump per CONTRIBUTING |
| One university folder (+ optional `-IncludeShared`) | `feat(unit-NN/slug): complete foundation pipeline` | `uni/{slug}/foundation/v1.0.0` with message `uni: {slug} foundation export v1.0.0` |
| Pin `shared/` to baseline only | `chore(shared): restore shared to shared/v1.2.0 baseline` | (no new shared tag — matches existing `shared/v1.2.0`) |

## Example blocks (agent fills real strings, not placeholders)

**Commit**

```powershell
cd "<repo-root>"
git add .gitignore README.md .cursor/skills/
git status
git commit -m "chore(infra): add Cursor uni onboarding skills and operator git rules"
```

**Tag** (after commit; bump patch `v1.0.0` → `v1.0.1` when skills/docs change again)

```powershell
git tag -a infra/onboarding-skills/v1.0.0 -m "infra: Cursor uni onboarding skills and README operator guide"
git tag -l "infra/*"
```

```powershell
git push origin main
git push origin infra/onboarding-skills/v1.0.0
```

When the agent recommends git steps, it must state **Recommended commit message:** and **Recommended tag message:** (if tagging) in prose above the blocks, then use those exact strings inside `-m "..."`.
