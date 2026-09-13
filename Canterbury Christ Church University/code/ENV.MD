UNIVERSITY_NAME=Canterbury Christ Church University

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- DEGREE_SCOPED_PAGINATED: all programmes in one run ---
UNDERGRADUATE_COURSE_LISTING_PAGE_1=https://www.canterbury.ac.uk/search/undergraduate-courses?pageIndex=1
UNDERGRADUATE_COURSE_LISTING_PAGE_2=https://www.canterbury.ac.uk/search/undergraduate-courses?pageIndex=2

POSTGRADUATE_COURSE_LISTING_PAGE_1=https://www.canterbury.ac.uk/search/postgraduate-taught-courses?pageIndex=1
POSTGRADUATE_COURSE_LISTING_PAGE_2=https://www.canterbury.ac.uk/search/postgraduate-taught-courses?pageIndex=2

FOUNDATION_COURSE_LISTING_PAGE_1=https://www.canterbury.ac.uk/search/foundation-year?pageIndex=1
FOUNDATION_COURSE_LISTING_PAGE_2=https://www.canterbury.ac.uk/search/foundation-year?pageIndex=2

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

UNIVERSITY_BASE_URL=https://www.canterbury.ac.uk
# Optional CSS selector — only scan these anchors (leave blank = all <a href>)
#COURSE_LINK_SELECTOR=

# CCCU course page paths under /study-here/courses/
COURSE_PATH_PATTERNS="
^/study-here/courses/[a-z0-9][a-z0-9\-]+(?:/[a-z0-9][a-z0-9\-]+)?$
"

# --- Study-level URL split (fallback when a catalogue is not degree-scoped) ---
UNDERGRADUATE_URL_PATTERNS="
(?:^|[-_/])(?:bsc|ba|beng|llb|mbchb|moptom|mpharm)(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
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
/study-here/courses
/study-here
/courses/a-to-z-listing
/courses/search
"

EXCLUDED_PATH_PREFIXES="
/bookmarked-courses
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

# --- Course page download (shared/scrape_course_urls.py) ---
# course_download_hooks.py clicks the International tab before HTML save.

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=main h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
# Omits course-page marketing prose (Course overview); keep entry, fees only.
# Key course information is injected from `.course-details-banner` in course_markdown_cleanup.py.
COURSE_CLEAN_BLOCKS="
Entry requirements :: #courseEntryRequirements
Fees :: #courseFees
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
#courseRelatedCourses
.related-courses
.carousel-root
"

COURSE_CLEAN_EXPAND_TABS=true

# Skip part-time courses at download/clean and LLM (--presetup-llm / --execute).
# Matches Course type fields and Key course information **Mode:** (e.g. Part-time).
COURSE_EXCLUDE_COURSE_TYPES="
*part-time*
"

# --- Course markdown cleanup (shared/course_markdown_cleanup.py) ---
COURSE_MARKDOWN_REMOVE_SECTIONS="
2 :: Course overview
2 :: Choose your country
2 :: *meet these entry requirements*
2 :: Modules
2 :: Module information
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
bangladesh-entry :: https://www.canterbury.ac.uk/study-here/international/find-your-country/bangladesh
english-requirements :: https://www.canterbury.ac.uk/study-here/international/english-language-requirements
scholarships :: https://www.canterbury.ac.uk/blogs/2025/international-student-scholarships-at-cccu
"
