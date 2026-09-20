UNIVERSITY_NAME=University of Birmingham

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- Postgraduate only: PG taught + PG research, full time (paginated course search) ---
# Page 1 has no pageIndex; scraper follows further pages from listing pagination (~32 pages).
POSTGRADUATE_COURSE_LISTING_PAGE_1=https://www.birmingham.ac.uk/study/courses?academicLevel=e2ad4c71-7518-45d7-b1a2-c1280513496c&campus=2a020f81-b3a9-483b-aaef-450ac0f1fe9d%2C6c94c033-0b1e-4acb-8860-c0796313a4be%2C5a58b8f7-243a-47af-b008-6458f4990519%2C78f73b08-54d9-4b84-bd63-2432c23dcf33&courseStructure=1c63ff89-efb7-4f2b-8bf5-f6f79365dc0c%2Ca6575da0-f868-4842-bbd8-288437f56505&preventScrollTop=true&studyLevel=Postgraduate%20taught%2CPostgraduate%20research&studyPattern=full%20time
POSTGRADUATE_COURSE_LISTING_PAGE_2=https://www.birmingham.ac.uk/study/courses?academicLevel=e2ad4c71-7518-45d7-b1a2-c1280513496c&campus=2a020f81-b3a9-483b-aaef-450ac0f1fe9d%2C6c94c033-0b1e-4acb-8860-c0796313a4be%2C5a58b8f7-243a-47af-b008-6458f4990519%2C78f73b08-54d9-4b84-bd63-2432c23dcf33&courseStructure=1c63ff89-efb7-4f2b-8bf5-f6f79365dc0c%2Ca6575da0-f868-4842-bbd8-288437f56505&pageIndex=2&preventScrollTop=true&studyLevel=Postgraduate%20taught%2CPostgraduate%20research&studyPattern=full%20time

# Undergraduate / foundation listing omitted (postgraduate-only catalogue).

UNIVERSITY_BASE_URL=https://www.birmingham.ac.uk
# Optional CSS selector — only scan these anchors (leave blank = all <a href>)
#COURSE_LINK_SELECTOR=

COURSE_PATH_PATTERNS="
^/study/postgraduate/subjects/[^/]+/[^/]+$
"

# --- Study-level URL split (classify links from the PG listing) ---
POSTGRADUATE_URL_PATTERNS="
^/study/postgraduate(?:/|$)
(?:^|[-_/])(?:msc|mba|llm|pgdip|pgcert|ma)(?:[-_/]|$)
"

POSTGRADUATE_RESEARCH_URL_PATTERNS="
^/study/postgraduate(?:/|$)
(?:^|[-_/])(?:phd|mres|engd|psychd|ma-by-research)(?:[-_/]|$)
"

EXCLUDED_COURSE_PATHS="
/study/courses
/study/applicants
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

# Exclude online / non-UK campus delivery when URLs carry location= (optional tighten)
COURSE_EXCLUDE_URL_PATTERNS="
*location=Dubai*
*location=Singapore*
*studyPattern=part*
*studyPattern=part%20time*
"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

# Hero country dropdown on PG course pages — download selects this before HTML capture.
COURSE_PAGE_COUNTRY=Bangladesh
# When hero Start date is month-only (e.g. "September"), append this year for Stage 1 intake.
COURSE_DEFAULT_INTAKE_YEAR=2026

COURSE_PAGE_TITLE_SELECTOR=h1.hero-courses__title

COURSE_CLEAN_ENGINE=generic

# Hero tiles and scholarship carousel cards are rewritten by preprocess into
# #birmingham-course-key-facts, #fees-and-funding, and #birmingham-course-scholarships.
COURSE_CLEAN_BLOCKS="
Key facts :: #birmingham-course-key-facts
Course summary :: #course-summary
Fees and funding :: #fees-and-funding
Scholarships :: #birmingham-course-scholarships
Entry requirements :: #entry-requirements
Modules :: #modules-and-programme-structure
"

COURSE_CLEAN_STRIP_WITHIN="
script
noscript
.staff-listing-carousel
.related-courses__card-item
.scroll-top-break__link
.carousel__list
.card-scholarship
.course-tile-ranking
"

COURSE_CLEAN_EXPAND_TABS=true

# --- Course markdown cleanup (postgraduate course pages) ---
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
3 :: Living costs
5 :: UK students*
5 :: *part-time*
"

UNI_REQ_SOURCE_URLS="
bangladesh-entry :: https://www.birmingham.ac.uk/international/students/country/bangladesh
english-requirements :: https://www.birmingham.ac.uk/study/undergraduate/apply/entry-requirements/international-entry-requirements
scholarships :: https://www.birmingham.ac.uk/study/postgraduate/fees-and-funding/scholarships
"
