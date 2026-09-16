UNIVERSITY_NAME=Cardiff Metropolitan University

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- DEGREE_SCOPED_PAGINATED: all programmes in one run ---
UNDERGRADUATE_COURSE_LISTING_PAGE_1=https://www.cardiffmet.ac.uk/courses/?page=1
UNDERGRADUATE_COURSE_LISTING_PAGE_2=https://www.cardiffmet.ac.uk/courses/?page=2

POSTGRADUATE_COURSE_LISTING_PAGE_1=https://www.cardiffmet.ac.uk/courses/?courseType=postgraduate&page=1
POSTGRADUATE_COURSE_LISTING_PAGE_2=https://www.cardiffmet.ac.uk/courses/?courseType=postgraduate&page=2

POSTGRADUATE_RESEARCH_COURSE_LISTING_PAGE_1=https://www.cardiffmet.ac.uk/courses/?courseType=research&page=1
POSTGRADUATE_RESEARCH_COURSE_LISTING_PAGE_2=https://www.cardiffmet.ac.uk/courses/?courseType=research&page=2

# Foundation hub (browser-save reference: course_listing/Foundation Years _ Cardiff Metropolitan University.html)
FOUNDATION_COURSE_LISTING_PAGE_1=https://www.cardiffmet.ac.uk/study/undergraduate/subjects/foundation/

# --- ALL_COURSE: degree-scoped saved catalogues (one run for all scopes) ---
# STRATEGY=ALL_COURSE
# UNDERGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/undergraduate.html
# POSTGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/postgraduate.html
# FOUNDATION_COURSE_CATALOGUE_HTML=../course_listing/foundation.html

# Legacy single catalogue (ALL_COURSE):
# COURSE_CATALOGUE_URL=
# COURSE_CATALOGUE_HTML=

UNIVERSITY_BASE_URL=https://www.cardiffmet.ac.uk
# Optional CSS selector — only scan these anchors (leave blank = all <a href>)
#COURSE_LINK_SELECTOR=

# Course detail paths under cardiffmet.ac.uk/courses/
COURSE_PATH_PATTERNS="
^/courses/(?:undergraduate|postgraduate)/[a-z0-9][a-z0-9-]*$
"

# --- Study-level URL split (fallback when a catalogue is not degree-scoped) ---
UNDERGRADUATE_URL_PATTERNS="
^/courses/undergraduate(?:/|$)
(?:^|[-_/])(?:bsc|ba|beng|llb|mbchb|moptom|mpharm)(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
^/courses/postgraduate(?:/|$)
(?:^|[-_/])(?:msc|mba|llm|pgdip|pgcert|ma)(?:[-_/]|$)
"

POSTGRADUATE_RESEARCH_URL_PATTERNS="
courses-phd
(?:^|[-_/])(?:phd|mres|engd|psychd)(?:[-_/]|$)
"

FOUNDATION_URL_PATTERNS="
^/courses/undergraduate/foundation
foundation-in-management
foundation-leading-to
"

EXCLUDED_COURSE_PATHS="
/courses
/courses/short-courses
"
EXCLUDED_PATH_PREFIXES="
/study/clearing/
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

COURSE_PAGE_TITLE_SELECTOR=.slide__wrapper-title-container h1, h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Course key facts :: section.block-12 ul[data-year]
Course overview :: #course-summary-container .block-wysiwyg, #course-summary-container section.block-11
Entry requirements :: #course-summary-container section.block-14
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
nav
"

COURSE_CLEAN_EXPAND_TABS=false

# --- Course markdown cleanup (shared/course_markdown_cleanup.py) ---
COURSE_MARKDOWN_REMOVE_SECTIONS="
2 :: Latest news
2 :: Be part of our community
2 :: Alumni services
2 :: *Read more news*
2 :: Course overview
4 :: With placement
4 :: With foundation year
4 :: Important additional notes
4 :: *part-time*
3 :: UK students
3 :: Contextual offers
3 :: Living costs
3 :: English Language Requirements
3 :: How to Apply
3 :: Part-time Fees
3 :: Mature Students
5 :: UK students*
5 :: *part-time*
"

UNI_REQ_SOURCE_URLS="
bangladesh-entry :: https://www.cardiffmet.ac.uk/international-students/country-specific-entry-requirements/#Asia
english-requirements :: https://www.cardiffmet.ac.uk/international-students/english-language-requirements/accepted-secure-english-language-tests/
scholarships :: https://www.cardiffmet.ac.uk/international-students/fees-and-finance/international-scholarships/
deposit :: https://www.cardiffmet.ac.uk/international-students/fees-and-finance/
"
