UNIVERSITY_NAME=University of Birmingham

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- DEGREE_SCOPED_PAGINATED: all programmes in one run ---
UNDERGRADUATE_COURSE_LISTING_PAGE_1=https://www.birmingham.ac.uk/study/courses?academicLevel=e2ad4c71-7518-45d7-b1a2-c1280513496c%2C73e0fd63-0e06-4007-9898-316387e121ec&campus=2a020f81-b3a9-483b-aaef-450ac0f1fe9d%2C6c94c033-0b1e-4acb-8860-c0796313a4be&courseStructure=1c63ff89-efb7-4f2b-8bf5-f6f79365dc0c%2Ca6575da0-f868-4842-bbd8-288437f56505&pageIndex=1&preventScrollTop=true&studyLevel=Undergraduate%2CPostgraduate%20taught%2CPostgraduate%20research&studyPattern=full%20time
UNDERGRADUATE_COURSE_LISTING_PAGE_2=https://www.birmingham.ac.uk/study/courses?academicLevel=e2ad4c71-7518-45d7-b1a2-c1280513496c%2C73e0fd63-0e06-4007-9898-316387e121ec&campus=2a020f81-b3a9-483b-aaef-450ac0f1fe9d%2C6c94c033-0b1e-4acb-8860-c0796313a4be&courseStructure=1c63ff89-efb7-4f2b-8bf5-f6f79365dc0c%2Ca6575da0-f868-4842-bbd8-288437f56505&pageIndex=2&preventScrollTop=true&studyLevel=Undergraduate%2CPostgraduate%20taught%2CPostgraduate%20research&studyPattern=full%20time

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

UNIVERSITY_BASE_URL=https://www.birmingham.ac.uk
# Optional CSS selector — only scan these anchors (leave blank = all <a href>)
#COURSE_LINK_SELECTOR=

# CCCU course page paths under /study-here/courses/
COURSE_PATH_PATTERNS="
^/study/(?:undergraduate|postgraduate)/subjects/[^/]+/[^/]+$
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
foundation
"

EXCLUDED_COURSE_PATHS="
/study/courses
/study/applicants
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

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Course summary :: #course-summary
Entry requirements :: #entry-requirements
Fees and funding :: #fees-and-funding
Modules :: #modules-and-programme-structure
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
.staff-listing-carousel
.related-courses__card-item
.scroll-top-break__link
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
bangladesh-entry :: https://www.birmingham.ac.uk/international/students/country/bangladesh
english-requirements :: https://www.birmingham.ac.uk/study/undergraduate/apply/entry-requirements/international-entry-requirements
scholarships :: page_type:
"
