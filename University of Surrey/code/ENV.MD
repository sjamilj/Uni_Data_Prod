UNIVERSITY_NAME=University of Surrey

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- DEGREE_SCOPED_PAGINATED: listing page URLs ---
UNDERGRADUATE_COURSE_LISTING_PAGE_1=https://www.surrey.ac.uk/undergraduate?courses_ug%5Bpage%5D=1&courses_ug%5Blayout%5D=grid
UNDERGRADUATE_COURSE_LISTING_PAGE_2=https://www.surrey.ac.uk/undergraduate?courses_ug%5Bpage%5D=2&courses_ug%5Blayout%5D=grid

POSTGRADUATE_COURSE_LISTING_PAGE_1=https://www.surrey.ac.uk/postgraduate?courses_pgt%5Bpage%5D=1&courses_pgt%5BrefinementList%5D%5Bmode%5D%5B0%5D=Full-time&courses_pgt%5Blayout%5D=grid
POSTGRADUATE_COURSE_LISTING_PAGE_2=https://www.surrey.ac.uk/postgraduate?courses_pgt%5Bpage%5D=2&courses_pgt%5BrefinementList%5D%5Bmode%5D%5B0%5D=Full-time&courses_pgt%5Blayout%5D=grid

POSTGRADUATE_RESEARCH_COURSE_LISTING_PAGE_1=https://www.surrey.ac.uk/postgraduate/research?courses_pgr%5Bpage%5D=1&courses_pgr%5BrefinementList%5D%5Bmode%5D%5B0%5D=Full-time&courses_pgr%5Blayout%5D=grid
POSTGRADUATE_RESEARCH_COURSE_LISTING_PAGE_2=https://www.surrey.ac.uk/postgraduate/research?courses_pgr%5Bpage%5D=2&courses_pgr%5BrefinementList%5D%5Bmode%5D%5B0%5D=Full-time&courses_pgr%5Blayout%5D=grid

FOUNDATION_COURSE_LISTING_PAGE_1=https://www.surrey.ac.uk/undergraduate?courses_ug%5Bpage%5D=1&courses_ug%5BrefinementList%5D%5Bstudy_options%5D%5B0%5D=Foundation%20year&courses_ug%5Blayout%5D=grid
FOUNDATION_COURSE_LISTING_PAGE_2=https://www.surrey.ac.uk/undergraduate?courses_ug%5Bpage%5D=2&courses_ug%5BrefinementList%5D%5Bstudy_options%5D%5B0%5D=Foundation%20year&courses_ug%5Blayout%5D=grid

# --- ALL_COURSE (not used) ---
# COURSE_CATALOGUE_HTML=../course_listing/all_course.html

UNIVERSITY_BASE_URL=https://www.surrey.ac.uk

# Optional — only scan matching anchors (blank = all <a href>)
#COURSE_LINK_SELECTOR=

COURSE_PATH_PATTERNS="
^/undergraduate/[a-z0-9\-]+$
^/postgraduate/[a-z0-9\-]+$
^/postgraduate/research/[a-z0-9\-]+$
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

bangladesh-entry :: https://www.surrey.ac.uk/bangladesh/entry-requirements
english-requirements :: https://www.surrey.ac.uk/apply/international/english-language-requirements
deposit :: https://www.surrey.ac.uk/fees-and-funding/tuition-fees-guidance
"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=#main-content h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Main content :: #main-content
Course sections :: .layout-container .region-content
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
nav
.country-btn
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
