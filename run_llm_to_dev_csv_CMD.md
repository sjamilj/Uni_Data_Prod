# run_llm_to_dev_csv.py — commands (any PC)

**Run from the cloned repo root** (any PC)  
**Shell:** cmd, PowerShell, or any terminal with Python  
**Script:** `shared/run_llm_to_dev_csv.py`  
**Config:** `{University}/code/.env`  
**Requires:** Ollama running; Phase 2 `output/clean/courses/*.md`

Phases 3–5: LLM extract → normalize → export `dev_courses_*.csv`.

Run these from the repo root. Paths are relative, not machine-specific.

Default below uses `--resume` (skips courses already in `extraction_progress.json`). Drop `--resume` for a full extract from scratch.

| Flag | Purpose |
|---|---|
| `--university` | University folder name |
| `--code-dir` | Path to `{University}/code` |
| `--resume` | Skip completed courses |
| `--limit N` | First N courses only |
| `--build-index` | Force rebuild `output/courses.csv` |
| `--skip-extract` | Skip Phase 3; normalize + export only |
| `--skip-normalize` | Skip Phase 4 |
| `--extract-only` | Phase 3 only |
| `--skip-stage1` | Reuse cached `stage1_parsed.json` |
| `--model` | Ollama model name |
| `--host` | Ollama host URL |

**Outputs (in `{University}\output\`):** `courses.csv`, `extracted\{slug}\`, `extracted\extraction_progress.json`, `extracted\{slug}\normalized.json`, `dev_courses_{UNIVERSITY_NAME}.csv`

---

## Per university (`-Resume`)

### Anglia Ruskin University - ARU

```cmd
python shared/run_llm_to_dev_csv.py --university "Anglia Ruskin University - ARU" --resume
```

### Aston University

```cmd
python shared/run_llm_to_dev_csv.py --university "Aston University" --resume
```

### Birmingham City University

```cmd
python shared/run_llm_to_dev_csv.py --university "Birmingham City University" --resume
```

### Brunel University London

```cmd
python shared/run_llm_to_dev_csv.py --university "Brunel University London" --resume
```

### Buckinghamshire New University

```cmd
python shared/run_llm_to_dev_csv.py --university "Buckinghamshire New University" --resume
```

### Canterbury Christ Church University

```cmd
python shared/run_llm_to_dev_csv.py --university "Canterbury Christ Church University" --resume
```

### Cardiff Metropolitan University

```cmd
python shared/run_llm_to_dev_csv.py --university "Cardiff Metropolitan University" --resume
```

### Edinburgh Napier University

```cmd
python shared/run_llm_to_dev_csv.py --university "Edinburgh Napier University" --resume
```

### Keele University

```cmd
python shared/run_llm_to_dev_csv.py --university "Keele University" --resume
```

### Kingston University

```cmd
python shared/run_llm_to_dev_csv.py --university "Kingston University" --resume
```

### London South Bank University

```cmd
python shared/run_llm_to_dev_csv.py --university "London South Bank University" --resume
```

### Ravensbourne University London

```cmd
python shared/run_llm_to_dev_csv.py --university "Ravensbourne University London" --resume
```

### Teesside University

```cmd
python shared/run_llm_to_dev_csv.py --university "Teesside University" --resume
```

### University of Birmingham

```cmd
python shared/run_llm_to_dev_csv.py --university "University of Birmingham" --resume
```

### University of Derby

```cmd
python shared/run_llm_to_dev_csv.py --university "University of Derby" --resume
```

### University of East London

```cmd
python shared/run_llm_to_dev_csv.py --university "University of East London" --resume
```

### University of Essex

```cmd
python shared/run_llm_to_dev_csv.py --university "University of Essex" --resume
```

### University of Greenwich

```cmd
python shared/run_llm_to_dev_csv.py --university "University of Greenwich" --resume
```

### University of Huddersfield

```cmd
python shared/run_llm_to_dev_csv.py --university "University of Huddersfield" --resume
```

### University of Hull

```cmd
python shared/run_llm_to_dev_csv.py --university "University of Hull" --resume
```

### University of Law

```cmd
python shared/run_llm_to_dev_csv.py --university "University of Law" --resume
```

### University of Roehampton

```cmd
python shared/run_llm_to_dev_csv.py --university "University of Roehampton" --resume
```

### University of Salford

```cmd
python shared/run_llm_to_dev_csv.py --university "University of Salford" --resume
```

### University of South Wales

```cmd
python shared/run_llm_to_dev_csv.py --university "University of South Wales" --resume
```

### University of Suffolk

```cmd
python shared/run_llm_to_dev_csv.py --university "University of Suffolk" --resume
```

### University of Surrey

```cmd
python shared/run_llm_to_dev_csv.py --university "University of Surrey" --resume
```

### University of Wales Trinity Saint David

```cmd
python shared/run_llm_to_dev_csv.py --university "University of Wales Trinity Saint David" --resume
```

### University of West London

```cmd
python shared/run_llm_to_dev_csv.py --university "University of West London" --resume
```

### University of Winchester

```cmd
python shared/run_llm_to_dev_csv.py --university "University of Winchester" --resume
```

---

## Limit / extract-only / skip extract

Drop `-Resume` for a full extract. Add `-Limit`, `-ExtractOnly`, or `-SkipExtract` as needed.

Example — ARU test first 5 courses:

```cmd
python shared/run_llm_to_dev_csv.py --university "Anglia Ruskin University - ARU" -Limit 5 --resume
```

Example — ARU LLM extract only:

```cmd
python shared/run_llm_to_dev_csv.py --university "Anglia Ruskin University - ARU" --extract-only --resume
```

Example — ARU normalize + export only (extraction already done):

```cmd
python shared/run_llm_to_dev_csv.py --university "Anglia Ruskin University - ARU" --skip-extract
```

Example — ARU custom Ollama model:

```cmd
python shared/run_llm_to_dev_csv.py --university "Anglia Ruskin University - ARU" --resume -Model "llama3.1:8b" -OllamaHost "http://localhost:11434"
```

---

## From repo root (relative paths)

**CMD / PowerShell / any terminal:**

```cmd
python shared/run_llm_to_dev_csv.py --university "Anglia Ruskin University - ARU" --resume
```

Replace the university folder name for others.
