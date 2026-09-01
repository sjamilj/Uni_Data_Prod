# validate_dev_courses.py

## 1. Purpose

Validates exported `dev_courses_*.csv` against schema rules, level consistency, and common data defects.

Run after export before marking a university complete.

---

## 2. Where this file is used

```powershell
python shared/validate_dev_courses.py --code-dir "University/code"
```

---

## 3. Main classes

| Class | Role |
|-------|------|
| `DevCoursesValidator` | Row-level validation |
| `CourseLevelResolver` | Match CSV row to study level |
| `DevCoursesValidationResult` | Aggregated errors/warnings |
| `DevCoursesValidateCLI` | argparse |

---

## 4. Typical checks

- Required columns populated
- Fee/intake format
- Study level matches URL/slug
- Duplicate course names

---

## 5. Read this next

1. [export_dev_courses.md](export_dev_courses.md)
2. [normalize_admission_data.md](normalize_admission_data.md)
