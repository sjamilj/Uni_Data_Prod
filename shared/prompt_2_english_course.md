# Stage 2b — Course-page English requirements (LLM only)

Extract English test **scores** from the course page English section.

Do **not** output `uniName`, course URL, fees, intake, duration, academic `requirements`, or scholarships — Python fills those.

Use only the provided input. Never use outside knowledge, guess, infer, or estimate. Missing → `""` or `[]`.

## Input
- Course: `{COURSE_NAME}`
- URL: `{COURSE_URL}`
- **Course level (use this):** `{COURSE_LEVEL}` — one of `foundation`, `undergraduate`, `postgraduate`
- Stage 1 JSON (course-page IELTS — prefer when more specific):

```json
{STAGE1_JSON}
```

- Course-page English section only:

```
{ENGLISH_CONTENT}
```

## Rules

1. Read IELTS, Pearson/PTE, BrunELT, and TOEFL from the course page bullets or tables.
2. Examples:
   - `IELTS: 6.5 (min 6 in all areas)` → `ieltsMinOverall`=`6.5`, `ieltsMinSection`=`6`
   - `IELTS Academic ... Score required 6.5 No bands less than 6.0` → `ieltsMinOverall`=`6.5`, `ieltsMinSection`=`6.0` (the "no bands less than" value may sit on a separate line below the score)
   - `Pearson: 59 (59 in all subscores)` → `pteMinOverall`=`59`, `pteMinSection`=`59`
   - `TOEFL: 90 (min 20 in all areas)` → `toeflMinOverall`=`90`, `toeflMinSection`=`20`
3. Prefer Stage 1 IELTS overall/section when present and course-specific.
4. If the course only references an English test **Group** (e.g. `Group B`), leave score fields empty — Python maps the group to IELTS/PTE/TOEFL from the university table.
5. If a test is **not stated** on the course page (e.g. only a link to "alternative English language requirements"), leave that test's fields `""`. Never fill TOEFL/PTE from memory or from examples in this prompt.
6. All score fields are numeric strings only. Never convert between test types.
7. Put the verbatim English requirement in `AcademicRequirementsMetaData` under subtitle `"English Requirement"` — one sentence per array item. Combine the test name, score and band rule of the same row into one item, e.g.:
   `IELTS Academic International English Language Testing System: 6.5, No bands less than 6.0`
8. Ignore links such as "See alternative English language requirements". Never output `"N/A"`.

## Output

Return exactly one JSON object in a single ` ```json ` block:

```json
{
  "ieltsMinOverall": "",
  "ieltsMinSection": "",
  "pteMinOverall": "",
  "pteMinSection": "",
  "toeflMinOverall": "",
  "toeflMinSection": "",
  "AcademicRequirementsMetaData": []
}
```