# normalize_admission_data.py

## 1. Purpose

Transforms raw `output.json` from LLM extraction into a consistent `normalized.json` suitable for CSV export.

Handles fee sanitization, GPA conversion, English score extraction, date normalization, and metadata enforcement.

---

## 2. Where this file is used

```
run_course_pipeline.run_execute()  → subprocess at end
run_llm_to_dev_csv.py              → middle step
export_dev_courses.py              → reads normalized.json
validate_dev_courses.py            → validates output
```

---

## 3. Dependencies

| Module | Why |
|--------|-----|
| `programme_name_dictionary.py` | Canonical degree names |
| `uni_paths` | Locate extracted/ tree |

---

## 4. Main classes

| Class | Role |
|-------|------|
| `AdmissionRecordNormalizer` | Top-level per-record pipeline |
| `FeeNormalizer` | Tuition fees; ignores placement/deposit lines |
| `GpaConverter` | UCAS/A-level → HSC GPA text |
| `DegreeNormalizer` | Degree name cleanup |
| `EnglishScoreExtractor` | IELTS etc. |
| `DateNormalizer` | Intake dates |
| `ScholarshipNormalizer` | Scholarship arrays |
| `MetadataEnforcer` | Required field defaults |
| `AdmissionNormalizeCLI` | Batch all `output.json` |

---

## 5. Key methods

### `AdmissionRecordNormalizer.process_record(record)`

Runs normalizers in sequence; returns dict for `normalized.json`.

### `FeeNormalizer.sanitize_international_tuition_fee()`

- Prefers explicit tuition patterns in metadata
- `_extract_gbp_fee_from_metadata()` skips placement-year and deposit-only lines
- Does not clear valid `tuitionFee` when metadata is deposit-only

### `GpaConverter.ucas_points_to_alevel_combo()`

Maps UCAS tariff to A-level combo for Bangladesh GPA derivation.

### `derive_hsc_gpa_from_uk_entry_text()`

Module-level helper used by Stage 1 and tests.

---

## 6. Important code

```python
def process_record(record: dict, ...) -> dict:
```

Entry point used by CLI and tests — applies all normalizers to one course record.

---

## 7. Why it was written this way

LLM output is noisy; normalization is deterministic and testable separately from Ollama. Class per domain (fees, GPA, English) keeps rules isolated when one university mis-extracts fees.

---

## 8. Artifacts

| Path | Content |
|------|---------|
| `extracted/{level}/{slug}/normalized.json` | Normalized record |
| `extracted_courses.csv` | Optional index (some unis) |

---

## 9. Prerequisites

- Target CSV schema (see export module)
- UK admissions terminology (UCAS, IELTS)

---

## 10. Read this next

1. [features/normalize-export-flow.md](../features/normalize-export-flow.md)
2. [export_dev_courses.md](export_dev_courses.md)
3. [llm_extract.md](llm_extract.md)
