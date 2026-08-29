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

bangladesh-entry :: https://www.tees.ac.uk/sections/international/country_details.cfm?country_id=21
english-requirements :: https://connect.tees.ac.uk/docs/publicdocumentslibraries/default-document-library/legal-and-governance-services/english-language-approved-tests-accepted-qualifications-and-exemptions-criteria-2025-2026.pdf?sfvrsn=6faf5957_12
scholarships :: https://www.tees.ac.uk/sections/international/scholarships.cfm
"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=#coursepage h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Course page :: #coursepage
Header summary :: .coursepageheadercontent
Main content :: #coursepage .coursecontent
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
