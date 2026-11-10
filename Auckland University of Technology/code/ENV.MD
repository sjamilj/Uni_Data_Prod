UNIVERSITY_NAME=Auckland University of Technology

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- DEGREE_SCOPED_PAGINATED: listing page URLs (one pair per programme) ---




# Legacy single-programme keys (optional fallback):
LISTING_PROGRAMME=all

# --- ALL_COURSE: saved catalogue HTML (use course_listing/ short names or full paths) ---
# STRATEGY=ALL_COURSE
# COURSE_CATALOGUE_URL=
# COURSE_CATALOGUE_HTML=../course_listing/all_course.html
# UNDERGRADUATE_COURSE_CATALOGUE_HTML=
# POSTGRADUATE_COURSE_CATALOGUE_HTML=
# POSTGRADUATE_RESEARCH_COURSE_CATALOGUE_HTML=
# FOUNDATION_COURSE_CATALOGUE_HTML=

UNIVERSITY_BASE_URL=https://www.aut.ac.nz

# --- Generated from Template.csv ---
COURSE_LISTING_PAGE_1=https://www.aut.ac.nz/s/search.html?&collection=aut%7Esp-aut-ac-nz-meta&f.Course+type%7C5=Postgraduate&f.Course+type%7C5=Undergraduate&f.Date%7Cd=d%3D0+%3A%3A+Uncertain&f.Type%7CT=Course&num_ranks=50&profile=main-search&query=&sitetheme=purple&tab=Course&start_rank=1
COURSE_LISTING_PAGE_2=https://www.aut.ac.nz/s/search.html?&collection=aut%7Esp-aut-ac-nz-meta&f.Course+type%7C5=Postgraduate&f.Course+type%7C5=Undergraduate&f.Date%7Cd=d%3D0+%3A%3A+Uncertain&f.Type%7CT=Course&num_ranks=50&profile=main-search&query=&sitetheme=purple&tab=Course&start_rank=51

COURSE_LISTING_FETCH=browser
COURSE_DOWNLOAD_USE_DEVICE_PROFILE=false
COURSE_DOWNLOAD_CDP_URL=http://127.0.0.1:9222
COURSE_DOWNLOAD_CLOUDFLARE_WARMUP=false
COURSE_DOWNLOAD_CLOUDFLARE_AUTO_CLICK=false
COURSE_DOWNLOAD_HEADLESS=false

# Optional — only scan matching anchors (blank = all <a href>)
#COURSE_LINK_SELECTOR=

COURSE_PATH_PATTERNS="
^/(?:study/study-options/[^/]+/courses/[^/]+|courses/[^/]+)$
"

# Course URL path regex (one per line). Example:
# COURSE_PATH_PATTERNS="
# ^/courses/[a-z0-9\-]+$
# "

# --- Study-level URL split (fallback when a catalogue is not degree-scoped) ---
UNDERGRADUATE_URL_PATTERNS="
(?:^|[-_/])(?:bachelor|certificate|diploma)(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
(?:^|[-_/])(?:master|postgraduate|graduate)(?:[-_/]|$)|(?:^|[-_/])bachelor-[^/]*-honours$
"

POSTGRADUATE_RESEARCH_URL_PATTERNS="
(?:^|[-_/])(?:doctor(?:-of-[^/]+)?|phd|master-of-philosophy|master-of-[^/]+-research|mres)(?:[-_/]|$)
"

FOUNDATION_URL_PATTERNS="
(?:^|[-_/])foundation(?:[-_/]|$)
"

EXCLUDED_COURSE_PATHS="
"

EXCLUDED_PATH_PREFIXES="
"

# --- Course page cleaning (tune using course_detail/ samples) ---
COURSE_PAGE_TITLE_SELECTOR=

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

COURSE_CLEAN_BLOCKS="
Entry requirements and English language requirements :: .r-tabs-panel[data-content='1']
Quick facts :: .mainRight .quickFacts:not(.quickFactsFees)
International tuition fees :: .quickFactsFees
"

COURSE_CLEAN_STRIP_WITHIN="
script
noscript
"

COURSE_CLEAN_EXPAND_TABS=true

# --- Course markdown cleanup (shared/course_markdown_cleanup.py) ---
# level :: heading
COURSE_MARKDOWN_REMOVE_SECTIONS="
3 :: If you have New Zealand qualifications
2 :: Useful New Zealand school subjects
4 :: With placement
4 :: With foundation year
3 :: UK students
"

# --- uni_req source URLs (JSON saves without browser URL metadata) ---
# html_stem :: canonical page URL (matches uni_req/*.html filename stem)
UNI_REQ_SOURCE_URLS="
bangladesh-entry ::
english-requirements ::
scholarships ::
deposit ::
"
