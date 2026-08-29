# download_and_clean_course_pages.py — CMD commands (this PC)

**Run from the cloned repo root** (any PC)  
**Shell:** Command Prompt (`cmd`)  
**Script:** `shared\download_and_clean_course_pages.py`  
**Config:** `{University}\code\.env`  
**Prerequisite:** `output\course_urls.csv` from `scrape_course_urls.py`

Run these from the repo root. Paths are relative, not machine-specific.

Default (no flags) = resume download of missing HTML, then clean **course** pages to markdown.

| Flag | Purpose |
|---|---|
| *(none)* | Resume download + clean courses |
| `--fresh` | Re-download all URLs (clears download progress) |
| `--limit N` | First N URLs only (download and/or clean, for testing) |
| `--download-only` | Download HTML only; skip cleaning |
| `--clean-only` | Re-clean existing course HTML; skip download and uni_req |
| `--clean-uni-only` | Clean `uni_req/` HTML only |
| `--clean-all` | Clean courses **and** uni_req; skip download |

`--clean-only`, `--clean-uni-only`, and `--clean-all` are mutually exclusive. Do not combine any of them with `--download-only`.

**Outputs (in `{University}\output\`):** `course_pages\`, `course_page_map.csv`, `failed_urls.csv`, `clean_warnings.csv`, `clean\courses\`, `clean\uni\`, `clean\manifest.json`, `scrape_progress.json`, `scrape.log`

---

## Per university (download + clean)

### Anglia Ruskin University - ARU

```cmd
python shared/download_and_clean_course_pages.py --code-dir "Anglia Ruskin University - ARU\code"
```

### Aston University

```cmd
python shared/download_and_clean_course_pages.py --code-dir "Aston University\code"
```

### Birmingham City University

```cmd
python shared/download_and_clean_course_pages.py --code-dir "Birmingham City University\code"
```

### Brunel University London

```cmd
python shared/download_and_clean_course_pages.py --code-dir "Brunel University London\code"
```

### Buckinghamshire New University

```cmd
python shared/download_and_clean_course_pages.py --code-dir "Buckinghamshire New University\code"
```

### Canterbury Christ Church University

```cmd
python shared/download_and_clean_course_pages.py --code-dir "Canterbury Christ Church University\code"
```

### Cardiff Metropolitan University

```cmd
python shared/download_and_clean_course_pages.py --code-dir "Cardiff Metropolitan University\code"
```

### Edinburgh Napier University

```cmd
python shared/download_and_clean_course_pages.py --code-dir "Edinburgh Napier University\code"
```

### Keele University

```cmd
python shared/download_and_clean_course_pages.py --code-dir "Keele University\code"
```

### Kingston University

```cmd
python shared/download_and_clean_course_pages.py --code-dir "Kingston University\code"
```

### London South Bank University

```cmd
python shared/download_and_clean_course_pages.py --code-dir "London South Bank University\code"
```

### Ravensbourne University London

```cmd
python shared/download_and_clean_course_pages.py --code-dir "Ravensbourne University London\code"
```

### Teesside University

```cmd
python shared/download_and_clean_course_pages.py --code-dir "Teesside University\code"
```

### University of Birmingham

```cmd
python shared/download_and_clean_course_pages.py --code-dir "University of Birmingham\code"
```

### University of Derby

```cmd
python shared/download_and_clean_course_pages.py --code-dir "University of Derby\code"
```

### University of East London

```cmd
python shared/download_and_clean_course_pages.py --code-dir "University of East London\code"
```

### University of Essex

```cmd
python shared/download_and_clean_course_pages.py --code-dir "University of Essex\code"
```

### University of Greenwich

```cmd
python shared/download_and_clean_course_pages.py --code-dir "University of Greenwich\code"
```

### University of Huddersfield

```cmd
python shared/download_and_clean_course_pages.py --code-dir "University of Huddersfield\code"
```

### University of Hull

```cmd
python shared/download_and_clean_course_pages.py --code-dir "University of Hull\code"
```

### University of Law

```cmd
python shared/download_and_clean_course_pages.py --code-dir "University of Law\code"
```

### University of Roehampton

```cmd
python shared/download_and_clean_course_pages.py --code-dir "University of Roehampton\code"
```

### University of Salford

```cmd
python shared/download_and_clean_course_pages.py --code-dir "University of Salford\code"
```

### University of South Wales

```cmd
python shared/download_and_clean_course_pages.py --code-dir "University of South Wales\code"
```

### University of Suffolk

```cmd
python shared/download_and_clean_course_pages.py --code-dir "University of Suffolk\code"
```

### University of Surrey

```cmd
python shared/download_and_clean_course_pages.py --code-dir "University of Surrey\code"
```

### University of Wales Trinity Saint David

```cmd
python shared/download_and_clean_course_pages.py --code-dir "University of Wales Trinity Saint David\code"
```

### University of West London

```cmd
python shared/download_and_clean_course_pages.py --code-dir "University of West London\code"
```

### University of Winchester

```cmd
python shared/download_and_clean_course_pages.py --code-dir "University of Winchester\code"
```

---

## Fresh / download-only / clean

Add `--fresh` to re-download every URL. Add `--download-only` to skip markdown. Use a clean flag when HTML is already on disk.

Example — ARU re-download + clean:

```cmd
python shared/download_and_clean_course_pages.py --code-dir "Anglia Ruskin University - ARU\code" --fresh
```

Example — ARU download HTML only:

```cmd
python shared/download_and_clean_course_pages.py --code-dir "Anglia Ruskin University - ARU\code" --download-only
```

Example — ARU re-clean existing course HTML:

```cmd
python shared/download_and_clean_course_pages.py --code-dir "Anglia Ruskin University - ARU\code" --clean-only
```

Example — ARU uni_req pages only:

```cmd
python shared/download_and_clean_course_pages.py --code-dir "Anglia Ruskin University - ARU\code" --clean-uni-only
```

Example — ARU clean courses + uni_req (no download):

```cmd
python shared/download_and_clean_course_pages.py --code-dir "Anglia Ruskin University - ARU\code" --clean-all
```

Example — ARU test first 5 URLs:

```cmd
python shared/download_and_clean_course_pages.py --code-dir "Anglia Ruskin University - ARU\code" --limit 5
```

---

## From repo root (relative paths)

```cmd
cd /d "{repo-root}"
python "shared\download_and_clean_course_pages.py" --code-dir "Anglia Ruskin University - ARU\code"
```

Replace the university folder name for others.

---

## .env (per uni)

| Key | Set in `.env` when |
|---|---|
| `COURSE_CLEAN_ENGINE` | HTML layout: `generic` \| `utopian` \| `plugin` |
| `COURSE_CLEAN_BLOCKS` | Section heading + CSS selector pairs |
| `COURSE_PAGE_TITLE_SELECTOR` | Course title on the page |
| `COURSE_CLEAN_STRIP_WITHIN` | Tags/classes to strip inside blocks |

Edit `code\.env` before running; the script is the same for every university.
