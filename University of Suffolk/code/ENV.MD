UNIVERSITY_NAME=University of Suffolk

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- DEGREE_SCOPED_PAGINATED: listing page URLs ---
UNDERGRADUATE_COURSE_LISTING_PAGE_1=https://www.uos.ac.uk/study/search-for-a-course/?courseType=undergraduate&courseStudyMode=full-time&page=1
UNDERGRADUATE_COURSE_LISTING_PAGE_2=https://www.uos.ac.uk/study/search-for-a-course/?courseType=undergraduate&courseStudyMode=full-time&page=2

POSTGRADUATE_COURSE_LISTING_PAGE_1=https://www.uos.ac.uk/study/search-for-a-course/?courseType=postgraduate&courseStudyMode=full-time&page=1
POSTGRADUATE_COURSE_LISTING_PAGE_2=https://www.uos.ac.uk/study/search-for-a-course/?courseType=postgraduate&courseStudyMode=full-time&page=2

# --- ALL_COURSE (not used) ---
# COURSE_CATALOGUE_HTML=../course_listing/all_course.html

UNIVERSITY_BASE_URL=https://www.uos.ac.uk

# Optional — only scan matching anchors (blank = all <a href>)
#COURSE_LINK_SELECTOR=

COURSE_PATH_PATTERNS="
^/study/[a-z0-9\-]+/?$
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
"

EXCLUDED_COURSE_PATHS="
/study/search-for-a-course
/study/undergraduate-study
/study/postgraduate-study
"

EXCLUDED_PATH_PREFIXES="
/study/search-for-a-course
/study/undergraduate-study/
/study/postgraduate-study/
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

bangladesh-entry :: https://www.uos.ac.uk/international/countries/bangladesh/
english-requirements :: https://www.uos.ac.uk/international/english-language-requirements/
"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=main h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Overview :: .accordion-container
Entry requirements :: section[id^="entry-requirements"]
Fees :: section[id^="fees"]
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
nav
.accordion-button
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
