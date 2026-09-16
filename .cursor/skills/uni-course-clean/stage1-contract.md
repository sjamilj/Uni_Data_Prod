# Stage 1 parser contract (markdown shapes)

`Stage1MarkdownParser.extract_stage1_fields_from_md` in `shared/llm_extract.py` drives **parser-owned** fields. After Stage 1 LLM, `apply_parser_owned_stage1_fields` sets `intakeInfo`, `courseDuration`, `tuitionFee`, `currency`, `ieltsMinOverall`, `ieltsMinSection` from hints only — unrecognized shapes become **empty**, not LLM fallbacks.

## Fields and matching lines

| Field | Markdown must include (examples) |
|-------|----------------------------------|
| `intakeInfo` | `- **Start date:** September 2026`, `- **Start:** ...`, `- Start date September 2026`, `Starting: September 2026`, or `**Start date**` then value on next line |
| `courseDuration` | `**Duration:** 1 year full-time` (bold `Duration:` on same line as value) |
| `tuitionFee` + `currency` | `Annual tuition fees: \| £16,000` or `First year tuition fee: \| £16,000`; or `### International students` block with `- Full Time` / duration / `- £...` triples |
| `ieltsMinOverall` / `ieltsMinSection` | `IELTS 6.0 overall with no less than 5.5 in each band` |

## Does NOT parse (common mistakes)

| Seen on site | Problem |
|--------------|---------|
| `### Duration:` then `4 years` on next lines | Use `**Duration:** 4 years` |
| `### Start date:` then `Sep` | Use `- **Start date:** September 2026` (year required for normalized intake) |
| `**Overseas fee:** £18,220` only | Not read by parser; use pipe table form or international fees block |
| Duplicate `## Fees` headings | Tighten `COURSE_CLEAN_BLOCKS` selector |

## Counter-example

Edinburgh Napier `ba-hons-international-tourism-management-undergraduate-fulltime.md` (presetup clean) often yields only `currency` + `degreeName` until cleanup rewrites facts into the shapes above.

## Not from course markdown

Bangladesh/HSC grades and programme entry rows come from `output/clean/uni/bangladesh-entry.md` (**uni-req-json**). Generic `### English language` boilerplate on course pages is expected to stay thin.

## Verify locally

From repo root:

```powershell
cd shared
python -c "from llm_extract import Stage1MarkdownParser as P; import pathlib; b=pathlib.Path('../{University}/output/clean/pre_setup_course/...').read_text(encoding='utf-8'); print(P.extract_stage1_fields_from_md(b))"
```

Target: non-empty `intakeInfo`, `courseDuration`, `tuitionFee` where the live page shows them.
