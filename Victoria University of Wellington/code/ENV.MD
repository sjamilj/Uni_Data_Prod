UNIVERSITY_NAME={University Name - SHORT}

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- DEGREE_SCOPED_PAGINATED: listing page URLs (one pair per programme) ---
UNDERGRADUATE_COURSE_LISTING_PAGE_1=
UNDERGRADUATE_COURSE_LISTING_PAGE_2=

POSTGRADUATE_COURSE_LISTING_PAGE_1=
POSTGRADUATE_COURSE_LISTING_PAGE_2=

POSTGRADUATE_RESEARCH_COURSE_LISTING_PAGE_1=
POSTGRADUATE_RESEARCH_COURSE_LISTING_PAGE_2=

FOUNDATION_COURSE_LISTING_PAGE_1=
FOUNDATION_COURSE_LISTING_PAGE_2=

# Legacy single-programme keys (optional fallback):
# LISTING_PROGRAMME=undergraduate
# COURSE_LISTING_PAGE_1=
# COURSE_LISTING_PAGE_2=

# --- ALL_COURSE: saved catalogue HTML (use course_listing/ short names or full paths) ---
# STRATEGY=ALL_COURSE
# COURSE_CATALOGUE_URL=
# COURSE_CATALOGUE_HTML=../course_listing/all_course.html
# UNDERGRADUATE_COURSE_CATALOGUE_HTML=
# POSTGRADUATE_COURSE_CATALOGUE_HTML=
# POSTGRADUATE_RESEARCH_COURSE_CATALOGUE_HTML=
# FOUNDATION_COURSE_CATALOGUE_HTML=

UNIVERSITY_BASE_URL=https://www.example.ac.uk

# Optional — only scan matching anchors (blank = all <a href>)
#COURSE_LINK_SELECTOR=

# Course URL path regex (one per line). Example:
# COURSE_PATH_PATTERNS="
# ^/courses/[a-z0-9\-]+$
# "

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
"

EXCLUDED_PATH_PREFIXES="
"

# --- Course page cleaning (tune using course_detail/ samples) ---
COURSE_PAGE_TITLE_SELECTOR=

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

COURSE_CLEAN_BLOCKS="
Course overview ::
Entry requirements ::
Fees and funding ::
"

COURSE_CLEAN_STRIP_WITHIN="
script
noscript
"

COURSE_CLEAN_EXPAND_TABS=true

# --- Course markdown cleanup (shared/course_markdown_cleanup.py) ---
# level :: heading
COURSE_MARKDOWN_REMOVE_SECTIONS="
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
