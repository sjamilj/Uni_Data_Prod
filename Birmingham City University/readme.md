# Birmingham City University

## Navigate here

```cmd
cd /d "e:\Project Next\UK UNIVERSITIES\F1\Birmingham City University"
```

## Subfolders

### Claude_Output

```cmd
cd /d "e:\Project Next\UK UNIVERSITIES\F1\Birmingham City University\Claude_Output"
```

### course_detail

```cmd
cd /d "e:\Project Next\UK UNIVERSITIES\F1\Birmingham City University\course_detail"
```

### course_listing

```cmd
cd /d "e:\Project Next\UK UNIVERSITIES\F1\Birmingham City University\course_listing"
```

### uni_req

```cmd
cd /d "e:\Project Next\UK UNIVERSITIES\F1\Birmingham City University\uni_req"
```

## Re-run entry requirements (merge-only)

From the repo root (`F1`), refresh Bangladesh entry requirements and `normalized.json` without calling the LLM:

```cmd
cd /d "e:\Project Next\UK UNIVERSITIES\F1"
python shared/rerun_entry_requirements.py "Birmingham City University/code" --merge-only --normalize
```

Requires existing `output/extracted/{study_level}/{slug}/stage1_parsed.json` per course (run full `llm_extract` first if missing).
