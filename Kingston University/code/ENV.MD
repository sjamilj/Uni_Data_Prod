UNIVERSITY_NAME=Kingston University

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- DEGREE_SCOPED_PAGINATED: all programmes in one run ---
UNDERGRADUATE_COURSE_LISTING_PAGE_1=https://www.kingston.ac.uk/study/course-search?course_type=1&course_type=2&course_type=14&page=1
UNDERGRADUATE_COURSE_LISTING_PAGE_2=https://www.kingston.ac.uk/study/course-search?course_type=1&course_type=2&course_type=14&page=2

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

UNIVERSITY_BASE_URL=https://www.kingston.ac.uk
# Optional CSS selector — only scan these anchors (leave blank = all <a href>)
#COURSE_LINK_SELECTOR=

# CCCU course page paths under /study-here/courses/
COURSE_PATH_PATTERNS="
^/study/(?:undergraduate|postgraduate|foundation|degree-apprenticeships|short-courses|online-courses)/[a-z0-9][a-z0-9-]*$
"

# --- Study-level URL split (fallback when a catalogue is not degree-scoped) ---
UNDERGRADUATE_URL_PATTERNS="
^/study/undergraduate(?:/|$)
(?:^|[-_/])(?:bsc|ba|beng|llb|mbchb|moptom|mpharm)(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
^/study/postgraduate(?:/|$)
(?:^|[-_/])(?:msc|mba|llm|pgdip|pgcert|ma)(?:[-_/]|$)
"

POSTGRADUATE_RESEARCH_URL_PATTERNS="
courses-phd
(?:^|[-_/])(?:phd|mres|engd|psychd)(?:[-_/]|$)
"

FOUNDATION_URL_PATTERNS="
^/study/foundation(?:/|$)
foundation
"

EXCLUDED_COURSE_PATHS="
/study/course-search
/study/undergraduate
/study/undergraduate/courses
/study/undergraduate/clearing
/study/undergraduate/how-to-apply
/study/undergraduate/parents-carers-and-supporters
/study/undergraduate/study-or-work-abroad
/study/undergraduate/keep-in-touch-with-news-and-events
/study/postgraduate
/study/postgraduate/courses
/study/postgraduate/how-to-apply
/study/postgraduate/postgraduate-professional-placement
/study/postgraduate/join-our-mailing-list
/study/foundation
/study/foundation/courses
/study/degree-apprenticeships
/study/degree-apprenticeships/courses
/study/short-courses
/study/short-courses/courses
/study/online-courses
"
EXCLUDED_PATH_PREFIXES="
/study/undergraduate/clearing/
/study/international-students/
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

COURSE_PAGE_TITLE_SELECTOR=#main-content h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Why choose this course :: #why-choose-this-course
Course content :: #course-content
Entry requirements :: #entry-requirements
Fees and funding :: #fees-and-funding
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
nav
.c-accordion-item__icon-wrapper
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
bangladesh-entry :: https://www.kingston.ac.uk/study/international-students/country-specific-information#asia
english-requirements :: https://www.kingston.ac.uk/study/international-students/english-language-entry-requirements
scholarships :: https://www.kingston.ac.uk/study/fees-and-funding/international-scholarships-and-bursaries
"
