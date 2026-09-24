UNIVERSITY_NAME=University of South Wales

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- DEGREE_SCOPED_PAGINATED: listing page URLs ---
# Foundation year (full-time UG filter); page 1 without &page= is equivalent to page=1
FOUNDATION_COURSE_CATALOGUE_URL=https://www.southwales.ac.uk/courses/?courselevel=undergraduate&coursemode=full-time&coursetype=foundation+year
FOUNDATION_COURSE_LISTING_PAGE_1=https://www.southwales.ac.uk/courses/?courselevel=undergraduate&coursemode=full-time&coursetype=foundation+year&page=1
FOUNDATION_COURSE_LISTING_PAGE_2=https://www.southwales.ac.uk/courses/?courselevel=undergraduate&coursemode=full-time&coursetype=foundation+year&page=2

UNDERGRADUATE_COURSE_LISTING_PAGE_1=https://www.southwales.ac.uk/courses/?courselevel=undergraduate&coursemode=full-time&page=1
UNDERGRADUATE_COURSE_LISTING_PAGE_2=https://www.southwales.ac.uk/courses/?courselevel=undergraduate&coursemode=full-time&page=2

POSTGRADUATE_COURSE_LISTING_PAGE_1=https://www.southwales.ac.uk/courses/?courselevel=postgraduate&coursemode=full-time&page=1
POSTGRADUATE_COURSE_LISTING_PAGE_2=https://www.southwales.ac.uk/courses/?courselevel=postgraduate&coursemode=full-time&page=2

# --- ALL_COURSE (not used) ---
# COURSE_CATALOGUE_HTML=../course_listing/all_course.html

UNIVERSITY_BASE_URL=https://www.southwales.ac.uk

# Cloudflare + CDP (real browser): code/CLOUDFLARE-CDP.md | docs/shared/cloudflare-course-download.md
COURSE_LISTING_FETCH=browser
COURSE_DOWNLOAD_USE_DEVICE_PROFILE=false
COURSE_DOWNLOAD_CDP_URL=http://127.0.0.1:9222
COURSE_DOWNLOAD_BROWSER=brave
COURSE_DOWNLOAD_HEADLESS=false
COURSE_DOWNLOAD_CLOUDFLARE_WARMUP=false
COURSE_DOWNLOAD_CLOUDFLARE_AUTO_CLICK=false
COURSE_DOWNLOAD_CLOUDFLARE_WAIT_SECONDS=300

# Optional — only scan matching anchors (blank = all <a href>)
#COURSE_LINK_SELECTOR=

COURSE_PATH_PATTERNS="
^/courses/[a-z0-9\-]+/?$
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
-foundation
"

EXCLUDED_COURSE_PATHS="
/courses
/courses/course-listing
"

EXCLUDED_PATH_PREFIXES="
"

# Exclude saved HTML during clean/download (shared/course_type_filter.py — COURSE_EXCLUDE_HTML_CONTAINS)
COURSE_EXCLUDE_HTML_CONTAINS="
*not currently open to international applicants*
"

COURSE_EXCLUDE_URL_PATTERNS="
*course-listing*
"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=.masthead-course__title, .masthead-course h1, .masthead-course-new__title

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Key facts :: #usw-stage1-facts
Typical entry :: #usw-typical-entry
Entry requirements :: #usw-international-entry
International fees :: #usw-fees-section
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
2 :: DESIGNED FOR
2 :: Course Highlights
2 :: Module Overview
3 :: *International applications welcomed*
4 :: With placement
4 :: With foundation year
4 :: Important additional notes
3 :: Additional information*
4 :: *part-time*
3 :: UK students
3 :: Contextual offers
3 :: Living costs
3 :: Contextual offers
3 :: We're here to help
5 :: UK students*
5 :: *part-time*
5 :: Home students
"

UNI_REQ_SOURCE_URLS="
bangladesh-entry :: https://www.southwales.ac.uk/international/your-country/bangladesh/
english-requirements :: https://www.southwales.ac.uk/international/english-language-programmes/requirements/
scholarships :: https://www.southwales.ac.uk/international/fees-scholarships/international-scholarships/
deposit :: https://www.southwales.ac.uk/international/your-country/bangladesh/
"
