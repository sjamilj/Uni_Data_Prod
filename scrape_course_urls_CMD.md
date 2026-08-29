# scrape_course_urls.py — CMD commands (this PC)

**Run from the cloned repo root** (any PC)  
**Shell:** Command Prompt (`cmd`)  
**Script:** `shared\scrape_course_urls.py`  
**Config:** `{University}\code\.env`

Run these from the repo root. Paths are relative, not machine-specific.

| Flag | Purpose |
|---|---|
| *(none)* | Resume — skip URLs already in progress |
| `--fresh` | Clear progress and re-extract URLs |
| `--append-urls` | Keep existing `course_urls.csv` and merge new URLs |

**Outputs (in `{University}\output\`):** `course_urls.csv`, `course_listing_pages\`, `scrape_progress.json`, `scrape.log`

---

## Per university (`--fresh`)

### Anglia Ruskin University - ARU

```cmd
python shared/scrape_course_urls.py --code-dir "Anglia Ruskin University - ARU\code" --fresh
```

### Aston University

```cmd
python shared/scrape_course_urls.py --code-dir "Aston University\code" --fresh
```

### Birmingham City University

```cmd
python shared/scrape_course_urls.py --code-dir "Birmingham City University\code" --fresh
```

### Brunel University London

```cmd
python shared/scrape_course_urls.py --code-dir "Brunel University London\code" --fresh
```

### Buckinghamshire New University

```cmd
python shared/scrape_course_urls.py --code-dir "Buckinghamshire New University\code" --fresh
```

### Canterbury Christ Church University

```cmd
python shared/scrape_course_urls.py --code-dir "Canterbury Christ Church University\code" --fresh
```

### Cardiff Metropolitan University

```cmd
python shared/scrape_course_urls.py --code-dir "Cardiff Metropolitan University\code" --fresh
```

### Edinburgh Napier University

```cmd
python shared/scrape_course_urls.py --code-dir "Edinburgh Napier University\code" --fresh
```

### Keele University

```cmd
python shared/scrape_course_urls.py --code-dir "Keele University\code" --fresh
```

### Kingston University

```cmd
python shared/scrape_course_urls.py --code-dir "Kingston University\code" --fresh
```

### London South Bank University

```cmd
python shared/scrape_course_urls.py --code-dir "London South Bank University\code" --fresh
```

### Ravensbourne University London

```cmd
python shared/scrape_course_urls.py --code-dir "Ravensbourne University London\code" --fresh
```

### Teesside University

```cmd
python shared/scrape_course_urls.py --code-dir "Teesside University\code" --fresh
```

### University of Birmingham

```cmd
python shared/scrape_course_urls.py --code-dir "University of Birmingham\code" --fresh
```

### University of Derby

```cmd
python shared/scrape_course_urls.py --code-dir "University of Derby\code" --fresh
```

### University of East London

```cmd
python shared/scrape_course_urls.py --code-dir "University of East London\code" --fresh
```

### University of Essex

```cmd
python shared/scrape_course_urls.py --code-dir "University of Essex\code" --fresh
```

### University of Greenwich

```cmd
python shared/scrape_course_urls.py --code-dir "University of Greenwich\code" --fresh
```

### University of Huddersfield

```cmd
python shared/scrape_course_urls.py --code-dir "University of Huddersfield\code" --fresh
```

### University of Hull

```cmd
python shared/scrape_course_urls.py --code-dir "University of Hull\code" --fresh
```

### University of Law

```cmd
python shared/scrape_course_urls.py --code-dir "University of Law\code" --fresh
```

### University of Roehampton

```cmd
python shared/scrape_course_urls.py --code-dir "University of Roehampton\code" --fresh
```

### University of Salford

```cmd
python shared/scrape_course_urls.py --code-dir "University of Salford\code" --fresh
```

### University of South Wales

```cmd
python shared/scrape_course_urls.py --code-dir "University of South Wales\code" --fresh
```

### University of Suffolk

```cmd
python shared/scrape_course_urls.py --code-dir "University of Suffolk\code" --fresh
```

### University of Surrey

```cmd
python shared/scrape_course_urls.py --code-dir "University of Surrey\code" --fresh
```

### University of Wales Trinity Saint David

```cmd
python shared/scrape_course_urls.py --code-dir "University of Wales Trinity Saint David\code" --fresh
```

### University of West London

```cmd
python shared/scrape_course_urls.py --code-dir "University of West London\code" --fresh
```

### University of Winchester

```cmd
python shared/scrape_course_urls.py --code-dir "University of Winchester\code" --fresh
```

---

## Resume / append

Drop `--fresh` to resume. Add `--append-urls` to merge into an existing `course_urls.csv`.

Example — ARU resume:

```cmd
python shared/scrape_course_urls.py --code-dir "Anglia Ruskin University - ARU\code"
```

Example — ARU append:

```cmd
python shared/scrape_course_urls.py --code-dir "Anglia Ruskin University - ARU\code" --append-urls
```

---

## From repo root (relative paths)

```cmd
cd /d "{repo-root}"
python "shared\scrape_course_urls.py" --code-dir "Anglia Ruskin University - ARU\code" --fresh
```

Replace the university folder name for others.

---

## .env strategies (per uni)

| STRATEGY | Set in `.env` when |
|---|---|
| `ALL_COURSE` | Single or degree-scoped catalogue (`*_COURSE_CATALOGUE_URL` / `_HTML`) |
| `DEGREE_SCOPED_PAGINATED` | Paginated search listings (`*_COURSE_LISTING_PAGE_1`, `_PAGE_2`, …) |

Edit `code\.env` before running; the script is the same for every university.
