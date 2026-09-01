# build_env.py

## 1. Purpose

Merges `code/env/*.env` fragment files into `code/.env` and `code/ENV.MD`.

Enables splitting foundation vs common config without duplicating entire env files.

---

## 2. Where this file is used

```powershell
python shared/build_env.py --code-dir "Anglia Ruskin University - ARU/code"
python shared/build_env.py --all
```

Also referenced by `Create-EnvFiles.ps1` fallback behaviour.

---

## 3. Main class: `EnvFragmentMerger`

| Method | Role |
|--------|------|
| `fragment_paths()` | Ordered list: `common.env`, `foundation.env`, … |
| `merge_text()` | Join fragments with blank lines |
| `build()` | Write `.env` and/or `ENV.MD` |

---

## 4. Fragment order

```python
FRAGMENT_ORDER = (
    "common.env",
    "foundation.env",
    "undergraduate.env",
    "postgraduate.env",
    "postgraduate_research.env",
)
```

Later files override keys from earlier files if duplicated (by concatenation — last wins in env parser depending on load order; fragments should not duplicate keys).

---

## 5. Fallback

If `code/env/common.env` missing:

- Copy `ENV.MD` → `.env` (legacy universities)

---

## 6. Why it was written this way

ARU foundation listings differ from UG but share clean config — `foundation.env` holds only `FOUNDATION_*` keys. Operators edit small files instead of 130-line monolith.

---

## 7. Artifacts

| File | Git |
|------|-----|
| `code/.env` | No |
| `code/ENV.MD` | Yes (optional sync) |
| `code/env/*.env` | Yes |

---

## 8. Read this next

1. [05-env-and-config.md](../05-env-and-config.md)
2. ARU `code/env/` example
