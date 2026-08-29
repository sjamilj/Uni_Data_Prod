# UK Uni Data

Pipeline for scraping UK university course pages, cleaning HTML to markdown, and extracting international admission requirements (entry, English, scholarships, deposits).

See [PIPELINE.md](PIPELINE.md) for the full workflow and [CONTRIBUTING.md](CONTRIBUTING.md) for git commit scopes (`feat(unit-03/bcu): ...`) so you can find each university later. Unit numbers live in [UNIVERSITIES_REGISTRY.md](UNIVERSITIES_REGISTRY.md).

## HTML clean engines (implemented)

`COURSE_CLEAN_ENGINE` in `code/.env` selects how HTML blocks become markdown:

| Engine | Module | When |
|--------|--------|------|
| `generic` (default) | `shared/engines/generic.py` | Most universities |
| `utopian` | `shared/engines/utopian.py` | ARU (Utopian CMS) |
| `plugin` | `{University}/code/course_html_builder.py` | Custom CMS hooks (optional) |

ARU sets `COURSE_CLEAN_ENGINE=utopian` in `.env`. Other unis omit it or use `generic`.

Supporting modules: `shared/markdown_converter.py`, `shared/clean_config.py`. `CourseMarkdownBuilder` in `shared/download_and_clean_course_pages.py` dispatches to the engine — generic unis no longer run Utopian code.

Markdown cleanup (after HTML→MD) stays in `shared/course_markdown_cleanup.py` + optional `{University}/code/course_markdown_cleanup.py`.

See also [shared/course_markdown_cleanup.md](shared/course_markdown_cleanup.md).
