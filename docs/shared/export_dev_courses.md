# export_dev_courses.py

## 1. Purpose

Flattens `normalized.json` files into a single tab-separated `dev_courses_{UNIVERSITY_NAME}.csv` for downstream consumption.

Final output artifact of the pipeline.

---

## 2. Where this file is used

- End of `run_course_pipeline.run_execute()`
- `run_llm_to_dev_csv.py` final step
- Direct CLI: `python shared/export_dev_courses.py --code-dir ...`

---

## 3. Main classes

| Class | Role |
|-------|------|
| `DevCoursesExporter` | Discover normalized files, build rows, write CSV |
| `DevCoursesExportCLI` | argparse |

---

## 4. Key methods

### `select_normalized_paths(output_dir)`

1. If `courses.csv` index exists → use indexed paths
2. Else scan `extracted/**/normalized.json` and dedupe by course name

### `run(code_dir)`

Writes `output/dev_courses_{UNIVERSITY_NAME}.csv` with Excel-friendly `sep=` hint.

---

## 5. Artifacts

| Path | Content |
|------|---------|
| `dev_courses_{UNIVERSITY_NAME}.csv` | Flat export |
| Optional `dev_courses_*_reviewed.csv` | Human-reviewed copy (some unis) |

---

## 6. Read this next

1. [normalize_admission_data.md](normalize_admission_data.md)
2. [features/normalize-export-flow.md](../features/normalize-export-flow.md)
3. [validate_dev_courses.md](validate_dev_courses.md)
