UNIVERSITY_NAME=University of Derby

STRATEGY=ALL_COURSE

# --- ALL_COURSE: saved catalogue HTML ---
COURSE_CATALOGUE_HTML=../course_listing/all_course.html
COURSE_CATALOGUE_URL=https://www.derby.ac.uk/courses/a-z/

# --- DEGREE_SCOPED_PAGINATED (not used for ALL_COURSE) ---
# UNDERGRADUATE_COURSE_LISTING_PAGE_1=

UNIVERSITY_BASE_URL=https://www.derby.ac.uk

# Optional — only scan matching anchors (blank = all <a href>)
#COURSE_LINK_SELECTOR=

COURSE_PATH_PATTERNS="
^/(?:undergraduate|postgraduate)/[^/]+/[^/]+/?$
"

# --- Study-level URL split (fallback when a catalogue is not degree-scoped) ---
UNDERGRADUATE_URL_PATTERNS="
^/undergraduate(?:/|$)
(?:^|[-_/])(?:bsc|ba|beng|llb|mbchb|moptom|mpharm)(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
^/postgraduate(?:/|$)
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
/short-courses-cpd
"

EXCLUDED_PATH_PREFIXES="
/short-courses-cpd/
/online/
/apprenticeships/
"

# Skip /online/ and /apprenticeships/ during download/clean/presetup/LLM
COURSE_EXCLUDE_URL_PATTERNS="
/online/*
/apprenticeships/*
"

# Part-time-only study modes (Study options / Duration); dual FT+PT degrees are kept.
COURSE_EXCLUDE_COURSE_TYPES="
*part-time*
"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=.course-hero h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
# #entry-requirements is only an <h2> (<20 chars) — use tab panel + prose section.
# Entry tabs: prefer #entry-year2 when both exist (see preprocess_course_html_uni); #entry-year1 if only one tab.
COURSE_CLEAN_BLOCKS="
Key course details :: #key-course-details
Entry requirements :: #entry-year2, #entry-year1, section.text-block[aria-labelledby=entry-requirements] div:has(> table), section.text-block[aria-labelledby=entry-requirements]:has(p)
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
.course-hero-navigation
.share-button
.course-hero-inner-content-buttons
.banner-promo
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
english-requirements :: https://www.derby.ac.uk/life/international-students/applicants/english-language-tests/
scholarships :: https://www.derby.ac.uk/study/fees-finance/scholarships/
deposit ::
"
