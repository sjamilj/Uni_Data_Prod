# University of Hull — degree-scoped ALL_COURSE catalogues (one run for all scopes)
UNIVERSITY_NAME=University of Hull

STRATEGY=ALL_COURSE

UNDERGRADUATE_COURSE_CATALOGUE_URL=https://www.hull.ac.uk/study/undergraduate/courses
UNDERGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/All Undergraduate Courses _ University of Hull.html

POSTGRADUATE_COURSE_CATALOGUE_URL=https://www.hull.ac.uk/study/postgraduate-taught/courses
POSTGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/All Postgraduate Taught Courses _ University of Hull.html

POSTGRADUATE_RESEARCH_COURSE_CATALOGUE_URL=https://www.hull.ac.uk/study/postgraduate-research/courses
POSTGRADUATE_RESEARCH_COURSE_CATALOGUE_HTML=../course_listing/All postgraduate research areas of study _ University of Hull.html

UNIVERSITY_BASE_URL=https://www.hull.ac.uk

#COURSE_LINK_SELECTOR=

COURSE_PATH_PATTERNS="
^/study/undergraduate/courses/[^/]+$
^/study/postgraduate-taught/courses/[^/]+$
^/study/postgraduate-research/courses/[^/]+$
"

# --- Study-level URL split (fallback when a catalogue is not degree-scoped) ---
UNDERGRADUATE_URL_PATTERNS="
^/study/undergraduate(?:/|$)
(?:^|[-_/])(?:bsc|ba|beng|llb|mbchb|moptom|mpharm)(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
^/study/postgraduate\-taught(?:/|$)
(?:^|[-_/])(?:msc|mba|llm|pgdip|pgcert|ma)(?:[-_/]|$)
"

POSTGRADUATE_RESEARCH_URL_PATTERNS="
^/study/postgraduate\-research(?:/|$)
courses-phd
(?:^|[-_/])(?:phd|mres|engd|psychd)(?:[-_/]|$)
"

FOUNDATION_URL_PATTERNS="
foundation
"

EXCLUDED_COURSE_PATHS="
/study/undergraduate/courses
/study/postgraduate-taught/courses
/study/postgraduate-research/courses
"

EXCLUDED_PATH_PREFIXES="
/international/
/current-students/
/alumni
/information/
/about/
/research/
/news/
/events/
"



"


"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=main h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Course content :: main
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
.carousel
youtube-video
#main-menu
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
bangladesh-entry :: https://www.hull.ac.uk/study/international-students/your-country/bangladesh
english-requirements :: https://www.hull.ac.uk/study/international-students/how-to-apply/english-language-requirements#accepted-english-qualifications
scholarships :: page_type:
"
