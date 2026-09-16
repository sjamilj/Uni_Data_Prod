# Uni_req markdown + JSON formats

Output directory: `{University}/output/clean/uni/`

Fixed filenames (`shared/uni_pages.py`): `bangladesh-entry.md`, `english-requirements.md`, `scholarships.md`, `deposit.md`.

## Frontmatter (all four)

```yaml
---
source_html: uni_req/bangladesh-entry.html
source_url: https://...
page_type: uni
university: {UNIVERSITY_NAME}
cleaned_at: YYYY-MM-DD
---
```

## bangladesh-entry.md

Heading: `## Academic Requirements` then raw JSON object:

```json
{
  "studyLevels": [
    {
      "studyLevel": "Foundation",
      "programs": [
        {
          "program": "International Foundation Programme",
          "requirements": [{ "degree": "HSC", "grade": "CGPA 2.5 / minimum 50%" }],
          "description": ["An Intermediate/High School Certificate with a minimum of 50%/CGPA 2.5"]
        }
      ]
    },
    {
      "studyLevel": "Undergraduate",
      "programs": [
        {
          "program": "",
          "requirements": [
            { "degree": "HSC", "grade": "CGPA 3.5" },
            { "degree": "Diploma", "grade": "above 65%" }
          ],
          "description": ["Intermediate/HSC with CGPA 3.5", "..."]
        }
      ]
    },
    {
      "studyLevel": "Postgraduate",
      "programs": [
        {
          "program": "",
          "requirements": [
            { "degree": "BSc", "grade": "minimum 60% or GPA 2.5/4.0" }
          ],
          "description": ["..."]
        }
      ]
    }
  ]
}
```

`degree` must be from allowed list in `shared/normalize_admission_data.py` (`HSC`, `Diploma`, `BA`, `BSc`, `BBA`, `BEng`, `BCom`, `MA`, `MSc`, `MBA`, `PhD`, etc.).

## deposit.md

Heading: `# Tuition fee deposit` then object:

```json
{
  "initialDeposit": "£5,000",
  "feesMetaData": [
    {
      "subtitle": "Initial Deposit",
      "description": ["The standard overseas tuition fee deposit is £5,000."]
    }
  ]
}
```

## scholarships.md

Heading: `# Scholarships` then array:

```json
[
  {
    "scholarshipName": "International Student Scholarship",
    "scholarshipType": "Amount",
    "scholarshipStudyLevel": "Foundation, Undergraduate, Postgraduate",
    "Eligibility": "...",
    "Amount": "£1,500",
    "description": ["..."]
  }
]
```

## english-requirements.md

Heading: `# English Language Requirements` then array of programme rows:

```json
[
  {
    "TestStudyLevel": "Undergraduate",
    "ProgramName": "Standard undergraduate programmes",
    "TestRequirements": [
      {
        "TestName": "IELTS Academic / IELTS Indicator",
        "ieltsMinOverall": "6.0",
        "ieltsMinSection": "5.5"
      }
    ],
    "description": ["Standard undergraduate programmes: IELTS 6.0 overall with no element below 5.5"]
  }
]
```

May also include flat summary objects with `requiredIelts`, `ieltsMinOverall`, `ieltsMinSection`, `pteMinOverall`, etc. (see Canterbury full file).

## Rules

- Do not invent data; use `""` or `[]` when the source omits a value.
- Operator pastes raw text; you structure JSON only from what they provided.
- Set `UNI_REQ_SOURCE_URLS` in `.env` / `ENV.MD` when saving from live URLs.

Reference copies: `Canterbury Christ Church University/output/clean/uni/*.md`.
