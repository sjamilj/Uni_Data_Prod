# LLM and Ollama

How local LLM extraction works in this pipeline.

---

## Overview

Structured admission data is extracted using **Ollama** (default `http://localhost:11434`). The pipeline does not call cloud APIs for course extraction.

```
clean/courses/{level}/{slug}.md
        ↓
Stage 1: regex + markdown parsers (no LLM)
        ↓
Stage 2: Ollama prompts per field group
        ↓
output.json + audit JSON in extracted/{level}/{slug}/
```

---

## Prerequisites

1. [Ollama](https://ollama.com/) installed and running
2. Model pulled (configured in `ollama_client.py` / env)
3. Dashboard checks `/api/tags` before Presetup LLM and Execute

---

## Prompt templates (`shared/prompt_*.md`)

| File | Used for |
|------|----------|
| `prompt_1.md` | Stage 1 LLM assist (when needed) |
| `prompt_2.md` | General stage 2 |
| `prompt_2_llm.md` | Core course fields |
| `prompt_2_entry.md` | Entry requirements |
| `prompt_2_english.md` | English language requirements |
| `prompt_2_scholarship.md` | Scholarships |
| `prompt_2_initialDeposit.md` | Deposits |

Prompts are loaded from `shared/` only (`ExtractionPathConfig.resolve_prompt_path`).

**Why separate prompts:** Smaller, focused JSON schemas per domain reduce hallucination and make retries cheaper.

---

## Stage 1 — deterministic first

`Stage1MarkdownParser` extracts from markdown without LLM:

- Course name, duration, intake lines
- Tuition fee patterns (e.g. ARU `**£17,500** International students starting`)
- `feesMetaData` object promotion to scalars

`Stage1Enricher` merges parser output with uni-level context from `clean/uni/*.md`.

**Why Stage 1 exists:** Fees and intakes often appear in predictable markdown structure; LLM is reserved for messy entry-requirement prose.

---

## Stage 2 — LLM field groups

`Stage2Enricher` runs targeted Ollama calls:

| Group | Output fields |
|-------|---------------|
| Entry | Bangladesh/international entry, UCAS, degree names, GPA |
| English | IELTS, TOEFL, etc. |
| Scholarship | Awards, amounts, eligibility |
| Initial deposit | Deposit amounts and rules |

Each call writes `*_prompt.txt`, `*_response.json`, `*_parsed.json` for audit.

---

## Final merge

`OutputJsonBuilder` combines Stage 1 + Stage 2 into `output.json`, then `normalize_admission_data.py` produces `normalized.json`.

---

## Progress and resume

`ExtractionProgressStore` tracks `completed` and `failed` slug keys in `extraction_progress.json`.

Execute and Presetup LLM pass `--resume` to skip completed courses.

---

## Configuration touchpoints

| Setting | Where |
|---------|-------|
| Ollama host | `dashboard/pipeline_config.json` → `ollama_host` |
| Code/output paths | `configure_code_dir()` in `llm_extract.py` |
| Uni context MD | `output/clean/uni/bangladesh-entry.md`, etc. |

---

## Common issues

| Symptom | Check |
|---------|-------|
| Empty `intakeInfo` / `tuitionFee` | Stage 1 parser + `feesMetaData` promotion in `llm_extract.py` |
| Wrong fee (placement year) | `FeeNormalizer` in `normalize_admission_data.py` |
| Dashboard blocks LLM | Ollama not running; host URL |
| Slow Execute | One course at a time by design — allows review and resume |

---

## See also

- [shared/llm_extract.md](shared/llm_extract.md) — class-level detail
- [features/llm-extraction-flow.md](features/llm-extraction-flow.md)
- [features/presetup-and-execute-flow.md](features/presetup-and-execute-flow.md)
