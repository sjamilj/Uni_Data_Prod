# UK Uni Data

Pipeline for scraping UK university course pages, cleaning HTML to markdown, and extracting international admission requirements (entry, English, scholarships, deposits).

See [PIPELINE.md](PIPELINE.md) for the full workflow and [CONTRIBUTING.md](CONTRIBUTING.md) for git commit scopes (`feat(unit-03/bcu): ...`) so you can find each university later. Unit numbers live in [UNIVERSITIES_REGISTRY.md](UNIVERSITIES_REGISTRY.md).

## Working with the agent

Cursor skills in `.cursor/skills/` guide onboarding a new university. You do not need command-line flags or file paths in chat — name the university and say what you want.

| You want to… | Say something like… |
|--------------|---------------------|
| Start a brand-new university (resets shared code) | **use new-uni-setup for** *University Name* |
| See the full step order | **use uni-pipeline** |
| Get the list of course links from saved listing pages | **find the course links for** *University Name* |
| Course link list is empty or wrong | **the course link search found nothing** (or describe what looks wrong) |
| Site shows a robot / human check | **it says verifying you are human** |
| Cleaned course pages missing fee, start date, or length | **the cleaned course pages have no fee or duration** |
| Give entry, English, scholarship, or deposit info | **here is the Bangladesh entry info for** *University Name* — then paste the text |
| Download and clean a small trial set | **run the 5-course test for** *University Name* |
| Run AI extraction on that trial set | **run the LLM on the 5 test courses** |

**Rules of thumb**

- Always name the university; the agent will not guess which folder you mean.
- Paste information exactly as you copied it — no need to format it first.
- If a result looks wrong, name the field (“the fee is empty”, “the intake is missing the year”) so the agent knows which step to revisit.
- Only **new-uni-setup** and **uni-pipeline** need the skill name in your message; other steps work from normal conversation.
- **Git:** you run all `git` commands yourself. The agent gives separate copy-paste blocks and **always suggests a concrete commit message and tag message** (you can edit before `-m`). No chained `commit` + `tag` in one line; no `Co-authored-by` unless you ask. See `.cursor/skills/git-for-operator.md`.

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

## Learning the codebase

Start at [docs/00-start-here.md](docs/00-start-here.md) for a guided path through architecture, feature flows, and per-module docs for `shared/` and `dashboard/`.
