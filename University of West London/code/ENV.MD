UNIVERSITY_NAME=University of West London

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- DEGREE_SCOPED_PAGINATED: listing page URLs ---
COURSE_LISTING_PAGE_1=https://www.uwl.ac.uk/courses/search?q=/courses/search%3Fquery%3D&f%5B0%5D=Mode%3AFull-time&query=&page=0
COURSE_LISTING_PAGE_2=https://www.uwl.ac.uk/courses/search?q=/courses/search%3Fquery%3D&f%5B0%5D=Mode%3AFull-time&query=&page=1

# --- ALL_COURSE (not used) ---
# COURSE_CATALOGUE_HTML=../course_listing/all_course.html

UNIVERSITY_BASE_URL=https://www.uwl.ac.uk

# Search-result titles only — skip foundation-year promos (btn-primary) and campus buttons (btn-tertiary)
COURSE_LINK_SELECTOR=a[rel="bookmark"][href*="/course/"]

COURSE_PATH_PATTERNS="
^/course/(?:undergraduate|postgraduate|research)/[a-z0-9\-]+$
"

# --- Study-level URL split (fallback when a catalogue is not degree-scoped) ---
UNDERGRADUATE_URL_PATTERNS="
^/course/undergraduate(?:/|$)
(?:^|[-_/])(?:bsc|ba|beng|llb|mbchb|moptom|mpharm)(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
^/course/postgraduate(?:/|$)
(?:^|[-_/])(?:msc|mba|llm|pgdip|pgcert|ma)(?:[-_/]|$)
"

POSTGRADUATE_RESEARCH_URL_PATTERNS="
^/course/research(?:/|$)
courses-phd
(?:^|[-_/])(?:phd|mres|engd|psychd)(?:[-_/]|$)
"

FOUNDATION_URL_PATTERNS="
foundation
"

EXCLUDED_COURSE_PATHS="
"

EXCLUDED_PATH_PREFIXES="
/courses/search
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

bangladesh-entry :: https://www.uwl.ac.uk/international/your-country/international-entry-requirements/bangladesh
english-requirements :: https://www.uwl.ac.uk/international/your-country/english-language-requirements
scholarships :: https://www.uwl.ac.uk/international/fees-and-funding-international-students/international-scholarships-and-bursaries
"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=.page-header h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Overview :: #overview
Course content :: #course-content
Entry requirements :: section[id*="entry"]
Fees :: section[id*="fees"]
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
.accordion-title
.mobile-expander--bar
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
