# Shared pipeline — code documentation index

Level 3 deep dives for `shared/` modules. Start with [00-start-here.md](../00-start-here.md) if you are new.

---

## Tier 1 — Read first (orchestration)

| Doc | Module | Lines | Role |
|-----|--------|-------|------|
| [uni_paths.md](uni_paths.md) | `uni_paths.py` | ~35 | `code/` vs `output/` resolution |
| [run_course_pipeline.md](run_course_pipeline.md) | `run_course_pipeline.py` | ~460 | Presetup + Execute |
| [pipeline_status.md](pipeline_status.md) | `pipeline_status.py` | ~310 | Dashboard status scan |

---

## Tier 2 — Pipeline phases

| Doc | Module | Role |
|-----|--------|------|
| [scrape_course_urls.md](scrape_course_urls.md) | `scrape_course_urls.py` | URL discovery |
| [download_and_clean_course_pages.md](download_and_clean_course_pages.md) | `download_and_clean_course_pages.py` | HTML → markdown |
| [llm_extract.md](llm_extract.md) | `llm_extract.py` | Ollama extraction |
| [normalize_admission_data.md](normalize_admission_data.md) | `normalize_admission_data.py` | Schema normalization |
| [export_dev_courses.md](export_dev_courses.md) | `export_dev_courses.py` | CSV export |

---

## Tier 3 — Supporting modules

| Doc | Module | Role |
|-----|--------|------|
| [study_level.md](study_level.md) | `study_level.py` | Level classification, presetup sample |
| [course_markdown_cleanup.md](course_markdown_cleanup.md) | `course_markdown_cleanup.py` | Post-MD section removal |
| [engines.md](engines.md) | `engines/` | generic vs utopian HTML clean |
| [build_env.md](build_env.md) | `build_env.py` | Merge `env/*.env` fragments |
| [run_llm_to_dev_csv.md](run_llm_to_dev_csv.md) | `run_llm_to_dev_csv.py` | LLM → normalize → CSV chain |
| [validate_uni_clean.md](validate_uni_clean.md) | `validate_uni_clean.py` | Uni MD validation |
| [validate_dev_courses.md](validate_dev_courses.md) | `validate_dev_courses.py` | CSV validation |

---

## Tier 4 — Short reference (no full doc)

| Module | Purpose |
|--------|---------|
| `ollama_client.py` | HTTP wrapper for Ollama chat API |
| `clean_config.py` | `CleanConfig` dataclass from `.env` keys |
| `uni_pages.py` | Slug from URL, frontmatter parsing |
| `course_type_filter.py` | Filter URLs by course type patterns |
| `portable_paths.py` | Cross-platform path helpers |
| `markdown_converter.py` | HTML fragment → markdown utilities |
| `programme_name_dictionary.py` | Programme name canonicalization |
| `bootstrap_university.py` | Scaffold new university folder |
| `scaffold_uni_clean_config.py` | Apply clean profiles to ENV.MD |
| `analyze_catalogue_html.py` | Debug tool for saved listing HTML |
| `extra_clean_courses.py` | Per-uni extra markdown rules runner |
| `export_portal_courses.py` | Portal CSV export variant |
| `retrofit_study_level_split.py` | Migrate flat extracted/ to level folders |
| `retrofit_intake_year_split.py` | Migrate intake year folder layout |
| `rerun_entry_requirements.py` | Re-run Stage 2 entry for existing slugs |
| `run_all_download_clean.py` | Batch download/clean all universities |

---

## Feature flows (Level 2)

| Flow | Doc |
|------|-----|
| Scrape URLs | [features/scrape-urls-flow.md](../features/scrape-urls-flow.md) |
| Download + clean | [features/download-clean-flow.md](../features/download-clean-flow.md) |
| Presetup + Execute | [features/presetup-and-execute-flow.md](../features/presetup-and-execute-flow.md) |
| LLM extraction | [features/llm-extraction-flow.md](../features/llm-extraction-flow.md) |
| Normalize + export | [features/normalize-export-flow.md](../features/normalize-export-flow.md) |

---

## Recommended read order (code track)

1. `uni_paths.md`
2. `scrape_course_urls.md` OR `download_and_clean_course_pages.md`
3. `run_course_pipeline.md`
4. `llm_extract.md`
5. `normalize_admission_data.md`

---

## Tests

`shared/test_entry_requirements.py` — run with `python -m unittest shared.test_entry_requirements -q`
