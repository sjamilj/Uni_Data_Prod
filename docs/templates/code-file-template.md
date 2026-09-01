# {module_name}.py

> Copy this template when adding a new Level 3 code doc under `docs/shared/` or `docs/dashboard/`.

## 1. Purpose

What business problem does this file solve? List main responsibilities as bullets — not a directory listing.

---

## 2. Where this file is used

Who calls it?

```
CallerA
  → ThisModule
  → DependencyB
  → Disk artifact
```

| Caller | How |
|--------|-----|
| `other_module.py` | `SomeClass.method()` |

---

## 3. Dependencies

| Dependency | Why |
|------------|-----|
| `pathlib.Path` | Resolve university folders |
| Playwright / Ollama | (if applicable) |

---

## 4. Main classes / entry points

### `ClassName`

One paragraph: what the class owns.

### `main()` / CLI

How the script is invoked from the command line.

---

## 5. Key methods

### `method_name(arg1, arg2)`

**Purpose:** …

**Input:** …

**Process:**

1. …
2. …

**Simplified flow:**

```
method_name()
  → step A
  → step B?
      ├── No → return
  → step C
```

---

## 6. Important code

```python
# snippet
```

**What happens here?** Explain the line, not just what it syntactically does.

**Why `await` / why a class / why JSON checkpoint?** Connect to design.

---

## 7. Why it was written this way

Design trade-offs: resume files, `--code-dir`, class wrappers with module aliases, etc.

---

## 8. Artifacts read / written

| Path (under `{University}/output/`) | When |
|-------------------------------------|------|
| `course_urls.csv` | After URL scrape |

---

## 9. Prerequisites

Before modifying this file, understand:

1. …
2. …

---

## 10. Read this next

1. [related-module.md](../shared/related-module.md)
2. [feature-flow.md](../features/feature-flow.md)
3. Operational runbook: [PIPELINE.md](../../PIPELINE.md)
