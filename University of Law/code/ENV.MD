UNIVERSITY_NAME=University of Law

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- DEGREE_SCOPED_PAGINATED: all programmes in one run ---
UNDERGRADUATE_COURSE_LISTING_PAGE_1=https://www.law.ac.uk/study/search/?method=campus&lvls=undergraduate&lvls=postgraduate&smodes=fulltime&page=1
UNDERGRADUATE_COURSE_LISTING_PAGE_2=https://www.law.ac.uk/study/search/?method=campus&lvls=undergraduate&lvls=postgraduate&smodes=fulltime&page=2

# POSTGRADUATE_COURSE_LISTING_PAGE_1=https://www.canterbury.ac.uk/search/postgraduate-taught-courses?pageIndex=1
# POSTGRADUATE_COURSE_LISTING_PAGE_2=https://www.canterbury.ac.uk/search/postgraduate-taught-courses?pageIndex=2

# FOUNDATION_COURSE_LISTING_PAGE_1=https://www.canterbury.ac.uk/search/foundation-year?pageIndex=1
# FOUNDATION_COURSE_LISTING_PAGE_2=https://www.canterbury.ac.uk/search/foundation-year?pageIndex=2

# Legacy single-programme keys (optional fallback if degree-scoped keys are omitted):
# LISTING_PROGRAMME=undergraduate
# COURSE_LISTING_PAGE_1=https://www.canterbury.ac.uk/search/undergraduate-courses?pageIndex=1
# COURSE_LISTING_PAGE_2=https://www.canterbury.ac.uk/search/undergraduate-courses?pageIndex=2

# --- ALL_COURSE: degree-scoped saved catalogues (one run for all scopes) ---
# STRATEGY=ALL_COURSE
# UNDERGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/undergraduate.html
# POSTGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/postgraduate.html
# FOUNDATION_COURSE_CATALOGUE_HTML=../course_listing/foundation.html

# Legacy single catalogue (ALL_COURSE):
# COURSE_CATALOGUE_URL=
# COURSE_CATALOGUE_HTML=

UNIVERSITY_BASE_URL=https://www.law.ac.uk

# Optional CSS selector — only scan these anchors (leave blank = all <a href>)
#COURSE_LINK_SELECTOR=

# University of Law course pages: /study/undergraduate/<area>/<slug>, /study/postgraduate/<area>/<slug>
COURSE_PATH_PATTERNS="
^/study/(?:undergraduate|postgraduate)/[^/]+/[^/]+$
"

# --- Study-level URL split (fallback when a catalogue is not degree-scoped) ---
UNDERGRADUATE_URL_PATTERNS="
^/study/undergraduate(?:/|$)
(?:^|[-_/])(?:bsc|ba|beng|llb|mbchb|moptom|mpharm)(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
^/study/postgraduate(?:/|$)
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
/study/search
/study/undergraduate
/study/postgraduate
/study/online
/study/business
/study/psychology
"

EXCLUDED_PATH_PREFIXES="
/study/postgraduate/sqe/
/study/apprenticeships/
/study/scholarships-bursaries/
/study/undergraduate/course-fees-and-funding/
/study/postgraduate/course-fees-and-funding/
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

COURSE_PAGE_TITLE_SELECTOR=.course-details-header h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Key facts (normalized) :: .ulaw-normalized-stage1
Key facts grid :: #courseKeyFactsBlock
Course Start Dates :: .coursestartdateaccordionblock
Key facts :: .key-facts__details
Fees and applying :: .ulaw-normalized-fees
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
nav
.course-details-header img
"

COURSE_CLEAN_EXPAND_TABS=true

# --- Course markdown cleanup (shared/course_markdown_cleanup.py) ---
COURSE_MARKDOWN_REMOVE_SECTIONS="
2 :: Course intro
2 :: Course details
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
bangladesh-entry :: https://www.law.ac.uk/students/international/the-application-process/entry-requirements/
english-requirements :: page_type:
scholarships :: https://www.law.ac.uk/students/international/why-study-with-us/financial-information/international-scholarships/
deposit :: https://www.law.ac.uk/study/undergraduate/course-fees-and-funding/
"

# Bangladesh per-subject entry + IELTS JSON (save country page HTML, then):
#   python convert_country_entry_html.py
#   python enrich_english_requirements_from_pdf.py
# Default HTML: ../uni_req/International Entry Requirements _ University of Law.html
# PDF enrich: ../uni_req/pdf_students_accepted-english-language-qualifications.pdf
# Output: ../output/clean/uni/bangladesh-entry.md and english-requirements.md

# Foundation Year routes (same URL as UG, separate intake line on course page):
#   python split_foundation_year_courses.py
#   python backfill_course_from_english.py
# Writes output/clean/courses/foundation/*-with-foundation-year.md and trims those lines from undergraduate/.
