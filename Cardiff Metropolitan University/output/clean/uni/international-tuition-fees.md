---
source_html: operator-paste
source_url: https://www.cardiffmet.ac.uk/international-students/fees-and-finance/
page_type: uni
university: Cardiff Metropolitan University
cleaned_at: 2026-09-16
---
# International student course fees

International Student Courses Fees (2026/27). Course pages do not list overseas £ amounts; apply this mapping in `code/course_markdown_cleanup.py` when cleaning presetup/full course markdown.

```json
{
  "academicYear": "2026/27",
  "currency": "GBP",
  "sourceNote": "Operator-pasted international fee table; not on individual course HTML.",
  "bands": [
    {
      "category": "Undergraduate Degree",
      "studyLevels": ["undergraduate"],
      "length": "3-4 years",
      "tuitionFee": "16000",
      "feeLine": "Annual tuition fees: | £16,000 per year"
    },
    {
      "category": "Top-Up Degree",
      "urlPatterns": ["top-up", "topup"],
      "length": "1 year",
      "tuitionFee": "16000",
      "feeLine": "Annual tuition fees: | £16,000"
    },
    {
      "category": "Foundation leading to Health Sciences (international)",
      "urlPatterns": ["foundation-leading-to-health-sciences"],
      "studyLevels": ["foundation"],
      "length": "4 years",
      "tuitionFee": "17000",
      "feeLine": "First year tuition fee: | £17,000",
      "feesMetaData": [
        {
          "subtitle": "International tuition fees",
          "description": [
            "Foundation leading to Health Sciences for international students: £17,000 (year 1); £16,000 per year (years 2-4)."
          ]
        }
      ]
    },
    {
      "category": "MBA",
      "urlPatterns": ["mba"],
      "length": "1 year",
      "tuitionFee": "19500",
      "feeLine": "Annual tuition fees: | £19,500"
    },
    {
      "category": "PGCE",
      "urlPatterns": ["pgce"],
      "length": "1 year",
      "tuitionFee": "14000",
      "feeLine": "Annual tuition fees: | £14,000"
    },
    {
      "category": "Postgraduate Doctoral Degree",
      "studyLevels": ["postgraduate_research"],
      "length": "varies",
      "tuitionFee": "17600",
      "feeLine": "Annual tuition fees: | £17,600 per year"
    },
    {
      "category": "Postgraduate Masters Degree",
      "studyLevels": ["postgraduate"],
      "length": "1-2 years",
      "tuitionFee": "17600",
      "feeLine": "Annual tuition fees: | £17,600 per year"
    },
    {
      "category": "Foundation / undergraduate (default international)",
      "studyLevels": ["foundation", "undergraduate"],
      "length": "per year",
      "tuitionFee": "16000",
      "feeLine": "Annual tuition fees: | £16,000 per year"
    }
  ]
}
```
