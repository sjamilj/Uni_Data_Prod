# University Admission Data Normalization Agent (Stage 2)

> **Pipeline note:** Python rule-fills identity, fees, intake, duration, and English test scalars from Stage 1. The live Stage 2 LLM call uses `prompt_2_llm.md` for `requirements`, `AcademicRequirementsMetaData`, and scholarship fields only. This file remains the full specification reference.

Merge **Stage 1 JSON** (course-page extraction) with **university-level page content**, normalize scalar values, and return one JSON row matching the `Course.csv` schema.

Use only the two inputs below. Never use outside knowledge, guess, infer, or estimate. Missing field → `""` (string) or `[]` (array). `description` arrays stay verbatim from source; normalization rules apply only to scalar fields (GPA, fees, duration, etc.).

## Input
- `{UNIVERSITY_NAME}`, `{COURSE_NAME}`, `{COURSE_URL}`
- `{STAGE1_JSON}` — Stage 1 output
- `{UNI_CONTENT}` — university Bangladesh-entry, English-requirements, scholarships/fees pages; select what's relevant to this course's level/faculty/intake

## Merging Rule
Stage 1 JSON and `{UNI_CONTENT}` are equal-priority inputs — for each field, use whichever is more complete/structured, and merge partial data across both when possible.

| Field group | Primary | Secondary |
|---|---|---|
| Fees, intake, duration, deadlines | Stage 1 | Uni pages if Stage 1 missing |
| Course-specific entry requirements | Stage 1 | — |
| Bangladesh academic requirements | Uni Bangladesh section (course-level row only — see below) | Stage 1 `AcademicRequirementsMetaData` |
| English tests | Uni English page (course-level row only — see below) | Stage 1 / course page IELTS table |
| Scholarships | Merge all into `scholarshipMetaData`; pick highest value for scalar fields | |

## Identity Fields
| Column | Rule |
|---|---|
| `uniName` | `{UNIVERSITY_NAME}` exactly |
| `courseName` | `{COURSE_NAME}`, or Stage 1 `courseName` if clearer |
| `programmeName` | Same as `courseName` unless a distinct programme name is explicitly stated |
| `degreeName` | Final award of this course (MSc, BSc, etc.) — not entry qualification |
| `courseUrlExternal` | `{COURSE_URL}` exactly |
| `commission` | Only if explicitly stated, else `""` |

## Determine Course Level

Before selecting uni-page sections, classify the course using `{COURSE_NAME}`, `{COURSE_URL}`, and Stage 1 content:

| Level | Use when |
|---|---|
| **Foundation** | Course name/URL contains `Foundation`, `Foundation Year`, `International Foundation`, or similar foundation programme wording |
| **Postgraduate** | Award or title is MSc, MA, MBA, MRes, MPhil, PhD, PGCE, PGDip, PGCert, MCh, or URL path contains `postgraduate` |
| **Undergraduate** | Default for BSc, BA, BEng, LLB, etc. when not Foundation or Postgraduate |

Use exactly **one** level per course.

## Academic Requirements and Degree Fields

### 1. Select the Correct Academic Requirement Section

Use the **course level** to determine which academic requirement section to extract from `{UNI_CONTENT}` (Bangladesh entry page and any equivalent uni academic tables).

| Course level | Section to use |
|---|---|
| **Foundation course** | **Foundation Requirement** (e.g. *International Foundation Programme*) |
| **Undergraduate course** | **Undergraduate Requirement** (e.g. *Undergraduate Degree*) |
| **Postgraduate course** | **Postgraduate Requirement** (e.g. *Postgraduate Degree*) |

Example sources in `{UNI_CONTENT}`:
- Bangladesh entry page — `Study Level` table rows
- Any other uni academic tables with Foundation / Undergraduate / Postgraduate headings

**Rules:**
- Extract only the row/section matching the course level.
- Do **not** combine Foundation, Undergraduate, and Postgraduate requirements when only one applies.
- Supplement with Stage 1 `AcademicRequirementsMetaData` only for **course-specific** requirements on the course page (e.g. GCSE Maths), not as a substitute for the wrong Bangladesh level.

### 2. Replace Degree/GPA Scalar Fields

Do **not** output:

```text
minDegreeName
minGpa
higherDegreeName
higherGpa
```

Instead, output:

```json
"requirements": [
  {
    "degree": "",
    "grade": ""
  }
]
```

The `requirements` field must be an array.

### 3. Degree Values

The `degree` field must contain the applicable qualification exactly according to normalization rules. Allowed values include (only when supported by source text):

`HSC`, `A Level`, `Diploma`, `BA`, `BSc`, `BBA`, `BEng`, `BCom`, `MA`, `MSc`, `MBA`, `PhD`

Mapping hints (apply only when the source states the underlying qualification):
- Bangladesh Intermediate/HSC, SSC, Dakhil, Alim → `HSC`
- A Levels / International A Levels → `A Level`
- 3-year polytechnic Diploma → `Diploma`
- Bachelor (Arts/Science/Commerce/Honours) → `BA`, `BSc`, or `BCom` as stated
- Master → `MA` or `MSc` as stated

Use only qualifications supported by the selected section and course page. Do not invent or infer qualifications.

### 4. Grade Field

Use a single `grade` field for the actual academic requirement.

The `grade` field may contain:
- GPA requirements, e.g. `GPA 3.00`
- A Level grades, e.g. `AAB`
- Degree classifications, e.g. `2:1`
- Percentage/CGPA text when explicitly stated, e.g. `CGPA 3.5`, `60%`
- Other explicitly stated academic grades/scores from the source

Do **not** create separate `gpa` or `score` fields.

Examples:

```json
{ "degree": "HSC", "grade": "GPA 3.00" }
```

```json
{ "degree": "A Level", "grade": "AAB" }
```

```json
{ "degree": "BA", "grade": "2:1" }
```

### 5. Multiple Requirements

If the source provides multiple accepted qualifications within the selected section, create one object per qualification.

```json
"requirements": [
  { "degree": "HSC", "grade": "GPA 3.00" },
  { "degree": "Diploma", "grade": "GPA 3.00" },
  { "degree": "A Level", "grade": "AAB" },
  { "degree": "BA", "grade": "2:1" },
  { "degree": "MSc", "grade": "GPA 3.00" },
  { "degree": "MA", "grade": "GPA 3.00" }
]
```

If no academic requirement is stated for the selected level → `"requirements": []`.

### GPA / Percentage Normalization (for `grade` only)

When converting Bangladesh or UK percentages to GPA inside the `grade` field, use numeric GPA with max 2 decimals and prefix `GPA ` (e.g. `GPA 3.00`). Ignore qualifier words ("minimum", "at least", "overall", "or above", "equivalent").

**4.0 scale** (Bachelor's/Master's/Foundation/HND, UK & international percentages, default):
`80%→4.00, 75%→3.75, 70%→3.50, 65%→3.25, 60%→3.00, 55%→2.75, 50%→2.50, 45%→2.25, 40%→2.00, <40%→0.00`

**5.0 scale** (Bangladesh SSC/HSC/Dakhil/Alim only):
`80%→5.00, 70%→4.00, 60%→3.50, 50%→3.00, 40%→2.00, 33%→1.00, <33%→0.00`

**5.0 scale with university-specific thresholds** (when a university states Bangladesh SSC/HSC on this scale):
`80%→5.00, 75%→4.69, 70%→4.38, 65%→4.06, 60%→3.75, 55%→3.44, 50%→3.13, 45%→2.81, 40%→2.50, <40%→0.00`

**UK degree classification:** First (70%+)→4.00, Upper Second/2:1 (60–69%)→3.00, Lower Second/2:2 (50–59%)→2.50, Third (40–49%)→2.00.

**UK GCSE:** 9–7/A*–A→5.00, 6–5/B→4.00, 4/C→2.00, below 4→0.00.

If the source already states GPA/CGPA verbatim, copy into `grade` unchanged (e.g. `CGPA 2.5/4.0`).

Apply conversion only when the source gives a percentage/classification that maps unambiguously; otherwise copy the stated grade text verbatim.

## English Test Fields — Select by Course Level

From `{UNI_CONTENT}` English requirements page, select the **one** row/section that matches the course:

| Course level / type | Typical English table row |
|---|---|
| Standard undergraduate (non-health) | Standard undergraduate and postgraduate programmes |
| Standard postgraduate (not in non-standard list) | Standard undergraduate and postgraduate programmes |
| Professional health undergraduate (Nursing, Physiotherapy, etc.) | Professional health undergraduate programmes |
| Nursing undergraduate 2027+ | Nursing undergraduate programmes starting 2027 onwards |
| Non-standard postgraduate (listed programmes) | Match named course in non-standard list, else *Non-standard postgraduate programmes* |
| Foundation | Use undergraduate standard row unless a foundation-specific row exists |

Populate `ieltsMinOverall`, `ieltsMinSection`, `toeflMinOverall`, `toeflMinSection`, `pteMinOverall`, `pteMinSection` — numeric strings only, from the selected row. Never infer missing bands; never convert between test types. Prefer course-page IELTS table when it is more specific than the generic uni row.

## Tuition Fee
- International fee only (never UK/EU/Home if International exists).
- `tuitionFee`: numeric only, no symbols/commas. `currency`: ISO code as stated; default `GBP` for UK universities if `£` is used without a code.
- If multiple international yearly fees are given, use the **highest**.
- Not available → `""`.

Example: `UK: £9,000/yr | International: £18,400/yr` → `"tuitionFee": "18400", "currency": "GBP"`.

## Deposit / Application Fee
`initialDeposit`, `applicationFee` — numeric only, symbols stripped, from whichever source states it; `""` if missing.

## Application Deadline
`applicationDeadline` — copy exactly as written. Never reformat, never assume, never default a missing day to `01`.

## Intake
`intakeInfo` — raw text, multiple intakes joined with `", "`. No format conversion. E.g. `"September 2026, January 2027"`.

## Course Duration
`courseDuration` — numeric string, **months only**: `1 year→"12", 2 years→"24", 3 years→"36", 4 years→"48", 18 months→"18"`. Convert other explicit durations to months only if unambiguous; otherwise `""`.

## AcademicRequirementsMetaData
Merge Stage 1 array with **course-page-only** entry text (not Bangladesh level tables). Always an array; subtitles only `"Entry Requirements"` / `"English Requirement"` (exact, never merged into one object); each `description` item = one verbatim sentence. Omit a subtitle entirely if no content exists for it — no empty placeholders.

Do **not** duplicate structured `requirements` entries here unless the source sentence adds detail not captured in `requirements`.

## feesMetaData
Array of `{ "subtitle": "Fees and Funding", "description": [] }` — full raw fee/deposit text as separate verbatim sentences. Prefer Stage 1; supplement from uni pages.

## Scholarship Normalization
| Field | Rule |
|---|---|
| `scholarshipName` | Highest-total-value scholarship found; official/umbrella name |
| `scholarshipAmount` | Highest stated **total** value, numeric only — don't multiply by years unless the total is explicit |
| `scholarshipType` | `"Amount"` or `"Percentage"`; `""` if unknown |

`scholarshipMetaData` — one object, subtitle `"Scholarships"`, `description` = all relevant scholarships (course + uni) as complete sentences (name, amount, eligibility, conditions).

## Metadata Format (all `*MetaData` fields)
Always an array of `{ "subtitle": "", "description": [] }` — never null, never a bare object, `description` always an array of strings.

## Output
Return exactly one JSON object in a single ` ```json ` block — no text outside it. All keys required; empty → `""` or `[]`.

```json
{
  "uniName": "",
  "programmeName": "",
  "courseName": "",
  "requirements": [],
  "AcademicRequirementsMetaData": [],
  "intakeInfo": "",
  "courseDuration": "",
  "tuitionFee": "",
  "currency": "",
  "initialDeposit": "",
  "applicationFee": "",
  "feesMetaData": [],
  "commission": "",
  "applicationDeadline": "",
  "ieltsMinOverall": "",
  "ieltsMinSection": "",
  "toeflMinOverall": "",
  "toeflMinSection": "",
  "pteMinOverall": "",
  "pteMinSection": "",
  "scholarshipName": "",
  "scholarshipAmount": "",
  "scholarshipType": "",
  "scholarshipMetaData": [],
  "degreeName": "",
  "courseUrlExternal": ""
}
```
