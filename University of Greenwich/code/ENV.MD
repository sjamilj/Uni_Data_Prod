# University of Greenwich — degree-scoped ALL_COURSE catalogues (DegreeScopedALLCourse.csv)
UNIVERSITY_NAME=University of Greenwich

STRATEGY=ALL_COURSE

# --- ALL_COURSE: one catalogue URL/HTML pair per programme ---
# UG A-Z is live until you save the listing. Do not use course_listing/Search _ University of Greenwich.html
# (find.gre.ac.uk redirects, not gre.ac.uk course hrefs).
UNDERGRADUATE_COURSE_CATALOGUE_URL=https://www.gre.ac.uk/undergraduate-courses/a-z
# UNDERGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/undergraduate.html

POSTGRADUATE_COURSE_CATALOGUE_URL=https://www.gre.ac.uk/postgraduate-courses/a-z
POSTGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/Postgraduate courses A - Z _ University of Greenwich, London.html

# No separate PGR catalogue in DegreeScopedALLCourse.csv — MPhil/PhD sit on the PG A-Z page.
# POSTGRADUATE_RESEARCH_COURSE_CATALOGUE_URL=
# POSTGRADUATE_RESEARCH_COURSE_CATALOGUE_HTML=

# Foundation listing is gre.ac.uk/foundation-degrees (FdSc / partner colleges). Save HTML when ready.
FOUNDATION_COURSE_CATALOGUE_URL=https://www.gre.ac.uk/foundation-degrees
# FOUNDATION_COURSE_CATALOGUE_HTML=../course_listing/foundation.html

UNIVERSITY_BASE_URL=https://www.gre.ac.uk

# Optional — only scan matching anchors (blank = all <a href>)
#COURSE_LINK_SELECTOR=

# Sample paths: /undergraduate-courses/business-school/business-management-ba-hons
#               /postgraduate-courses/engsci/computing-and-information-systems-msc
COURSE_PATH_PATTERNS="
^/undergraduate-courses/[^/]+/[^/]+$
^/postgraduate-courses/[^/]+/[^/]+$
^/foundation-degrees/[^/]+(?:/[^/]+)?$
"

# --- Study-level URL split (fallback when a catalogue is not degree-scoped) ---
UNDERGRADUATE_URL_PATTERNS="
^/undergraduate\-courses(?:/|$)
(?:^|[-_/])(?:bsc|ba|beng|llb|mbchb|moptom|mpharm|fdsc|fda)(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
^/postgraduate\-courses(?:/|$)
(?:^|[-_/])(?:msc|mba|llm|pgdip|pgcert|ma|march)(?:[-_/]|$)
"

POSTGRADUATE_RESEARCH_URL_PATTERNS="
mphilphd
(?:^|[-_/])(?:phd|mres|engd|psychd|mphil)(?:[-_/]|$)
"

FOUNDATION_URL_PATTERNS="
^/foundation\-degrees(?:/|$)
foundation
(?:^|[-_/])(?:fdsc|fda)(?:[-_/]|$)
"

EXCLUDED_COURSE_PATHS="
/undergraduate-courses/a-z
/postgraduate-courses/a-z
/foundation-degrees
"

EXCLUDED_PATH_PREFIXES="
/international/
/current-students/
/alumni
/information/
/about/
/research/
/news/
/events/
/online
"

# Skip online / distance / part-time / sandwich at download/clean (they can still appear in course_urls.csv).
# Greenwich PT-only pages often have no part-time slug; #prog-mode "1 year part-time" is excluded
# via COURSE_EXCLUDE_COURSE_TYPES (dual-mode FT+PT pages are kept).
# Sandwich-only duration ("2 years sandwich") and *industrial-practice* URLs are discarded.
# Pages with "Available to overseas students? No" are always discarded at clean.
COURSE_EXCLUDE_URL_PATTERNS="
*/online-*
*online*
*distance-learning*
*distance*
*part-time*
*parttime*
*sandwich*
*industrial-practice*
"

COURSE_EXCLUDE_COURSE_TYPES="
*part-time*
*distance learning*
*online*
*sandwich*
"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=h1.gre-long-title

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
# Key facts are built in course_markdown_cleanup.py (international FT only).
COURSE_CLEAN_BLOCKS="
 :: #gre-clean-facts
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
nav
.prog-country-entry-requirements select
"

COURSE_CLEAN_EXPAND_TABS=true

# --- Course markdown cleanup (shared/course_markdown_cleanup.py) ---
COURSE_MARKDOWN_REMOVE_SECTIONS="
2 :: Latest news
2 :: Be part of our community
2 :: Alumni services
2 :: *Read more news*
4 :: With placement
4 :: With foundation year
4 :: Important additional notes
4 :: *part-time*
3 :: UK students
3 :: Contextual offers
3 :: Living costs
5 :: UK students*
5 :: *part-time*
"

UNI_REQ_SOURCE_URLS="
bangladesh-entry :: https://www.gre.ac.uk/international/countries/bangladesh
english-requirements :: https://www.gre.ac.uk/international/support-and-help/courses
scholarships ::
deposit ::
"
