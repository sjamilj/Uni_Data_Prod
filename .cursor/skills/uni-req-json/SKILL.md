---
name: uni-req-json
description: >-
  clean/uni bangladesh-entry, english-requirements, scholarships, deposit (markdown + JSON)
  from pasted requirement text. Use when user pastes Bangladesh entry, English requirements,
  scholarships, deposit, uni_req, or asks for requirement JSON manual help.
---

# Uni requirement JSON (manual help)

Git: [git-for-operator.md](../git-for-operator.md).

## Trigger

User pastes entry, English, scholarship, or deposit information and asks for JSON / clean uni files.

## Outputs

Write or update under `{University}/output/clean/uni/`:

| File | Role |
|------|------|
| `bangladesh-entry.md` | Country/academic entry by study level |
| `english-requirements.md` | IELTS/PTE/TOEFL by programme |
| `scholarships.md` | International scholarships |
| `deposit.md` | Tuition fee deposit |

Schemas and examples: [formats.md](formats.md).

## Steps

1. Confirm `UNIVERSITY_NAME` matches the folder.
2. Use frontmatter from formats.md; set `source_url` from `uni_req/*.html` or the URL the user gives.
3. Convert pasted text into JSON — no invented grades, fees, or scores.
4. Mirror requirement URLs in `UNI_REQ_SOURCE_URLS` in `code/.env` and `code/ENV.MD` if needed.

## Re-clean from HTML (optional)

If `uni_req/*.html` exists:

```powershell
python shared/download_and_clean_course_pages.py --code-dir "{University}/code" --clean-uni-only
```

Then merge/override JSON sections if the auto-clean left prose instead of structured JSON.

## Next

**uni-presetup** after course URLs and course clean are in good shape.
