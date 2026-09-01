# validate_uni_clean.py

## 1. Purpose

Validates cleaned university requirement markdown (`clean/uni/*.md`) for required sections, links, and content quality before LLM extraction relies on them.

---

## 2. Where this file is used

```powershell
python shared/validate_uni_clean.py --university-dir "Birmingham City University"
```

Used in tests: `test_entry_requirements.test_validate_bcu_uni_clean_passes`

---

## 3. Main classes

| Class | Role |
|-------|------|
| `UniCleanValidator` | Run checks, collect issues |
| `ValidationReport` | `error_count`, list of `ValidationIssue` |
| `UniCleanValidateCLI` | argparse |

---

## 4. What it checks

- Required uni pages present (bangladesh-entry, english-requirements, scholarships, deposit)
- Markdown structure expectations per page type
- Broken or missing source URLs in frontmatter

---

## 5. Read this next

1. [download_and_clean_course_pages.md](download_and_clean_course_pages.md)
2. [features/download-clean-flow.md](../features/download-clean-flow.md)
