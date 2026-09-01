# LLM extraction flow

How one course markdown file becomes structured `output.json`.

---

## Complete flow

```
clean/courses/{level}/{slug}.md
clean/uni/*.md (context)
        ↓
llm_extract.py run_extraction()
        ↓
configure_code_dir(code_dir)
        ↓
CourseExtractor.extract_one()
        ↓
Stage1MarkdownParser + Stage1Enricher
        ↓
stage1_parsed.json
        ↓
Stage2Enricher (Ollama per field group)
        ↓
stage2_parsed.json, stage2_llm_parsed.json
        ↓
OutputJsonBuilder.merge()
        ↓
output.json
        ↓
normalize_admission_data.py → normalized.json
```

---

## Step table

| Step | Class | What happens |
|------|-------|--------------|
| 1 | `LlmExtractCLI` | CLI: `--resume`, slug filters |
| 2 | `CourseExtractor` | Orchestrates one course |
| 3 | `Stage1MarkdownParser` | Regex/MD: fees, intakes, title |
| 4 | `Stage1Enricher` | Merges uni context, promotes `feesMetaData` |
| 5 | `Stage2Enricher` | Ollama: entry, English, scholarship, deposit |
| 6 | `ollama_client.py` | HTTP to Ollama API |
| 7 | `OutputJsonBuilder` | Final `output.json` |
| 8 | `ExtractionProgressStore` | Marks slug completed/failed |

---

## Audit trail (per slug folder)

Each LLM call saves:

- `*_prompt.txt` — what was sent
- `*_response.json` — raw model output
- `*_parsed.json` — validated JSON

**Why:** Debug extraction failures without re-running Ollama.

---

## Resume behaviour

`extraction_progress.json`:

```json
{
  "completed": ["foundation/study-undergraduate-biology", ...],
  "failed": [...]
}
```

With `--resume`, completed keys are skipped.

---

## Ollama pre-check

Dashboard calls `GET {ollama_host}/api/tags` before starting Presetup LLM or Execute.

`PipelineOrchestrator.ollama_ok()` — same check in CLI orchestrator.

---

## Read this next

1. [06-llm-and-ollama.md](../06-llm-and-ollama.md)
2. [shared/llm_extract.md](../shared/llm_extract.md)
3. [normalize-export-flow.md](normalize-export-flow.md)
