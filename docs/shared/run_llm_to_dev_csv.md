# run_llm_to_dev_csv.py

## 1. Purpose

Chains three steps for one university without the dashboard:

1. `llm_extract.py` (optional skip)
2. `normalize_admission_data.py`
3. `export_dev_courses.py`

Portable alternative to PowerShell `run_llm_to_dev_csv.ps1`.

---

## 2. Where this file is used

```powershell
python shared/run_llm_to_dev_csv.py --code-dir "Aston University/code" --resume
python shared/run_llm_to_dev_csv.py --university "Aston University" --resume
```

---

## 3. Main classes

| Class | Role |
|-------|------|
| `LlmToDevCsvPipeline` | Step runner with subprocess |
| `LlmToDevCsvCLI` | argparse |

---

## 4. Key methods

### `resolve_university_code_dir(args)`

Priority: `--code-dir` → `--university` + `/code` → `cwd`

### `run_step(label, command, cwd)`

Runs subprocess; exits on non-zero.

### `run(args)`

Checks Ollama, markdown count, then runs extract → normalize → export.

---

## 5. Flags

| Flag | Effect |
|------|--------|
| `--resume` | Pass to llm_extract |
| `--skip-extract` | Normalize + export only |
| `--presetup` | Use `pre_setup_course` markdown dir |
| `--host` | Ollama URL override |

---

## 6. Read this next

1. [llm_extract.md](llm_extract.md)
2. [features/normalize-export-flow.md](../features/normalize-export-flow.md)
3. [07-how-to-run.md](../07-how-to-run.md)
