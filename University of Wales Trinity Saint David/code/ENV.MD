UNIVERSITY_NAME=University of Wales Trinity Saint David

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- DEGREE_SCOPED_PAGINATED: listing page URLs ---
COURSE_LISTING_PAGE_1=https://www.uwtsd.ac.uk/programme-search?f%5B0%5D=course_type%3A256&f%5B1%5D=level%3A1&f%5B2%5D=level%3A14&page=0
COURSE_LISTING_PAGE_2=https://www.uwtsd.ac.uk/programme-search?f%5B0%5D=course_type%3A256&f%5B1%5D=level%3A1&f%5B2%5D=level%3A14&page=1

# --- ALL_COURSE (not used) ---
# COURSE_CATALOGUE_HTML=../course_listing/all_course.html

UNIVERSITY_BASE_URL=https://www.uwtsd.ac.uk

# Optional — only scan matching anchors (blank = all <a href>)
#COURSE_LINK_SELECTOR=

COURSE_PATH_PATTERNS="
^/programme-courses/.+/.+$
"

# --- Study-level URL split (fallback when a catalogue is not degree-scoped) ---
UNDERGRADUATE_URL_PATTERNS="
^/programme\-courses/undergraduate(?:/|$)
(?:^|[-_/])(?:bsc|ba|beng|llb|mbchb|moptom|mpharm)(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
^/programme\-courses/postgraduate\-pgce(?:/|$)
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
/programme-search
"

EXCLUDED_PATH_PREFIXES="
/programme-search
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

bangladesh-entry :: https://www.uwtsd.ac.uk/study/how-apply/international-applications
english-requirements :: https://www.uwtsd.ac.uk/study/how-apply/international-applications/english-language-requirements
scholarships :: https://www.uwtsd.ac.uk/study/fees-and-finance/international-fees/international-funding-and-support/international-scholarships
"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=#main-content h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Main content :: #main-content
Course body :: .main-content
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
