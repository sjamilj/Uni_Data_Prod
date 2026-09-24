UNIVERSITY_NAME=University of East Anglia

STRATEGY=DEGREE_SCOPED_PAGINATED

# Mixed catalogue (Paginated.csv). Study level is split from course URLs.
COURSE_LISTING_PAGE_1=https://www.uea.ac.uk/search/courses?primaryCategory%5B0%5D=Undergraduate&primaryCategory%5B1%5D=Postgraduate&primaryCategory%5B2%5D=PhD%20or%20other%20doctorate&secondaryCategory%5B0%5D=Full%20Time&secondaryCategory%5B1%5D=International

# Optional degree-scoped listing URLs (same Next-button pager):
# UNDERGRADUATE_COURSE_LISTING_PAGE_1=https://www.uea.ac.uk/search/courses/undergraduate
# POSTGRADUATE_COURSE_LISTING_PAGE_1=https://www.uea.ac.uk/search/courses/postgraduate-taught

# Listing URL does not change between pages — click Next.
LISTING_PAGINATION_MODE=click
LISTING_CLICK_NEXT_SELECTOR=button[aria-label="Next Page"]
LISTING_AJAX_WAIT_SELECTOR=a[href*="/course/"]

UNIVERSITY_BASE_URL=https://www.uea.ac.uk

COURSE_LINK_SELECTOR=a[href*="/course/"]

COURSE_PATH_PATTERNS="
^/course/(?:undergraduate|postgraduate)/[a-z0-9-]+$
"

# --- Study-level URL split (mixed /search/courses listing) ---
UNDERGRADUATE_URL_PATTERNS="
^/course/undergraduate(?:/|$)
(?:^|[-_/])(?:bsc|ba|beng|llb|mbchb|moptom|mpharm|msci|mphys|meng)(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
^/course/postgraduate(?:/|$)
(?:^|[-_/])(?:msc|mba|llm|pgdip|pgcert|ma|mres)(?:[-_/]|$)
"

POSTGRADUATE_RESEARCH_URL_PATTERNS="
(?:^|[-_/])(?:phd|mphil|engd|psychd|doctorate)(?:[-_/]|$)
"

FOUNDATION_URL_PATTERNS="
foundation-year
with-a-foundation
foundation
"

EXCLUDED_COURSE_PATHS="
/search/courses
/search/courses/undergraduate
/search/courses/postgraduate-taught
"

EXCLUDED_PATH_PREFIXES="
/study/international-students/
/apply/
/visit/
/research/
/news/
/events/
/about/
"

COURSE_EXCLUDE_URL_PATTERNS="
*part-time*
*parttime*
"

# Headed Playwright — no Cloudflare / CDP.
COURSE_DOWNLOAD_HEADLESS=false
COURSE_DOWNLOAD_USE_DEVICE_PROFILE=false
COURSE_DOWNLOAD_CLOUDFLARE_WARMUP=false
COURSE_DOWNLOAD_CLOUDFLARE_AUTO_CLICK=false

# --- Course page cleaning (tune using course_detail/ samples) ---
COURSE_PAGE_TITLE_SELECTOR=h1.course-title

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

COURSE_CLEAN_BLOCKS="
Key information :: [class*=key-details__content]
Entry requirements :: #entry_requirements
Fees and funding :: #fees_funding
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
2 :: Related courses
2 :: How to Apply
2 :: Explore our Campus
2 :: Accreditations
2 :: Careers
2 :: Study and Modules
"

# --- uni_req source URLs (JSON saves without browser URL metadata) ---
# html_stem :: canonical page URL (matches uni_req/*.html filename stem)
UNI_REQ_SOURCE_URLS="
bangladesh-entry :: https://www.uea.ac.uk/study/international-students/country-map/south-asia
english-requirements :: https://www.uea.ac.uk/apply/our-admissions-policy/english-language-equivalencies
scholarships :: https://www.uea.ac.uk/study/international-students/fees-and-scholarships
deposit :: https://www.uea.ac.uk/study/international-students/fees-and-scholarships
"
