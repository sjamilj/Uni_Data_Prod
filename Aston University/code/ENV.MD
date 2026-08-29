# Aston University
UNIVERSITY_NAME=Aston University
# Catalogue strategy — single page (or one URL) listing all courses.

STRATEGY=ALL_COURSE

# Full URL of the all-courses / A–Z catalogue page (from ALL_COURSE.csv Course_listing_Link)
COURSE_CATALOGUE_URL=https://www.aston.ac.uk/courses-atoz

# Offline saved catalogue HTML (put file in course_listing/)
COURSE_CATALOGUE_HTML=../course_listing/Courses - A to Z _ Aston University.html

# Optional domain base for resolving relative course links
UNIVERSITY_BASE_URL=https://www.aston.ac.uk

# Path regexes that identify a course page (one per line inside quotes, or ;-separated)
COURSE_PATH_PATTERNS="
^/study/courses(?:-phd)?/[^/]+(?:/[^/]+)?$
"

# --- Study-level URL split (fallback when a catalogue is not degree-scoped) ---
UNDERGRADUATE_URL_PATTERNS="
^/study/courses(?:/|$)
(?:^|[-_/])(?:bsc|ba|beng|llb|mbchb|moptom|mpharm)(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
(?:^|[-_/])(?:msc|mba|llm|pgdip|pgcert|ma)(?:[-_/]|$)
"

POSTGRADUATE_RESEARCH_URL_PATTERNS="
^/study/courses\-phd(?:/|$)
courses-phd
(?:^|[-_/])(?:phd|mres|engd|psychd)(?:[-_/]|$)
"

FOUNDATION_URL_PATTERNS="
foundation
"

EXCLUDED_COURSE_PATHS="
/courses/a-to-z-listing
/courses/search
/courses/choices
/courses/prospectus
/courses/short-courses
/courses/saved
/courses/foundation-programmes
/study/courses
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

COURSE_PAGE_TITLE_SELECTOR=h1.title-field.page-title

# generic (default) | utopian | plugin | auto
COURSE_CLEAN_ENGINE=generic

# Drupal bbd-course-page: header summary + main body (entry/fees live inside content-sections)
COURSE_CLEAN_BLOCKS="
Course summary :: .course-page-header
Course details :: .field--name-field-content-sections
"

COURSE_CLEAN_STRIP_WITHIN="
script
noscript
style
iframe
.slick-cloned
nav.slick__arrow
.eu-cookie-compliance-banner
.hide-from-mobile-nav
.course-info-section-link
"

COURSE_CLEAN_EXPAND_TABS=false

# --- Course markdown cleanup (shared/course_markdown_cleanup.py) ---
COURSE_MARKDOWN_REMOVE_SECTIONS="
2 :: Latest news
2 :: Be part of our community
2 :: Alumni services
2 :: *Read more news*
3 :: Contextual offer
"

UNI_REQ_SOURCE_URLS="
bangladesh-entry :: https://www.aston.ac.uk/international/aston-in-your-country/south-asia/bangladesh
english-requirements :: https://www.aston.ac.uk/international/english-language-requirements
scholarships :: https://www.aston.ac.uk/international/scholarships
"

# --- Course type filter (download + clean pipeline) ---
# Skip short-course/CPD and part-time courses after download.

COURSE_TYPE_HTML_SELECTORS="
.field--name-field-bbd-course-type .field--item
"

COURSE_EXCLUDE_COURSE_TYPES="
*short*
*CPD*
*part-time*
*distance learning*
"

COURSE_EXCLUDE_URL_PATTERNS="
*standalone-module*
*short-course*
"
