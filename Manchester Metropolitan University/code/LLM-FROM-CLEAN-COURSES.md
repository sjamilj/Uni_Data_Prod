# LLM from `output/clean/courses`

MMU uses the **full catalogue** markdown under `output/clean/courses/` — not `presetup_sample.json` or `clean/pre_setup_course/`.

## Prerequisites

1. Course pages downloaded and cleaned (`download_and_clean_course_pages.py` or `--clean-only`).
2. **Ollama** running (default `http://localhost:11434`).
3. **Uni clean validation** passes (`output/clean/uni/*.md`). Until `english-requirements.md` is a JSON array (like Essex), full extract stops at validation; use shared `--skip-uni-validation` only for smoke tests.

## Commands (repo root)

```powershell
# Index + LLM + normalize + dev CSV (all indexed courses, resume)
python -u "Manchester Metropolitan University/code/run_llm_from_clean.py" --all --resume

# First N courses
python -u "Manchester Metropolitan University/code/run_llm_from_clean.py" --limit 5

# One study level
python -u "Manchester Metropolitan University/code/run_llm_from_clean.py" --study-level postgraduate --all --resume

# Rebuild output/courses.csv only
python -u "Manchester Metropolitan University/code/build_course_index.py"
```

## Index rules

- Built from canonical picks under `clean/courses/**/*.md`.
- Markdown **without** `source_url` / `course_url` in frontmatter is **not** indexed (e.g. bad course-search HTML saves in `other/search-*.md`).
- Duplicate intake variants collapse to one row per course URL.

## Outputs

| Path | Purpose |
|------|---------|
| `output/courses.csv` | LLM input index |
| `output/extracted/` | Per-course JSON |
| `output/extracted_courses.csv` | Flat extract |
| Dev CSV | via normalize + export at end of `run_llm_from_clean.py` |

See also `ENV.MD` (LLM section) and `CLOUDFLARE-CDP.md` for download/listing.

## Course IELTS priority (MMU)

MMU often states IELTS under **Entry requirements** (not a separate English heading). Config in `code/.env`:

- `LLM_STAGE2_ENGLISH_SOURCE=course` — Stage 2 English prompt + lookup use course markdown, not uni JSON.
- `LLM_STAGE2_ENGLISH_SECTIONS=Entry requirements` — section fed to the English LLM prompt.
- `LLM_STAGE2_UNI_PARTS=entry,scholarship,deposit` — uni `english-requirements.json` still used for validation, not default IELTS on each course.

**Final IELTS scalars** (`ieltsMinOverall` / `ieltsMinSection`):

1. **Stage 1 parser** from full course markdown (wins if present).
2. Stage 2 LLM output (if filled).
3. Course-body parse (`parse_english_from_course_markdown`) when IELTS is detected.
4. Else uni `english-requirements.md` JSON (standard UG/PG tiers).

Example: LLM Legal Practice course text **7.0 / 5.5** overrides uni PG default **6.5 / 5.5**.
