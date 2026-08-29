# Course markdown cleanup

## Shared engine (`shared/course_markdown_cleanup.py`)

| Feature | Config |
|---------|--------|
| Remove markdown sections | `COURSE_MARKDOWN_REMOVE_SECTIONS` in `code/.env` |
| uni_req JSON → markdown | Built-in — keeps JSON in a ` ```json ` fenced block (paste-friendly) |

### Manual paste format (`clean/uni/*.md`)

After the YAML frontmatter, each uni file uses:

```markdown
# Page Title

```json
{ ... paste JSON from uni_req/*.html here ... }
```
```

- `bangladesh-entry.md` — object with `studyLevels[]`
- `english-requirements.md` — array of test rows
- `scholarships.md` — array of scholarship objects
- `deposit.md` — object with `initialDeposit` and `feesMetaData`

Re-run uni clean after editing HTML: `python shared/download_and_clean_course_pages.py --code-dir "{University}/code" --clean-uni-only`
| uni_req canonical URLs | `UNI_REQ_SOURCE_URLS` in `code/.env` |

### `COURSE_MARKDOWN_REMOVE_SECTIONS`

One rule per line: `level :: heading` (optional third part: `until_level`).

Heading match is exact unless you use `*`:

- `UK students*` — heading starts with that text (`UK students, 2026/27 (per year)`)
- `*part-time*` — heading contains that text

```ini
COURSE_MARKDOWN_REMOVE_SECTIONS="
4 :: With placement
4 :: With foundation year
4 :: *part-time*
3 :: UK students
5 :: UK students*
5 :: *part-time*
"
```

Removes that heading block until the next heading at `level` (or `until_level` if set).

`cleanup_course_markdown(markdown, code_dir=...)` runs:

1. `.env` section removal (all universities)
2. `{University}/code/course_markdown_cleanup.py` → `cleanup_course_markdown_uni()` if present

## Per-university (`{University}/code/course_markdown_cleanup.py`)

Use only for **conditional** rules that `.env` cannot express.

ARU example: remove `#### Professional Experience` only when both `#### MSc` and `#### Professional Experience` exist → `cleanup_course_markdown_uni()` in ARU's module.

Universities with no extra rules: template no-op `cleanup_course_markdown_uni()` or omit the function.

## Run cleanup only

```powershell
python course_markdown_cleanup.py .
python "../../shared/course_markdown_cleanup.py" .
```

## Manual extra clean (second pass, folder-specific)

**Not in the pipeline.** Re-trim existing `output/clean/courses/{level}/*.md` after the main clean.

| Feature | Config |
|---------|--------|
| Remove sections (all levels) | `EXTRA_CLEAN_REMOVE_SECTIONS` in `code/.env` |
| Per-folder rules | `EXTRA_CLEAN_REMOVE_SECTIONS_FOUNDATION`, `_UNDERGRADUATE`, etc. |
| Conditional Python | `extra_clean_course_markdown_uni(markdown, *, study_level)` in `code/course_markdown_cleanup.py` |

```powershell
python shared/extra_clean_courses.py --code-dir "Birmingham City University/code"
python shared/extra_clean_courses.py --code-dir "Birmingham City University/code" --level foundation undergraduate --passes 2
```

BCU launcher: `Birmingham City University/output/clean/EXTRA_CLEAN.bat`

## New university

1. Set `COURSE_MARKDOWN_REMOVE_SECTIONS` in `.env` for simple drops.
2. Set `UNI_REQ_SOURCE_URLS` if using JSON uni_req files.
3. Add `code/course_markdown_cleanup.py` only if you need conditional Python rules.
