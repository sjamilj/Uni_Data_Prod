UNIVERSITY_NAME=Teesside University

STRATEGY=ALL_COURSE

# --- ALL_COURSE: saved catalogue HTML ---
COURSE_CATALOGUE_HTML=../course_listing/all_course.html
COURSE_CATALOGUE_URL=https://www.tees.ac.uk/sections/coursesearch/

# --- DEGREE_SCOPED_PAGINATED (not used for ALL_COURSE) ---
# UNDERGRADUATE_COURSE_LISTING_PAGE_1=

UNIVERSITY_BASE_URL=https://www.tees.ac.uk

# Optional — only scan matching anchors (blank = all <a href>)
#COURSE_LINK_SELECTOR=

COURSE_PATH_PATTERNS="
^/(?:undergraduate_courses|postgraduate_courses)/[^/]+/[^/]+\.cfm$
"

# --- Study-level URL split (fallback when a catalogue is not degree-scoped) ---
UNDERGRADUATE_URL_PATTERNS="
^/undergraduate_courses(?:/|$)
(?:^|[-_/])(?:bsc|ba|beng|llb|mbchb|moptom|mpharm)(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
^/postgraduate_courses(?:/|$)
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
"

EXCLUDED_PATH_PREFIXES="
/sections/coursesearch/
"

# Drop online-only courses during URL scrape and download (path contains "(online)")
COURSE_EXCLUDE_URL_PATTERNS="
*(online)*
"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=#coursepage h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
# #tees-key-info is assembled in code/course_markdown_cleanup.py from #notifications + .row.courseinfo
COURSE_CLEAN_BLOCKS="
Key information :: #tees-key-info
Entry requirements :: #tab3
Fees and funding :: #tees-fees
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
#sectionmenu
#mainmenu
"

COURSE_CLEAN_EXPAND_TABS=true

# --- Course markdown cleanup (shared/course_markdown_cleanup.py) ---
COURSE_MARKDOWN_REMOVE_SECTIONS="
2 :: Course page
2 :: Course overview
2 :: Course details
2 :: Employability
2 :: Information for international applicants
2 :: Header summary
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
