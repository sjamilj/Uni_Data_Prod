UNIVERSITY_NAME=Ravensbourne University London

STRATEGY=ALL_COURSE

# --- ALL_COURSE: saved catalogue HTML ---
UNDERGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/undergraduate.html
UNDERGRADUATE_COURSE_CATALOGUE_URL=https://www.ravensbourne.ac.uk/study/undergraduate

POSTGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/postgraduate.html
POSTGRADUATE_COURSE_CATALOGUE_URL=https://www.ravensbourne.ac.uk/study/postgraduate

# --- DEGREE_SCOPED_PAGINATED (not used for ALL_COURSE) ---
# UNDERGRADUATE_COURSE_LISTING_PAGE_1=

UNIVERSITY_BASE_URL=https://www.ravensbourne.ac.uk

# Optional — only scan matching anchors (blank = all <a href>)
#COURSE_LINK_SELECTOR=

COURSE_PATH_PATTERNS="
^/study/(?:pre-degree|undergraduate|postgraduate)/[a-z0-9\-]+$
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
/study/pre-degree
/study/undergraduate
/study/postgraduate
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

bangladesh-entry :: https://www.ravensbourne.ac.uk/international-students
english-requirements :: https://www.ravensbourne.ac.uk/international-students
scholarships :: https://www.ravensbourne.ac.uk/bursaries-and-scholarships
"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=h1[data-js-hook="hero-title"]

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Main content :: #main-content
Entry requirements :: #entry-requirements
Overview slices :: .slice--type--slice-content
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
nav
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
