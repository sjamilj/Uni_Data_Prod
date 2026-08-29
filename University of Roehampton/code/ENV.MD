UNIVERSITY_NAME=University of Roehampton

STRATEGY=ALL_COURSE

# --- ALL_COURSE: saved catalogue HTML ---
FOUNDATION_COURSE_CATALOGUE_HTML=../course_listing/foundation.html
FOUNDATION_COURSE_CATALOGUE_URL=https://www.roehampton.ac.uk/study/foundation-studies/?

UNDERGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/undergraduate.html
UNDERGRADUATE_COURSE_CATALOGUE_URL=https://www.roehampton.ac.uk/study/undergraduate-courses/?page=4

POSTGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/postgraduate.html
POSTGRADUATE_COURSE_CATALOGUE_URL=https://www.roehampton.ac.uk/study/postgraduate-taught-courses/?

POSTGRADUATE_RESEARCH_COURSE_CATALOGUE_HTML=../course_listing/postgraduate-research.html
POSTGRADUATE_RESEARCH_COURSE_CATALOGUE_URL=https://www.roehampton.ac.uk/study/postgraduate-research-courses/?

# --- DEGREE_SCOPED_PAGINATED (not used for ALL_COURSE) ---
# UNDERGRADUATE_COURSE_LISTING_PAGE_1=

UNIVERSITY_BASE_URL=https://www.roehampton.ac.uk

# Optional — only scan matching anchors (blank = all <a href>)
#COURSE_LINK_SELECTOR=

COURSE_PATH_PATTERNS="
^/study/(?:foundation-studies|undergraduate-courses|postgraduate-taught-courses|postgraduate-research-courses)/[a-z0-9\-]+/?$
"

# --- Study-level URL split (fallback when a catalogue is not degree-scoped) ---
UNDERGRADUATE_URL_PATTERNS="
^/study/undergraduate\-courses(?:/|$)
(?:^|[-_/])(?:bsc|ba|beng|llb|mbchb|moptom|mpharm)(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
^/study/postgraduate\-taught\-courses(?:/|$)
(?:^|[-_/])(?:msc|mba|llm|pgdip|pgcert|ma)(?:[-_/]|$)
"

POSTGRADUATE_RESEARCH_URL_PATTERNS="
^/study/postgraduate\-research\-courses(?:/|$)
courses-phd
(?:^|[-_/])(?:phd|mres|engd|psychd)(?:[-_/]|$)
"

FOUNDATION_URL_PATTERNS="
^/study/foundation\-studies(?:/|$)
foundation
"

EXCLUDED_COURSE_PATHS="
/study/foundation-studies
/study/undergraduate-courses
/study/postgraduate-taught-courses
/study/postgraduate-research-courses
"

EXCLUDED_PATH_PREFIXES="
"



Course overview ::
Entry requirements ::
Fees and funding ::
"

script
noscript
"


4 :: With placement
4 :: With foundation year
3 :: UK students
"

bangladesh-entry :: https://www.roehampton.ac.uk/student-support/international-students/entry-requirements/
english-requirements ::
scholarships :: https://www.roehampton.ac.uk/study/fees-and-funding/international-fees-and-financial-support/
"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=#wrapper h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Course overview :: #wrapper > section:first-of-type
Main content :: #wrapper main
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
.accordion-input
#navigation
#search-bar
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
bangladesh-entry ::
english-requirements ::
scholarships ::
deposit ::
"
