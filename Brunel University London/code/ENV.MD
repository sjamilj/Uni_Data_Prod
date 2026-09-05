# Brunel University of London
UNIVERSITY_NAME=Brunel University London
# Catalogue strategy — single page (or one URL) listing all courses.

STRATEGY=ALL_COURSE

# Full URL of the all-courses catalogue page (from ALL_COURSE.csv Course_listing_Link)
COURSE_CATALOGUE_URL=https://www.brunel.ac.uk/study/courses?courseLevel=0%2F2%2F24%2F28%2F870%2C0%2F2%2F24%2F28%2F43%2C0%2F2%2F24%2F28%2F871%2C0%2F2%2F24%2F28%2F44%2C0%2F2%2F24%2F28%2F872&pageSize=10000&studyMode=0%2F2%2F24%2F834%2F837%2C0%2F2%2F24%2F834%2F838

# Offline saved catalogue HTML (put file in course_listing/)
COURSE_CATALOGUE_HTML=../course_listing/Explore our courses _ Brunel University of London.html

# --- ALL_COURSE: degree-scoped saved catalogues (optional) ---
# UNDERGRADUATE_COURSE_CATALOGUE_HTML=
# POSTGRADUATE_COURSE_CATALOGUE_HTML=
# FOUNDATION_COURSE_CATALOGUE_HTML=

# Optional domain base for resolving relative course links
UNIVERSITY_BASE_URL=https://www.brunel.ac.uk
# Optional CSS selector — only scan these anchors (leave blank = all <a href>)
#COURSE_LINK_SELECTOR=

# Path regexes that identify a course page (one per line inside quotes, or ;-separated)
# Brunel course pages live at /study/courses/<slug>, online programmes at
# /online-programme/<department>/<slug>, and a small number of research-group PhD
# pages sit at the site root as /<slug>-research-phd.
COURSE_PATH_PATTERNS="
^/study/courses/[^/]+$
^/online-programme/[^/]+/[^/]+$
^/[a-z0-9-]+-research-phd$
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
courses-phd
(?:^|[-_/])(?:phd|mres|engd|psychd)(?:[-_/]|$)
"

FOUNDATION_URL_PATTERNS="
foundation
"

EXCLUDED_COURSE_PATHS="
/study/courses
/study/courses-atoz
/study/courses/electronic-and-communications-engineering-beng-china
/study/courses/electronic-engineering-beng-top-up
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

# China partnership / top-up programmes (no Bangladesh entry; taught in China or UK top-up only)
COURSE_EXCLUDE_URL_PATTERNS="
*/electronic-and-communications-engineering-beng-china
*/electronic-engineering-beng-top-up
*-beng-china
*-beng-top-up
"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=main h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Overview :: #main
Entry requirements :: #entryRequirements
Fees and funding :: #fees
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
.scroll-top-break__link
.accreditation-logos
.carousel-root
"

COURSE_CLEAN_EXPAND_TABS=true

# --- Course page download (scrape_course_urls.py — before saving HTML) ---
# Brunel: open Entry requirements tab, select Bangladesh, wait for country API.
COURSE_DOWNLOAD_PREP=entry_tab_country
COURSE_DOWNLOAD_HEADLESS=false
COURSE_DOWNLOAD_ENTRY_TAB_SELECTORS="
a:has-text('Entry requirements')
a[href='#entryRequirements']
"
COURSE_DOWNLOAD_COUNTRY_SELECT=#country-requirement
COURSE_DOWNLOAD_COUNTRY=Bangladesh
COURSE_DOWNLOAD_COUNTRY_WAIT_URL=courseInternationalEntryEquivalent
COURSE_DOWNLOAD_SCROLL_TO=#entryRequirements

# --- Course markdown cleanup (shared/course_markdown_cleanup.py) ---
COURSE_MARKDOWN_REMOVE_SECTIONS="
2 :: Overview
2 :: Course content
2 :: Careers and your future
2 :: UK entry requirements
2 :: Teaching and learning
2 :: Assessment and feedback
2 :: Location of study
2 :: Entry requirements
3 :: Related courses
4 :: UK
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
scholarships :: https://www.brunel.ac.uk/scholarships/home
deposit :: page_type:
"

# --- LLM Stage 2 routing ---
# Entry + English from course markdown; uni LLM only for scholarship + deposit.
LLM_STAGE2_UNI_PARTS=scholarship,deposit
LLM_STAGE2_ENTRY_SOURCE=course
LLM_STAGE2_ENGLISH_SOURCE=course
LLM_STAGE2_ENTRY_SECTIONS="
International entry requirements
"
LLM_STAGE2_ENGLISH_SECTIONS="
English language requirements
"
