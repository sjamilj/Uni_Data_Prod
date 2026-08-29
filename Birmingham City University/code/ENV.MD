UNIVERSITY_NAME=Birmingham City University

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- DEGREE_SCOPED_PAGINATED: all 4 programmes in one run ---
UNDERGRADUATE_COURSE_LISTING_PAGE_1=https://www.bcu.ac.uk/courses/search?int=1&international=&janstart=&mode=1&skiptoresults=False&type=2&isclearingsearch=False&isinternationalsearch=True&isjanstartsearch=False&perpage=20&page=1#results
UNDERGRADUATE_COURSE_LISTING_PAGE_2=https://www.bcu.ac.uk/courses/search?int=1&international=&janstart=&mode=1&skiptoresults=False&type=2&isclearingsearch=False&isinternationalsearch=True&isjanstartsearch=False&perpage=20&page=2#results

POSTGRADUATE_COURSE_LISTING_PAGE_1=https://www.bcu.ac.uk/courses/search?int=1&international=&janstart=&mode=1&skiptoresults=False&type=3&isclearingsearch=False&isinternationalsearch=True&isjanstartsearch=False&perpage=20&page=1#results
POSTGRADUATE_COURSE_LISTING_PAGE_2=https://www.bcu.ac.uk/courses/search?int=1&international=&janstart=&mode=1&skiptoresults=False&type=3&isclearingsearch=False&isinternationalsearch=True&isjanstartsearch=False&perpage=20&page=2#results

POSTGRADUATE_RESEARCH_COURSE_LISTING_PAGE_1=https://www.bcu.ac.uk/courses/search?term=&intake=&type=5&subj=&mode=1&International=true&page=&perpage=20&skiptoresults=1#results
POSTGRADUATE_RESEARCH_COURSE_LISTING_PAGE_2=https://www.bcu.ac.uk/courses/search?term=&intake=&type=5&subj=&mode=1&International=true&page=&perpage=20&skiptoresults=2#results

FOUNDATION_COURSE_LISTING_PAGE_1=https://www.bcu.ac.uk/courses/search?int=1&international=&janstart=&mode=1&skiptoresults=False&type=1&isclearingsearch=False&isinternationalsearch=True&isjanstartsearch=False&perpage=20&page=1#results
FOUNDATION_COURSE_LISTING_PAGE_2=https://www.bcu.ac.uk/courses/search?int=1&international=&janstart=&mode=1&skiptoresults=False&type=1&isclearingsearch=False&isinternationalsearch=True&isjanstartsearch=False&perpage=20&page=2#results

# Legacy single-programme keys (optional fallback if degree-scoped keys are omitted):
# LISTING_PROGRAMME=undergraduate
# COURSE_LISTING_PAGE_1=https://www.canterbury.ac.uk/search/undergraduate-courses?pageIndex=1
# COURSE_LISTING_PAGE_2=https://www.canterbury.ac.uk/search/undergraduate-courses?pageIndex=2

# --- ALL_COURSE: degree-scoped saved catalogues (one run for all scopes) ---
# STRATEGY=ALL_COURSE
# UNDERGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/undergraduate.html
# POSTGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/postgraduate.html
# FOUNDATION_COURSE_CATALOGUE_HTML=../course_listing/foundation.html

# Legacy single catalogue (ALL_COURSE):
# COURSE_CATALOGUE_URL=
# COURSE_CATALOGUE_HTML=

UNIVERSITY_BASE_URL=https://www.bcu.ac.uk
# Optional CSS selector — only scan these anchors (leave blank = all <a href>)
#COURSE_LINK_SELECTOR=

# CCCU course page paths under /study-here/courses/
COURSE_PATH_PATTERNS="
^/courses/[a-z0-9][a-z0-9-]*-\d{4}-\d{2}$
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
/courses/search
/courses/choices
/courses/prospectus
/courses/short-courses
/courses/saved
"
EXCLUDED_PATH_PREFIXES="
/bookmarked-courses
/clearing/
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

COURSE_PAGE_TITLE_SELECTOR=.course__title h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Overview :: #overview
Entry requirements :: #entry_requirements
Fees and how to apply :: #fees_how_to_apply
Course in depth :: #course_in_depth
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
.course__menu
.course__actions
.course-function-btns
.course__image-container
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

# --- Manual extra clean (shared/extra_clean_courses.py — NOT in pipeline) ---
# Folder-specific keys: EXTRA_CLEAN_REMOVE_SECTIONS_{LEVEL}
# Levels: foundation, undergraduate, postgraduate, postgraduate_research, other
EXTRA_CLEAN_REMOVE_SECTIONS="
2 :: Clearing *
2 :: Overview
2 :: Course in depth
3 :: Clearing
3 :: Hotline now open
3 :: Accredited By
3 :: What's covered in this course?
3 :: Similar Courses
3 :: Download course specification
3 :: Go Abroad
3 :: Guidance for UK*
3 :: Personal statement
3 :: Work Experience
3 :: Financial Support
3 :: Clearing Open Days
4 :: Professional alignment
4 :: Personal statement
4 :: *UCAS*
4 :: *country representative*
5 :: Association of Chartered Certified Accountants*
5 :: Chartered Institute of Management Accountants
5 :: Institute of Chartered Accountants in England and Wales
5 :: The Institute of Financial Accountants
5 :: ICAS
5 :: *UCAS*
5 :: Complete your details
5 :: Select your course
5 :: Write a personal statement
5 :: Get a reference
5 :: Pay your application fee
"

EXTRA_CLEAN_REMOVE_SECTIONS_FOUNDATION="
3 :: *Open Days*
3 :: Why Choose Us*
"

EXTRA_CLEAN_REMOVE_SECTIONS_UNDERGRADUATE="
3 :: *Open Days*
3 :: Why Choose Us*
3 :: Professional Placement year
"

UNI_REQ_SOURCE_URLS="
bangladesh-entry :: https://www.bcu.ac.uk/international/bcu-in-your-country/bangladesh
english-requirements :: https://www.bcu.ac.uk/international/your-application/english-language-and-english-tests/accepted-qualifications
scholarships :: page_type:
"
