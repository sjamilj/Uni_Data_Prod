# University of East London — degree-scoped ALL_COURSE catalogues
UNIVERSITY_NAME=University of East London

STRATEGY=ALL_COURSE

# --- ALL_COURSE: catalogues (DegreeScopedALLCourse.csv) ---


UNDERGRADUATE_COURSE_CATALOGUE_URL=https://www.uel.ac.uk/study/undergraduate/courses
# UNDERGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/undergraduate.html

POSTGRADUATE_COURSE_CATALOGUE_URL=https://www.uel.ac.uk/study/postgraduate/courses
# POSTGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/postgraduate.html

# Foundation listing = UEL ISC IFP page. Scrape takes progression-degree <a href>s
# (Business & Management + Engineering, Computing & Science) as foundation URLs on uel.ac.uk.
# The IFP page itself is also kept. Same UG URL may also appear under undergraduate.
# PGR (MPhil/PhD, Prof Doc, EdD) is listed on the postgraduate catalogue.

UNIVERSITY_BASE_URL=https://www.uel.ac.uk

# Optional — only scan matching anchors (blank = all <a href>)
#COURSE_LINK_SELECTOR=

# Sample paths: /undergraduate/courses/bsc-hons-computer-science
#               /postgraduate/courses/msc-civil-engineering
#               /our-programmes/international-foundation-programme/ (uelisc.com)
COURSE_PATH_PATTERNS="
^/(?:undergraduate|postgraduate)/courses/[a-z0-9\-]+$
^/our-programmes/international-foundation-programme/?$
"

# --- Study-level URL split (fallback when a catalogue is not degree-scoped) ---
UNDERGRADUATE_URL_PATTERNS="
^/undergraduate(?:/|$)
(?:^|[-_/])(?:bsc|ba|beng|llb|mbchb|moptom|mpharm|fdsc)(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
^/postgraduate(?:/|$)
(?:^|[-_/])(?:msc|mba|llm|pgdip|pgcert|ma|march)(?:[-_/]|$)
"

POSTGRADUATE_RESEARCH_URL_PATTERNS="
(?:^|[-_/])(?:mphil-phd|prof-doc|edd|phd|mres|engd|psychd|mphil)(?:[-_/]|$)
"

FOUNDATION_URL_PATTERNS="
international-foundation-programme
foundation
(?:^|[-_/])fdsc(?:[-_/]|$)
"

EXCLUDED_COURSE_PATHS="
/study/undergraduate/courses
/study/postgraduate/courses
/undergraduate/courses
/postgraduate/courses
/our-programmes
/our-programmes/international-year-one
/our-programmes/pre-masters-business-and-humanities
/our-programmes/pre-masters-english-and-research-skills
"

EXCLUDED_PATH_PREFIXES="
/international/
/study/fees-funding/
/clearing/
/current-students/
/alumni
/information/
/about/
/research/
/news/
/events/
/blog/
/visa-immigration-advice/
/zh/
/vi/
/th/
/ar/
/ru/
"

# Skip online / distance-learning slugs at download/clean (they can still appear in course_urls.csv)
COURSE_EXCLUDE_URL_PATTERNS="
*-online
*distance-learning*
*distance*
*part-time*
*parttime*
"

COURSE_EXCLUDE_COURSE_TYPES="
*part-time*
*distance learning*
*online*
"

# --- Course page cleaning (tune from course_detail/ samples) ---
# Keep h1 + international full-time .course-option-details + start-date buttons.
# Home / part-time / overview are dropped; full-entry modal (academic + English per route) is kept in #uel-entry-requirements.
# UG pages with both modal routes produce two markdown files (same URL): clean/courses/undergraduate/{slug}.md uses
# Degree (including contextual offer); clean/courses/foundation/{slug}.md uses Degree with foundation year.
# PG: Full entry requirements modal content (flat h3 sections, no route picker) is taken from dialog.modal-entry in the block.

COURSE_PAGE_TITLE_SELECTOR=h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

COURSE_CLEAN_BLOCKS="
 :: #uel-clean-facts
 :: #uel-entry-requirements
"

COURSE_CLEAN_STRIP_WITHIN="
script
noscript
nav
.apply-link
.right
.progressive-reveal-modal
.coh-modal
"

COURSE_CLEAN_EXPAND_TABS=true

# --- Course markdown cleanup (shared/course_markdown_cleanup.py) ---
COURSE_MARKDOWN_REMOVE_SECTIONS="
2 :: Latest news
3 :: Home Applicant
3 :: UK students
4 :: *part-time*
4 :: With placement
4 :: With foundation year
"

UNI_REQ_SOURCE_URLS="
bangladesh-entry :: https://www.uel.ac.uk/international/guidance-your-region/south-asia/bangladesh
english-requirements :: https://www.uel.ac.uk/regions/english-language-requirements
scholarships :: https://www.uel.ac.uk/study/fees-funding/international-fees-funding/international-scholarships
deposit :: https://www.uel.ac.uk/study/fees-funding/paying-your-fees-international-students
"
