# Stage 2a — Course-page entry requirements (LLM only)

Extract academic entry fields from the **course page** international entry section and Stage 1.

Do **not** output `uniName`, course URL, fees, intake, duration, IELTS/PTE/TOEFL scalars, or scholarships — Python fills those.

Use only the provided input. Never use outside knowledge, guess, infer, or estimate. Missing → `""` or `[]`.

## Input
- Course: `{COURSE_NAME}`
- URL: `{COURSE_URL}`
- **Course level (use this):** `{COURSE_LEVEL}` — one of `foundation`, `undergraduate`, `postgraduate`
- Stage 1 JSON (course-page facts — use for course-specific entry sentences only):

```json
{STAGE1_JSON}
```

- Course-page entry section only:

```
{ENTRY_CONTENT}
```

## Rules

1. Use the **international / Bangladesh** entry text from the course page when present.
2. Ignore UK-only entry requirements, visa/CAS boilerplate, and country-selector UI text (`Select your country/region`).
3. **Two entry blocks (New Zealand pages):** when the page shows separate blocks for *"University of Auckland"* (GPA) and *"Another tertiary institution"* (GPE), use only the **"Another tertiary institution" / GPE** block. Ignore the "University of Auckland" / GPA block.
4. **NZ GPA / GPE values are not converted and not placed in `requirements`.** Bangladesh grades come from the Bangladesh entry page (Python merges them). Copy each study-option row into `AcademicRequirementsMetaData` under `"Entry Requirements"` as one sentence per row, in the form:
   `<Study option>: <Grade required text> - <Qualification text>`
   Example: `Taught 180 points: GPE Grade Point Equivalent 5.0 - A Bachelors degree or Postgraduate Certificate in Design`
5. For other universities: map qualifications to allowed `degree` values only when both qualification and grade/score are stated:
   `HSC`, `A Level`, `Diploma`, `BA`, `BSc`, `BBA`, `BEng`, `BCom`, `MA`, `MSc`, `MBA`, `PhD`.
6. Copy grades verbatim (`2:2`, `GPA 3.00`, `GPE 5.0`, `60%`, `AAB`, etc.). Do not invent or convert grades.
7. When the source only says institution-dependent or equivalent qualification with no numeric grade, leave `requirements` empty and put the verbatim sentence(s) in `AcademicRequirementsMetaData` under `"Entry Requirements"`.
8. Also copy other admission conditions in the same section verbatim as separate sentences under `"Entry Requirements"` (e.g. interview needed, written statement, CV, portfolio).
9. Do **not** include English test scores here — those belong in the English stage.
10. Never output `"N/A"`. No content → `""` or `[]`.

## Output

Return exactly one JSON object in a single ` ```json ` block. **Only these keys:**

```json
{
  "requirements": [],
  "AcademicRequirementsMetaData": []
}
```