UNIVERSITY_NAME=London South Bank University

STRATEGY=ALL_COURSE

# --- ALL_COURSE: saved catalogue HTML ---
UNDERGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/undergraduate.html
UNDERGRADUATE_COURSE_CATALOGUE_URL=https://www.lsbu.ac.uk/study/course-finder?f.Method+of+Study%7CcoursesMode=full-time&profile=_default&query=%21nullsearch&collection=lsbu%7Esp-courses-meta&sort=title&f.Level%7CcourseLevel=undergraduate

POSTGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/postgraduate.html
POSTGRADUATE_COURSE_CATALOGUE_URL=https://www.lsbu.ac.uk/study/course-finder?f.Method+of+Study%7CcoursesMode=full-time&profile=_default&query=%21nullsearch&collection=lsbu%7Esp-courses-meta&sort=title&f.Level%7CcourseLevel=postgraduate

# --- DEGREE_SCOPED_PAGINATED (not used for ALL_COURSE) ---
# UNDERGRADUATE_COURSE_LISTING_PAGE_1=

UNIVERSITY_BASE_URL=https://www.lsbu.ac.uk

# Optional CSS selector — only scan these anchors (blank = all <a href>)
COURSE_LINK_SELECTOR=.item__title a, a.item__list-view-link

# LSBU course-finder listings use Funnelback redirect hrefs; scraper unwraps ?url=
# to the real path e.g. /study/course-finder/bsc-hons-adult-nursing
COURSE_PATH_PATTERNS="
^/study/course-finder/[a-z0-9][a-z0-9\-]*$
"

# --- Study-level URL split (fallback when a catalogue is not degree-scoped) ---
UNDERGRADUATE_URL_PATTERNS="
^/study/course\-finder(?:/|$)
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
/study/course-finder
"

EXCLUDED_PATH_PREFIXES="
/study/course-finder?
"

COURSE_EXCLUDE_COURSE_TYPES="
*part-time*
"

# --- Cloudflare: attach to Edge via CDP (see code/CLOUDFLARE-CDP.md) ---
COURSE_DOWNLOAD_USE_DEVICE_PROFILE=false
COURSE_DOWNLOAD_BROWSER=edge
COURSE_DOWNLOAD_CDP_URL=http://127.0.0.1:9222
COURSE_DOWNLOAD_CLOUDFLARE_WARMUP=false
COURSE_DOWNLOAD_CLOUDFLARE_AUTO_CLICK=false
COURSE_DOWNLOAD_HEADLESS=false
COURSE_DOWNLOAD_CLOUDFLARE_WAIT_SECONDS=300

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=h1.hero-banner-courses__title, h1.top-banner__main-title

COURSE_DEFAULT_INTAKE_YEAR=2026

LSBU_ENTRY_COUNTRY_SLUG=bangladesh

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Key facts :: #lsbu-course-key-facts
Entry requirements :: #lsbu-course-entry-requirements, #entry-requirements, #entry-level-requirements
Fees :: #fees
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
.main-tabs__tab-label
.js-tablist__link
"

COURSE_CLEAN_EXPAND_TABS=true

# --- Course markdown cleanup (shared/course_markdown_cleanup.py) ---
COURSE_MARKDOWN_REMOVE_SECTIONS="
2 :: Non-standard entry
2 :: Latest news
2 :: Be part of our community
2 :: Alumni services
2 :: *Read more news*
4 :: With placement
4 :: With foundation year
4 :: Important additional notes
4 :: *part-time*
3 :: Choose your country
3 :: Missing English and Maths qualifications?
3 :: Possible fee changes
3 :: Scholarships
3 :: UK students
3 :: Contextual offers
3 :: Living costs
5 :: UK students*
5 :: *part-time*
"

UNI_REQ_SOURCE_URLS="
bangladesh-entry :: https://www.lsbu.ac.uk/international/your-country/asia-and-oceania/bangladesh
english-requirements :: https://www.lsbu.ac.uk/study/undergraduate/entry-requirements
scholarships :: https://www.lsbu.ac.uk/international/fees-and-funding/scholarships
deposit :: https://www.lsbu.ac.uk/international/fees-and-funding
"
