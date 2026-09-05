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
   - `Pearson: 59 (59 in all subscores)` → `pteMinOverall`=`59`, `pteMinSection`=`59`
   - `TOEFL: 90 (min 20 in all areas)` → `toeflMinOverall`=`90`, `toeflMinSection`=`20`
3. Prefer Stage 1 IELTS overall/section when present and course-specific.
4. All score fields are numeric strings only. Never convert between test types.
5. Put verbatim English requirement sentence(s) in `AcademicRequirementsMetaData` under subtitle `"English Requirement"` — one sentence per array item.

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
