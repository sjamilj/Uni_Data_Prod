# University of Salford — international full-time course search (Template.csv / Paginated.csv)
UNIVERSITY_NAME=University of Salford

STRATEGY=DEGREE_SCOPED_PAGINATED

UNIVERSITY_BASE_URL=https://www.salford.ac.uk

# --- DEGREE_SCOPED_PAGINATED: shared search (classify by COURSE_PATH_PATTERNS + URL patterns) ---
COURSE_LISTING_PAGE_1=https://www.salford.ac.uk/search/courses?query=&field_enrolment_year=All&field_subject_area_name=All&field_delivery_mode_name%5BFulltime%5D=Fulltime&field_available_to_international=1&page=0
COURSE_LISTING_PAGE_2=https://www.salford.ac.uk/search/courses?query=&field_enrolment_year=All&field_subject_area_name=All&field_delivery_mode_name%5BFulltime%5D=Fulltime&field_available_to_international=1&page=1

#COURSE_LINK_SELECTOR=.uos-results-item__course__link

COURSE_PATH_PATTERNS="
^/courses/undergraduate/[a-z0-9\-]+$
^/courses/postgraduate/[a-z0-9\-]+$
^/courses/postgraduate-researchdoctorate/[a-z0-9\-]+$
"

UNDERGRADUATE_URL_PATTERNS="
^/courses/undergraduate(?:/|$)
(?:^|[-_/])(?:bsc|ba|beng|llb|mbchb|moptom|mpharm|meng)(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
^/courses/postgraduate(?:/|$)
(?:^|[-_/])(?:msc|mba|llm|pgdip|pgcert|ma)(?:[-_/]|$)
"

POSTGRADUATE_RESEARCH_URL_PATTERNS="
^/courses/postgraduate-researchdoctorate(?:/|$)
(?:^|[-_/])(?:phd|mres|engd|psychd)(?:[-_/]|$)
"

FOUNDATION_URL_PATTERNS="
foundation
with-foundation
"

EXCLUDED_COURSE_PATHS="
"

EXCLUDED_PATH_PREFIXES="
/search/courses
"

COURSE_EXCLUDE_URL_PATTERNS="
*-with-placement*
*with-placement*
*part-time*
*parttime*
"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=h1.uos-course__header__title

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Key facts :: #salford-course-key-facts
Entry requirements :: #requirement
Fees :: #fees
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
nav
.uos-course-accordion__trigger
"

COURSE_CLEAN_EXPAND_TABS=true

# --- Course markdown cleanup (shared/course_markdown_cleanup.py) ---
COURSE_MARKDOWN_REMOVE_SECTIONS="
2 :: Main content
2 :: Overview
2 :: Course summary
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
4 :: APPLICANT PROFILE
4 :: PRE-ENROLLMENT ATTENDANCE
4 :: INTERNATIONAL APPLICATIONS
4 :: PROFESSIONAL ACCREDITATION
3 :: Additional costs
"

UNI_REQ_SOURCE_URLS="
bangladesh-entry :: page_type:
english-requirements :: https://www.salford.ac.uk/international/english-language-requirements
scholarships :: https://www.salford.ac.uk/international/scholarships
deposit :: https://www.salford.ac.uk/international/your-country-or-region/bangladesh
"
