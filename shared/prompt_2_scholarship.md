# Stage 2c — Scholarships (LLM only)

Extract **only** scholarship fields from the scholarships page (and Stage 1 if course-specific).

Do **not** output `uniName`, course URL, fees, intake, duration, IELTS, or academic `requirements` — Python fills those.

Use only the provided input. Never use outside knowledge, guess, infer, or estimate. Missing → `""` or `[]`.

## Input
- Course: `{COURSE_NAME}`
- URL: `{COURSE_URL}`
- Stage 1 JSON (optional course-specific scholarship notes):

```json
{STAGE1_JSON}
```

- Scholarships page only:

```
{SCHOLARSHIP_CONTENT}
```

## Fields

| Field | Rule |
|---|---|
| `scholarshipName` | Official name of highest-value scholarship |
| `scholarshipAmount` | Highest numeric **total** value, digits only (e.g. `4500` not `£4,500`) |
| `scholarshipType` | Exactly `"Amount"` or `"Percentage"` or `""` |
| `scholarshipMetaData` | Always subtitle exactly `"Scholarships"`; `description` = one complete sentence per fact |

Prefer an explicit multi-year total when stated (e.g. £4,500 across three years → amount `4500`, type `Amount`). Do not invent scholarships from other universities.

## Output

Return exactly one JSON object in a single ` ```json ` block. **Only these keys:**

```json
{
  "scholarshipName": "",
  "scholarshipAmount": "",
  "scholarshipType": "",
  "scholarshipMetaData": []
}
```
