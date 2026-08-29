UNIVERSITY_NAME=University of Huddersfield

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- DEGREE_SCOPED_PAGINATED: all programmes in one run ---
UNDERGRADUATE_COURSE_LISTING_PAGE_1=https://courses.hud.ac.uk/?searchstax[query]=*&searchstax[page]=1&searchstax[order]=searchTitle_s%20asc&searchstax[itemsPerPage]=25&searchstax[facets][0]=and:study_mode_ss:Full-time&searchstax[facets][1]=and:years_list_ss:2026-27&searchstax[facets][2]=and:start_dates_range_list_ss:January%20-%20April&searchstax[facets][3]=and:start_dates_range_list_ss:September%20-%20December&searchstax[model]=Coursefinder
UNDERGRADUATE_COURSE_LISTING_PAGE_2=https://courses.hud.ac.uk/?searchstax[query]=*&searchstax[page]=2&searchstax[order]=searchTitle_s%20asc&searchstax[itemsPerPage]=25&searchstax[facets][0]=and:study_mode_ss:Full-time&searchstax[facets][1]=and:years_list_ss:2026-27&searchstax[facets][2]=and:start_dates_range_list_ss:January%20-%20April&searchstax[facets][3]=and:start_dates_range_list_ss:September%20-%20December&searchstax[model]=Coursefinder

# POSTGRADUATE_COURSE_LISTING_PAGE_1=https://www.canterbury.ac.uk/search/postgraduate-taught-courses?pageIndex=1
# POSTGRADUATE_COURSE_LISTING_PAGE_2=https://www.canterbury.ac.uk/search/postgraduate-taught-courses?pageIndex=2

# FOUNDATION_COURSE_LISTING_PAGE_1=https://www.canterbury.ac.uk/search/foundation-year?pageIndex=1
# FOUNDATION_COURSE_LISTING_PAGE_2=https://www.canterbury.ac.uk/search/foundation-year?pageIndex=2

# Legacy single-programme keys (optional fallback if degree-scoped keys are omitted):
# LISTING_PROGRAMME=undergraduate
# COURSE_LISTING_PAGE_1=https://www.canterbury.ac.uk/search/undergraduate-courses?pageIndex=1
# COURSE_LISTING_PAGE_2=https://www.canterbury.ac.uk/search/undergraduate-courses?pageIndex=2

# --- ALL_COURSE: degree-scoped saved catalogues (one run for all scopes) ---
# STRATEGY=ALL_COURSE
# UNDERGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/undergraduate.html
# POSTGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/postgraduate.html
# FOUNDATION_COURSE_CATALOGUE_HTML=../course_listing/foundation.html

# Legacy single catalogue (ALL_COURSE):
# COURSE_CATALOGUE_URL=
# COURSE_CATALOGUE_HTML=

UNIVERSITY_BASE_URL=https://courses.hud.ac.uk

# Optional CSS selector — only scan these anchors (leave blank = all <a href>)
#COURSE_LINK_SELECTOR=

# Huddersfield course pages on courses.hud.ac.uk: /2026-27/undergraduate/<slug>, etc.
COURSE_PATH_PATTERNS="
^/\d{4}-\d{2}/(?:undergraduate|postgraduate|distance-learning)/[a-z0-9][a-z0-9-]*$
"

# --- Study-level URL split (fallback when a catalogue is not degree-scoped) ---
UNDERGRADUATE_URL_PATTERNS="
^/2026\-27/undergraduate(?:/|$)
(?:^|[-_/])(?:bsc|ba|beng|llb|mbchb|moptom|mpharm)(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
^/2026\-27/postgraduate(?:/|$)
(?:^|[-_/])(?:msc|mba|llm|pgdip|pgcert|ma)(?:[-_/]|$)
"

POSTGRADUATE_RESEARCH_URL_PATTERNS="
courses-phd
(?:^|[-_/])(?:phd|mres|engd|psychd)(?:[-_/]|$)
"

FOUNDATION_URL_PATTERNS="
foundation
"

EXCLUDED_COURSE_PATHS="
/
"

EXCLUDED_PATH_PREFIXES="
/clearing/
/international/
/current-students/
/alumni
/information/
/about/
/research/
/news/
/events/
"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=.coursefinder-course-overview h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Overview :: .coursefinder-course-overview
Entry requirements :: #section-entry-requirements
Fees and finance :: #section-fees-and-finance
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
.coursefinder-accordion-btn
#accred
.content-tabs__nav
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
bangladesh-entry :: https://www.hud.ac.uk/international/courses-and-entry-requirements/international-entry-requirements/
english-requirements :: page_type:
scholarships :: https://www.hud.ac.uk/lorem/lauren-bolton/builds/international-draft/scholarships/
"
