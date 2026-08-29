# Prompt: extract course URLs from a saved university course-catalogue page

Use this prompt (fill in the bracketed parts) whenever you have a new
`scrape_course_urls.py` + `.env` setup and one or more saved HTML snapshots
of a university's course-finder / course-search page, and you want the
`COURSE_PATH_PATTERNS` regex fixed and the scraper run.

---

I have a course-URL scraper (`scrape_course_urls.py`, class-based, reads
config from `.env`) and one or more saved HTML snapshots of
[UNIVERSITY NAME]'s course catalogue: [list filenames, e.g.
"Undergraduate_courses.html", "Postgraduate_courses.html"].

The current `.env` was copied from a different university's setup, so
`COURSE_PATH_PATTERNS`, `UNIVERSITY_BASE_URL`, `EXCLUDED_COURSE_PATHS`, and
`EXCLUDED_PATH_PREFIXES` may not match this site's real URL structure —
please don't assume they're correct.

Do the following:

1. Open each saved HTML file and find the real course-detail links (not nav,
   footer, or "how to apply" links) — grep for the site's domain, look at
   `<!-- saved from url=(...) -->`, `<link rel="canonical">`, or `<base
   href>` to confirm the domain, and sample enough `<a href>` values to see
   the actual path shape course pages use (e.g. `/study/undergraduate/<slug>`
   vs `/courses/<slug>` vs `/course/<id>/<slug>`).
2. Rewrite `COURSE_PATH_PATTERNS` as a regex (or set of regexes) that matches
   only real course-detail paths for this site — anchor it (`^...$`) so it
   doesn't accidentally match listing/search/nav pages that happen to share a
   path prefix.
3. Set `UNIVERSITY_BASE_URL` to this site's actual scheme+domain.
4. Test the regex against a handful of known course paths (should match) and
   known non-course paths that have the same shape, e.g. "how-to-apply",
   "clearing", a bare `/study/undergraduate` — list any such lookalikes you
   find and add them to `EXCLUDED_COURSE_PATHS` / `EXCLUDED_PATH_PREFIXES`
   rather than trying to solve it purely with the regex.
5. Point the relevant `*_COURSE_CATALOGUE_HTML=` keys (UNDERGRADUATE /
   POSTGRADUATE / POSTGRADUATE_RESEARCH / FOUNDATION — whichever you have
   files for) at the saved HTML paths, with `STRATEGY=ALL_COURSE`, so the
   run reads from disk instead of trying to browse the live site.
6. Run `python scrape_course_urls.py --fresh` and show me `course_urls.csv`.
   Sanity-check the count and a sample of the URLs — flag anything that
   still looks like a listing/nav page rather than a course page.

---

### Why this matters (context for whoever's running it)

`COURSE_PATH_PATTERNS` is a regex whitelist: every `<a href>` on the saved
page gets normalized and checked against it, and only matches are kept. If
the regex is copied from another university it will almost always match
zero real links (silent empty output) or the wrong links (junk in the CSV) —
it needs to be derived from *this* site's actual course URLs, not assumed.