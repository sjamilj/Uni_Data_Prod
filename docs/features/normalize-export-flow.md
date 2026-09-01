# Normalize and export flow

Turning per-course `output.json` into a single developer CSV.

---

## Complete flow

```
extracted/{level}/{slug}/output.json  (many files)
        ↓
normalize_admission_data.py
        ↓
AdmissionRecordNormalizer.process_record()
        ↓
extracted/{level}/{slug}/normalized.json
        ↓
export_dev_courses.py
        ↓
output/dev_courses_{UNIVERSITY_NAME}.csv
```

Execute runs normalize + export automatically at the end via `run_course_pipeline.py`.

---

## Step table — Normalize

| Step | Class | What happens |
|------|-------|--------------|
| 1 | `AdmissionNormalizeCLI` | Finds all `output.json` under `extracted/` |
| 2 | `AdmissionRecordNormalizer` | Per-record pipeline |
| 3 | `FeeNormalizer` | International tuition, ignores placement/deposit lines |
| 4 | `GpaConverter` | UCAS/A-level → HSC GPA equivalents |
| 5 | `EnglishScoreExtractor` | IELTS etc. from structured fields |
| 6 | `ScholarshipNormalizer` | Scholarship array cleanup |
| 7 | Write | `normalized.json` beside `output.json` |

---

## Step table — Export

| Step | Class | What happens |
|------|-------|--------------|
| 1 | `DevCoursesExporter` CLI | `--code-dir` |
| 2 | `select_normalized_paths()` | From `courses.csv` index or disk scan |
| 3 | Row builder | Flattens JSON to CSV columns |
| 4 | Write | `dev_courses_{UNIVERSITY_NAME}.csv` |

---

## Validation (optional)

```powershell
python shared/validate_dev_courses.py --code-dir "University/code"
```

Checks CSV against schema and common data issues.

---

## Dashboard status

| Column | Signal |
|--------|--------|
| Norm | `normalized.json` count vs extracted |
| CSV | `dev_courses_*.csv` exists |

---

## Read this next

1. [shared/normalize_admission_data.md](../shared/normalize_admission_data.md)
2. [shared/export_dev_courses.md](../shared/export_dev_courses.md) (Phase 3)
3. [04-data-flow.md](../04-data-flow.md)
