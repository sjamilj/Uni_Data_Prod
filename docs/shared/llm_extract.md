# llm_extract.py

## 1. Purpose

Largest pipeline module (~2800 lines). Extracts structured admission data from course markdown using deterministic parsers (Stage 1) and Ollama LLM calls (Stage 2).

Outputs `output.json` per course slug under `extracted/{level}/{slug}/`.

---

## 2. Where this file is used

| Caller | Context |
|--------|---------|
| `run_course_pipeline.py` | Presetup LLM + Execute per course |
| `run_llm_to_dev_csv.py` | Standalone LLM batch |
| `rerun_entry_requirements.py` | Re-run Stage 2 entry only |

---

## 3. Dependencies

| Dependency | Why |
|------------|-----|
| `ollama_client.py` | HTTP chat API |
| `shared/prompt_*.md` | Prompt templates |
| `normalize_admission_data` | Some shared parsing helpers |
| `uni_paths`, `study_level` | Paths and level keys |

---

## 4. Main classes

| Class | Role |
|-------|------|
| `ExtractionPathConfig` | Prompt paths, `configure_code_dir()` |
| `Stage1MarkdownParser` | Regex/MD: fees, intakes, title |
| `Stage1Enricher` | Merge uni context, promote `feesMetaData` |
| `Stage2Enricher` | Ollama per field group |
| `CourseExtractor` | Orchestrates one course |
| `OutputJsonBuilder` | Merge stages → `output.json` |
| `ExtractionProgressStore` | `extraction_progress.json` |
| `CourseIndexManager` | `courses.csv` index |
| `LlmExtractCLI` | argparse |

---

## 5. Key methods

### `configure_code_dir(code_dir)`

Sets global `_CODE_DIR`, `_OUTPUT_DIR`, loads prompt file paths. Must run before extraction.

### `Stage1MarkdownParser.parse(md_text)`

Extracts scalars without LLM:

- ARU patterns: `**Start date:**`, `**£17,500** International students starting`
- `normalize_intake_text()` for space-separated intakes

### `coalesce_stage1_fields_from_fees_metadata()`

Promotes nested `feesMetaData.tuitionFee` → top-level `tuitionFee` when LLM left scalars empty.

### `Stage2Enricher.enrich(...)`

Runs separate Ollama calls for entry, English, scholarship, deposit. Writes audit JSON per call.

### `CourseExtractor.extract_one(url, study_level, ...)`

Full pipeline for one course markdown file.

---

## 6. Important code

```python
def configure_code_dir(code_dir: Path) -> Path:
    global _CODE_DIR, _OUTPUT_DIR, PROMPT_1, ...
    _CODE_DIR = resolve_code_dir(code_dir)
    _OUTPUT_DIR = resolve_output_dir(_CODE_DIR)
```

**Why globals:** Legacy module structure; `configure_code_dir()` is explicit initialization before batch runs.

---

## 7. Why it was written this way

- **Two stages:** Cheap deterministic parse first; LLM only for unstructured prose.
- **Audit files:** Every prompt/response saved — essential for debugging wrong entry requirements.
- **Class refactor:** Nine classes replace thousand-line functions while keeping `run_extraction()` alias.

---

## 8. Artifacts (per slug)

| File | Content |
|------|---------|
| `output.json` | Merged record |
| `stage1_parsed.json` | Stage 1 only |
| `stage2_llm_parsed.json` | Stage 2 LLM fields |
| `entry_requirement_*.json` | Audit trail |
| `extraction_progress.json` | Parent dir — completed keys |

---

## 9. Prerequisites

- [06-llm-and-ollama.md](../06-llm-and-ollama.md)
- JSON schema for admission fields
- async HTTP (Ollama is sync in client)

---

## 10. Read this next

1. [features/llm-extraction-flow.md](../features/llm-extraction-flow.md)
2. [normalize_admission_data.md](normalize_admission_data.md)
3. `shared/test_entry_requirements.py`
