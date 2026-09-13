# Kingston University

## Route clean (undergraduate only)

Kingston has **two different foundation types**:

| Type | Examples | Route clean? |
|------|----------|--------------|
| **Standalone foundation courses** | Midwifery Foundation Year, Foundation Diploma in Art & Design | **No** — download + clean only |
| **Undergraduate courses with a foundation-year mode** | Biochemistry BSc, Interior Design BA, Cyber Security BSc | **Yes** — use the page route selector |

For **undergraduate URLs with a route selector** (Select course → Start date → Mode), presetup/execute runs `kingston_route_clean.py` automatically:

- **3 years full time** → `output/clean/pre_setup_course/undergraduate/{slug}.md`
- **4 years full time including foundation year** → `output/clean/pre_setup_course/foundation/{slug}.md`

Each route `.md` includes **Course**, **Start date**, and **Mode** (default start year: `ROUTE_START_YEAR=2027` in `code/.env`).

**Postgraduate / PGR** — no route selector; download + clean + LLM only.

**Do not** run route clean on standalone foundation catalogue URLs — they are full pages, not hub routes.

## Navigate here

```cmd
cd /d "e:\Project Next\UK UNIVERSITIES\F1\Kingston University"
```

## Subfolders

### Claude_Output

```cmd
cd /d "e:\Project Next\UK UNIVERSITIES\F1\Kingston University\Claude_Output"
```

### course_detail

```cmd
cd /d "e:\Project Next\UK UNIVERSITIES\F1\Kingston University\course_detail"
```

### course_listing

```cmd
cd /d "e:\Project Next\UK UNIVERSITIES\F1\Kingston University\course_listing"
```

### uni_req

```cmd
cd /d "e:\Project Next\UK UNIVERSITIES\F1\Kingston University\uni_req"
```
