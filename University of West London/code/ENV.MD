# University of West London — full-time course search (Template.csv / Paginated.csv)
UNIVERSITY_NAME=University of West London

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- DEGREE_SCOPED_PAGINATED: listing page URLs ---
COURSE_LISTING_PAGE_1=https://www.uwl.ac.uk/courses/search?q=/courses/search%3Fquery%3D&f%5B0%5D=Mode%3AFull-time&query=&page=0
COURSE_LISTING_PAGE_2=https://www.uwl.ac.uk/courses/search?q=/courses/search%3Fquery%3D&f%5B0%5D=Mode%3AFull-time&query=&page=1

# Foundation year — full-time UG search + refine_results (Foundation Year facet).
# Same course URL as UG is OK: FOUNDATION listing scope tags study_level=foundation in foundation_course_urls.csv.
FOUNDATION_COURSE_LISTING_PAGE_1=https://www.uwl.ac.uk/courses/search?q=/courses/search%3Fquery%3D&f%5B0%5D=Mode%3AFull-time&f%5B1%5D=level%3AUndergraduate&f%5B2%5D=refine_results%3A1&query=&page=0
FOUNDATION_COURSE_LISTING_PAGE_2=https://www.uwl.ac.uk/courses/search?q=/courses/search%3Fquery%3D&f%5B0%5D=Mode%3AFull-time&f%5B1%5D=level%3AUndergraduate&f%5B2%5D=refine_results%3A1&query=&page=1

# --- ALL_COURSE (not used) ---
# COURSE_CATALOGUE_HTML=../course_listing/all_course.html

UNIVERSITY_BASE_URL=https://www.uwl.ac.uk

# Search-result titles only — skip foundation-year promos (btn-primary) and campus buttons (btn-tertiary)
COURSE_LINK_SELECTOR=a[rel="bookmark"][href*="/course/"]

COURSE_PATH_PATTERNS="
^/course/(?:undergraduate|postgraduate|research)/[a-z0-9\-]+$
"

# --- Study-level URL split (fallback when a catalogue is not degree-scoped) ---
UNDERGRADUATE_URL_PATTERNS="
^/course/undergraduate(?:/|$)
(?:^|[-_/])(?:bsc|ba|beng|llb|mbchb|moptom|mpharm)(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
^/course/postgraduate(?:/|$)
(?:^|[-_/])(?:msc|mba|llm|pgdip|pgcert|ma)(?:[-_/]|$)
"

POSTGRADUATE_RESEARCH_URL_PATTERNS="
^/course/research(?:/|$)
courses-phd
(?:^|[-_/])(?:phd|mres|engd|psychd)(?:[-_/]|$)
"

FOUNDATION_URL_PATTERNS="
foundation
"

EXCLUDED_COURSE_PATHS="
"

EXCLUDED_PATH_PREFIXES="
/courses/search
"

COURSE_EXCLUDE_URL_PATTERNS="
*-foundation-year*
*part-time*
"

# --- Cloudflare + CDP: attach to YOUR browser (code/CLOUDFLARE-CDP.md) ---
COURSE_DOWNLOAD_USE_DEVICE_PROFILE=false
COURSE_DOWNLOAD_CDP_URL=http://127.0.0.1:9222
COURSE_DOWNLOAD_BROWSER=edge
COURSE_DOWNLOAD_HEADLESS=false
COURSE_DOWNLOAD_CLOUDFLARE_WARMUP=false
COURSE_DOWNLOAD_CLOUDFLARE_AUTO_CLICK=false

# Device-profile fallback (if CDP not possible): code/CLOUDFLARE-BROWSER.md
# COURSE_DOWNLOAD_USE_DEVICE_PROFILE=true
# COURSE_DOWNLOAD_REFRESH_DEVICE_PROFILE=false
# COURSE_DOWNLOAD_CLOUDFLARE_WAIT_SECONDS=300

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=.page-header h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Key facts :: #uwl-course-key-facts
UK entry requirements :: #uwl-uk-entry-requirements
Entry requirements :: #t-requirements-2
Fees and funding :: [data-tabs-content='t-funding']
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
.accordion-title
.mobile-expander--bar
"

COURSE_CLEAN_EXPAND_TABS=true

# --- Course markdown cleanup (shared/course_markdown_cleanup.py) ---
COURSE_MARKDOWN_REMOVE_SECTIONS="
2 :: Latest news
2 :: Be part of our community
2 :: Alumni services
2 :: *Read more news*
2 :: Course details
2 :: What you'll study
2 :: What our students say
4 :: With placement
4 :: With foundation year
4 :: Important additional notes
4 :: *part-time*
3 :: Funding your studies
3 :: UK students
3 :: Contextual offers
3 :: Living costs
3 :: Requirements:
3 :: Funding:
5 :: UK students*
5 :: *part-time*
"

UNI_REQ_SOURCE_URLS="
bangladesh-entry :: https://www.uwl.ac.uk/international/your-country/international-entry-requirements/bangladesh
english-requirements :: https://www.uwl.ac.uk/international/your-country/english-language-requirements
scholarships :: https://www.uwl.ac.uk/international/fees-and-funding-international-students/international-scholarships-and-bursaries
deposit :: https://www.uwl.ac.uk/international/after-you-apply
"
