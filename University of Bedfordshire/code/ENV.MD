UNIVERSITY_NAME=University of Bedfordshire

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- DEGREE_SCOPED_PAGINATED: listing page URLs (one pair per programme) ---




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

UNIVERSITY_BASE_URL=https://www.beds.ac.uk

# --- Generated from Template.csv ---
UNDERGRADUATE_COURSE_LISTING_PAGE_1=https://www.beds.ac.uk/howtoapply/courses/undergraduate/
UNDERGRADUATE_LISTING_AJAX_LEVEL_CHECKBOX_IDS=Undergraduate_313909
UNDERGRADUATE_LISTING_AJAX_MODE_CHECKBOX_IDS=Full-time_614

POSTGRADUATE_COURSE_LISTING_PAGE_1=https://www.beds.ac.uk/howtoapply/courses/postgraduate/
POSTGRADUATE_LISTING_AJAX_LEVEL_CHECKBOX_IDS=Postgraduate_313908
POSTGRADUATE_LISTING_AJAX_MODE_CHECKBOX_IDS=Full-time_614

POSTGRADUATE_RESEARCH_COURSE_LISTING_PAGE_1=https://www.beds.ac.uk/howtoapply/courses/postgraduate/
POSTGRADUATE_RESEARCH_LISTING_AJAX_LEVEL_CHECKBOX_IDS=Postgraduate Research Scheme_439549
POSTGRADUATE_RESEARCH_LISTING_AJAX_MODE_CHECKBOX_IDS=Full-time_614

FOUNDATION_COURSE_LISTING_PAGE_1=https://www.beds.ac.uk/howtoapply/courses/undergraduate/
FOUNDATION_LISTING_AJAX_LEVEL_CHECKBOX_IDS=Undergraduate_313909
FOUNDATION_LISTING_AJAX_VARIANT_CHECKBOX_IDS=with Foundation Year_1519
FOUNDATION_LISTING_AJAX_MODE_CHECKBOX_IDS=Full-time_614

LISTING_PAGINATION_MODE=ajax_click
LISTING_AJAX_WAIT_SELECTOR=a.search-results__title__link
LISTING_AJAX_PAGE_BUTTON_SELECTOR=.pagination button.page-link[data-page="{page}"]
LISTING_AJAX_MODE_CHECKBOX_IDS=Full-time_614

COURSE_DOWNLOAD_USE_DEVICE_PROFILE=false
COURSE_DOWNLOAD_CDP_URL=http://127.0.0.1:9222
COURSE_DOWNLOAD_CLOUDFLARE_WARMUP=false
COURSE_DOWNLOAD_CLOUDFLARE_AUTO_CLICK=false
COURSE_DOWNLOAD_CLOUDFLARE_WAIT_SECONDS=300
COURSE_DOWNLOAD_HEADLESS=false

COURSE_LINK_SELECTOR=a.search-results__title__link

COURSE_PATH_PATTERNS="
^/courses/[^/]+$
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
"

EXCLUDED_PATH_PREFIXES="
"

# --- Course page cleaning (tune using course_detail/ samples) ---
COURSE_PAGE_TITLE_SELECTOR=h1.title

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# preprocess_course_html_uni selects International fees (#studyType) before blocks run
COURSE_CLEAN_BLOCKS="
Key information :: #bedsKeyFacts
Entry requirements :: #entryRequirements
Fees and funding :: #feesFunding
"

# Course page .course-selector (download + preprocess_course_html_uni use the same keys)
COURSE_DOWNLOAD_STUDY_TYPE=International
COURSE_DOWNLOAD_STUDY_TYPE_SELECT=#studyType
COURSE_DOWNLOAD_STUDY_MODE=Full-time
COURSE_DOWNLOAD_INTAKE_MONTH=September
# Leave empty to prefer Luton when several campuses match intake/mode
COURSE_DOWNLOAD_LOCATION=
COURSE_DOWNLOAD_INTAKE_YEAR=2026
# Fetch UCIF PDF during course download (Brave/CDP); embeds duration, Final award, Standard intake months in HTML — PDF is not kept
COURSE_DOWNLOAD_FETCH_SPEC_PDF=true

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
bangladesh-entry :: https://www.beds.ac.uk/international/countries/bangladesh/
english-requirements :: https://www.beds.ac.uk/international/international-entry-requirements/
scholarships :: https://www.beds.ac.uk/international/fees-and-scholarships/
deposit :: https://www.beds.ac.uk/international/fees-and-scholarships/
"
