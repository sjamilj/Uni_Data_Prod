# University of Greenwich — degree-scoped ALL_COURSE catalogues (one run for all scopes)
UNIVERSITY_NAME=University of Greenwich

STRATEGY=ALL_COURSE

UNDERGRADUATE_COURSE_CATALOGUE_URL=https://www.gre.ac.uk/undergraduate-courses/a-z
# Search-page HTML uses find.gre.ac.uk redirects (not gre.ac.uk hrefs) — use A-Z URL above instead.
# UNDERGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/Search _ University of Greenwich.html

POSTGRADUATE_COURSE_CATALOGUE_URL=https://www.gre.ac.uk/postgraduate-courses/a-z
POSTGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/Postgraduate courses A - Z _ University of Greenwich, London.html

FOUNDATION_COURSE_CATALOGUE_URL=https://www.gre.ac.uk/foundation-degrees
# FOUNDATION_COURSE_CATALOGUE_HTML=

UNIVERSITY_BASE_URL=https://www.gre.ac.uk

#COURSE_LINK_SELECTOR=

COURSE_PATH_PATTERNS="
^/undergraduate-courses/[^/]+/[^/]+$
^/postgraduate-courses/[^/]+/[^/]+$
^/foundation-degrees/[^/]+(?:/[^/]+)?$
"

# --- Study-level URL split (fallback when a catalogue is not degree-scoped) ---
UNDERGRADUATE_URL_PATTERNS="
^/undergraduate\-courses(?:/|$)
(?:^|[-_/])(?:bsc|ba|beng|llb|mbchb|moptom|mpharm)(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
^/postgraduate\-courses(?:/|$)
(?:^|[-_/])(?:msc|mba|llm|pgdip|pgcert|ma)(?:[-_/]|$)
"

POSTGRADUATE_RESEARCH_URL_PATTERNS="
courses-phd
(?:^|[-_/])(?:phd|mres|engd|psychd)(?:[-_/]|$)
"

FOUNDATION_URL_PATTERNS="
^/foundation\-degrees(?:/|$)
foundation
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
"



"


"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=h1.gre-long-title

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Overview :: .gre-prog-overview
Entry requirements :: .prog-entry-requirements
Fees :: .prog-fees
Main content :: #gre-main-content
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
scholarships :: page_type:
"
