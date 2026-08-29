# Stage 2b — English Language Requirements (LLM only)

Extract English test **scores** and metadata for this course from the English page.

Do **not** output `uniName`, course URL, fees, intake, duration, academic `requirements`, or scholarships — Python fills those.

Use only the provided input. Never use outside knowledge, guess, infer, or estimate. Missing → `""` or `[]`.

## Input
- Course: `{COURSE_NAME}`
- URL: `{COURSE_URL}`
- **Course level (use this):** `{COURSE_LEVEL}` — one of `foundation`, `undergraduate`, `postgraduate`
- Stage 1 JSON (course-page IELTS — use if more specific than the uni table):

```json
{STAGE1_JSON}
```

- English language requirements page only:

```
{ENGLISH_CONTENT}
```

## Select the matching course-type row

Use the **same** course-type label across the IELTS, PTE, and TOEFL tables.

| Course level / type | Typical row label |
|---|---|
| Standard undergraduate (non-health) | Standard undergraduate and postgraduate programmes |
| Standard postgraduate (not in non-standard list) | Standard undergraduate and postgraduate programmes |
| Professional health undergraduate (Nursing, Physiotherapy, etc.) | Professional health undergraduate programmes |
| Nursing undergraduate 2027+ | Nursing undergraduate programmes starting 2027 onwards |
| Named course in non-standard / named-course tables | That course's row |
| Foundation | Standard undergraduate and postgraduate programmes unless a foundation row exists |

Example — if the matching row is **Standard undergraduate and postgraduate programmes**, extract from all three tables:

| Test | Example cell | Scalars |
|---|---|---|
| IELTS | `6.0 overall with no element below 5.5` | `ieltsMinOverall`=`6.0`, `ieltsMinSection`=`5.5` |
| PTE | `59 overall with no element below 59` | `pteMinOverall`=`59`, `pteMinSection`=`59` |
| TOEFL IBT | `Minimum of 60 overall: Reading 8, Listening 7, Speaking 16 and Writing 18` | `toeflMinOverall`=`60`, `toeflMinSection`=`7` (lowest section) |

For TOEFL tables with **two** score columns, use the **first** (classic TOEFL IBT) column — ignore the newer “from January 2026” column unless it is the only one.

Prefer Stage 1 IELTS overall/section when Stage 1 has them and they are for this course; still fill PTE/TOEFL from the uni tables.

## Scalar field rules

All score fields are numeric strings only (e.g. `"6.0"`, `"59"`, `"60"`). Never invent bands. Never convert between IELTS/PTE/TOEFL.

| Field | Rule |
|---|---|
| `ieltsMinOverall` / `ieltsMinSection` | From IELTS row: overall + “no element below” band |
| `pteMinOverall` / `pteMinSection` | From PTE row: overall + “no element below” band |
| `toeflMinOverall` | Overall minimum from TOEFL row |
| `toeflMinSection` | Lowest listed section score when Reading/Listening/Speaking/Writing are given; else the single section minimum if stated |

## `AcademicRequirementsMetaData`

Do **not** output this field — Python copies the full `description` array from the matching English JSON row.

## Output

Return exactly one JSON object in a single ` ```json ` block. **Only these keys:**

```json
{
  "AcademicRequirementsMetaData": [],
  "ieltsMinOverall": "",
  "ieltsMinSection": "",
  "toeflMinOverall": "",
  "toeflMinSection": "",
  "pteMinOverall": "",
  "pteMinSection": ""
}
```
