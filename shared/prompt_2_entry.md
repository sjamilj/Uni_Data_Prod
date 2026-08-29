# Stage 2a — Bangladesh Entry Requirements (LLM only)

Extract **only** academic entry fields from the Bangladesh page and Stage 1 course-specific notes.

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

- Bangladesh entry page only:

```
{ENTRY_CONTENT}
```

## Course level → Bangladesh academic section

The Bangladesh page is JSON with `studyLevels[]`. Use **only** the object whose `studyLevel` matches `{COURSE_LEVEL}`:

| `{COURSE_LEVEL}` | `studyLevel` value |
|---|---|
| `foundation` | `Foundation` or `Foundation year` |
| `undergraduate` | `Undergraduate` |
| `postgraduate` | `Postgraduate` |

**Critical:** Read requirements from `programs[].requirements[]` in the matching `studyLevel` only. Ignore all other levels.

For `undergraduate`: do **not** include Bachelor/Master qualifications (those belong to postgraduate).
For `foundation`: do **not** include Undergraduate or Postgraduate levels.
For `postgraduate`: do **not** include Foundation or Undergraduate levels.

## `requirements` array

Each item: `{ "degree": "", "grade": "" }`.

Only emit a requirement when **both** a qualification and a grade/score appear in the selected section. Never invent empty placeholders for unused degree types.

Allowed `degree` values (only when stated in the selected section): `HSC`, `A Level`, `Diploma`, `BA`, `BSc`, `BBA`, `BEng`, `BCom`, `MA`, `MSc`, `MBA`, `PhD`.

Map source labels to these values when needed:
- `HSC (Alim)` / `Completion of HSC (Alim)` → `HSC`
- `Bachelor Degree` / `4-year Bachelor degree` → `BSc`
- `Master's Degree` / `2 year Master's degree` → `MSc`

Python also adds a UK-derived `HSC` equivalence row from Stage 1 UCAS / A-Level course-page text when present. Do **not** invent UCAS→GPA conversions in the LLM output.

Typical for undergraduate Bangladesh sections: `HSC`, `A Level`, `Diploma` only.
Typical for postgraduate Bangladesh sections: `BSc`, `MSc` (from Bachelor/Master degree bullets).

`grade` — single field: `GPA 3.00`, `CGPA 3.5`, `AAB`, `2:1`, `60%`, `65%`, etc. Copy verbatim when not converting. Skip qualifications that have no grade in the source.

GPA conversion (only when source gives % without GPA):
- 4.0 scale: `60%→GPA 3.00`, `50%→GPA 2.50`, `70%→GPA 3.50` (80→4.00, 75→3.75, 65→3.25, 55→2.75, 45→2.25, 40→2.00)
- Bangladesh HSC/SSC 5.0 scale when stated: `50%→GPA 3.00`, `60%→GPA 3.50`
- If source says `CGPA 2.5/4.0` or `CGPA 3.5` copy unchanged

## `AcademicRequirementsMetaData`

Do **not** output this field — Python copies full `description` arrays from the Bangladesh JSON (`programs[].description`) and English JSON (`description`) for the matching level.

## Output

Return exactly one JSON object in a single ` ```json ` block. **Only these keys:**

```json
{
  "requirements": [],
  "AcademicRequirementsMetaData": []
}
```
