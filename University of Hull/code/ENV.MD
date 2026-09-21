# University of Hull — degree-scoped paginated search listings (Template.csv)
UNIVERSITY_NAME=University of Hull

STRATEGY=DEGREE_SCOPED_PAGINATED

UNIVERSITY_BASE_URL=https://www.hull.ac.uk

# --- DEGREE_SCOPED_PAGINATED: COURSE_LISTING_PAGE_1 / PAGE_2 (from Template.csv) ---
# Foundation
FOUNDATION_COURSE_LISTING_PAGE_1=https://www.hull.ac.uk/search/courses?q=&level=undergraduate&option=foundation-year&year=2027&mode=full-time&page=1
FOUNDATION_COURSE_LISTING_PAGE_2=https://www.hull.ac.uk/search/courses?q=&level=undergraduate&option=foundation-year&year=2027&mode=full-time&page=2
# Undergraduate
UNDERGRADUATE_COURSE_LISTING_PAGE_1=https://www.hull.ac.uk/search/courses?q=&mode=full-time&page=1&level=undergraduate&year=2027
UNDERGRADUATE_COURSE_LISTING_PAGE_2=https://www.hull.ac.uk/search/courses?q=&mode=full-time&page=2&level=undergraduate&year=2027
# Postgraduate
POSTGRADUATE_COURSE_LISTING_PAGE_1=https://www.hull.ac.uk/search/courses?q=&mode=full-time&page=1&level=postgraduate-taught&year=2027
POSTGRADUATE_COURSE_LISTING_PAGE_2=https://www.hull.ac.uk/search/courses?q=&mode=full-time&page=2&level=postgraduate-taught&year=2027
# Postgraduate Research
POSTGRADUATE_RESEARCH_COURSE_LISTING_PAGE_1=https://www.hull.ac.uk/search/courses?q=&mode=full-time&page=1&level=postgraduate-research&year=2027
POSTGRADUATE_RESEARCH_COURSE_LISTING_PAGE_2=https://www.hull.ac.uk/search/courses?q=&mode=full-time&page=2&level=postgraduate-research&year=2027

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

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=main h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Key facts :: #hull-course-key-facts
Entry Requirements :: section[aria-label="Entry Requirements"]
Fees & Funding :: section[aria-label="Fees & Funding"]
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
2 :: Course content
2 :: Boost your CV
2 :: AMBA & AACSB
2 :: Study abroad
2 :: Specialise
2 :: Participate in live projects
2 :: About this course
2 :: Module options
2 :: Our facilities
2 :: Featured academics
2 :: Future prospects
2 :: Become part of the next generation*
2 :: Not ready to apply yet?
2 :: You may also be interested in*
2 :: Latest news
2 :: Be part of our community
2 :: Alumni services
2 :: *Read more news*
3 :: Watchlist
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
scholarships :: https://www.hull.ac.uk/study/postgraduate-taught/fees-and-funding/scholarships-and-awards
"
