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
3. Map qualifications to allowed `degree` values only when both qualification and grade/score are stated:
   `HSC`, `A Level`, `Diploma`, `BA`, `BSc`, `BBA`, `BEng`, `BCom`, `MA`, `MSc`, `MBA`, `PhD`.
4. Copy grades verbatim (`2:2`, `GPA 3.00`, `60%`, `AAB`, etc.). Do not invent grades.
5. When the source only says institution-dependent or equivalent qualification with no numeric grade, leave `requirements` empty and put the verbatim sentence(s) in `AcademicRequirementsMetaData` under `"Entry Requirements"`.
6. Do **not** include English test scores here — those belong in the English stage.

## Output

Return exactly one JSON object in a single ` ```json ` block. **Only these keys:**

```json
{
  "requirements": [],
  "AcademicRequirementsMetaData": []
}
```
