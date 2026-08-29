# Stage 2 — Requirements and Metadata (LLM only) — DEPRECATED

> **Superseded:** Live extraction now uses three focused prompts to reduce hallucination:
> `prompt_2_entry.md`, `prompt_2_english.md`, `prompt_2_scholarship.md`, `prompt_2_initialDeposit.md`.
> This file is kept as a combined reference only.

Extract **only** the fields below from `{UNI_CONTENT}` and `{STAGE1_JSON}`. Do **not** output university name, course URL, tuition fee, intake, duration, or IELTS/PTE/TOEFL scalar scores — Python fills those from Stage 1.

Use only the provided input. Never use outside knowledge, guess, infer, or estimate. Missing → `""` or `[]`.

## Input
- University: `{UNIVERSITY_NAME}`
- Course: `{COURSE_NAME}`
- URL: `{COURSE_URL}`
- **Course level (use this):** `{COURSE_LEVEL}` — one of `foundation`, `undergraduate`, `postgraduate`
- Stage 1 JSON (course-page facts — use for course-specific entry sentences only):

```json
{STAGE1_JSON}
```

- University pages:

```
{UNI_CONTENT}
```

## Course level → Bangladesh academic section

| `{COURSE_LEVEL}` | Extract from Bangladesh / academic tables |
|---|---|
| `foundation` | Foundation / International Foundation Programme row only |
| `undergraduate` | Undergraduate Degree row only |
| `postgraduate` | Postgraduate Degree row only |

Do **not** mix levels. Parse multiple qualifications from the **one** selected row into separate `requirements` objects.

## `requirements` array

Each item: `{ "degree": "", "grade": "" }`.

Allowed `degree` values (only when stated in source): `HSC`, `A Level`, `Diploma`, `BA`, `BSc`, `BBA`, `BEng`, `BCom`, `MA`, `MSc`, `MBA`, `PhD`.

`grade` — single field: `GPA 3.00`, `CGPA 3.5`, `AAB`, `2:1`, `60%`, etc. Copy verbatim when not converting.

GPA conversion (only when source gives % without GPA):
- 4.0 scale: `60%→GPA 3.00`, `50%→GPA 2.50`, `70%→GPA 3.50` (80→4.00, 75→3.75, 65→3.25, 55→2.75, 45→2.25, 40→2.00)
- Bangladesh HSC/SSC 5.0 scale when stated: `50%→GPA 3.00`, `60%→GPA 3.50`
- If source says `CGPA 2.5/4.0` copy unchanged

## `AcademicRequirementsMetaData`

Array of `{ "subtitle": "", "description": [] }`. Subtitles **exactly**:
- `"Entry Requirements"` — course-specific text from Stage 1 + any extra course-page sentences not in `requirements`
- `"English Requirement"` — verbatim sentence(s) from the **matching** English table row in `{UNI_CONTENT}` for this course level/type (IELTS/PTE/TOEFL wording as written)

Do not merge subtitles. Omit a subtitle if no content. Each `description` item = one verbatim sentence.

## Scholarships

From scholarship content in `{UNI_CONTENT}` (and Stage 1 if course-specific):

| Field | Rule |
|---|---|
| `scholarshipName` | Official name of highest-value scholarship |
| `scholarshipAmount` | Highest numeric total, no symbols |
| `scholarshipType` | `"Amount"` or `"Percentage"` or `""` |
| `scholarshipMetaData` | `[{ "subtitle": "Scholarships", "description": ["..."] }]` — one sentence per scholarship |

## Output

Return exactly one JSON object in a single ` ```json ` block. **Only these keys:**

```json
{
  "requirements": [],
  "AcademicRequirementsMetaData": [],
  "scholarshipName": "",
  "scholarshipAmount": "",
  "scholarshipType": "",
  "scholarshipMetaData": []
}
```
