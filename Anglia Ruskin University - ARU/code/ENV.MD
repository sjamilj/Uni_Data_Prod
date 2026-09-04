UNIVERSITY_NAME=Anglia Ruskin University - ARU

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- DEGREE_SCOPED_PAGINATED: all 4 programmes in one run ---
UNDERGRADUATE_COURSE_LISTING_PAGE_1=https://www.aru.ac.uk/study/undergraduate/clearing/clearing-courses?levelofstudy=Undergraduate&modeofstudy=Full-time&page=1
UNDERGRADUATE_COURSE_LISTING_PAGE_2=https://www.aru.ac.uk/study/undergraduate/clearing/clearing-courses?levelofstudy=Undergraduate&modeofstudy=Full-time&page=2


# Legacy single-programme keys (optional fallback if degree-scoped keys are omitted):
# LISTING_PROGRAMME=undergraduate
# COURSE_LISTING_PAGE_1=https://www.canterbury.ac.uk/search/undergraduate-courses?pageIndex=1
# COURSE_LISTING_PAGE_2=https://www.canterbury.ac.uk/search/undergraduate-courses?pageIndex=2

# --- ALL_COURSE: degree-scoped saved catalogues (one run for all scopes) ---
# STRATEGY=ALL_COURSE
# UNDERGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/undergraduate.html
# POSTGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/…
# POSTGRADUATE_RESEARCH_COURSE_CATALOGUE_HTML=../course_listing/…
# FOUNDATION_COURSE_CATALOGUE_HTML=../course_listing/…

# Legacy single catalogue (ALL_COURSE):
# COURSE_CATALOGUE_URL=
# COURSE_CATALOGUE_HTML=


UNIVERSITY_BASE_URL=https://www.aru.ac.uk
 
# Optional CSS selector — only scan these anchors (leave blank = all <a href>)
#COURSE_LINK_SELECTOR=
 
# --- FIXED: ARU course page paths ---
# Old value was still Canterbury Christ Church's shape (^/study-here/courses/...),
# which never matches aru.ac.uk links, so every candidate URL was silently
# thrown out and course_urls.csv came out empty. ARU course pages sit one
# level under /study/undergraduate/ or /study/postgraduate/, e.g.
#   /study/undergraduate/architecture
#   /study/postgraduate/computer-science
# Foundation-year courses use the same /study/undergraduate/<slug> shape.
COURSE_PATH_PATTERNS="
^/study/(?:undergraduate|postgraduate)/[a-z0-9][a-z0-9\-]*$
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

 
# Real ARU non-course pages that match the shape above and must be excluded
EXCLUDED_COURSE_PATHS="
/study/undergraduate
/study/postgraduate
/study/undergraduate/clearing
/study/undergraduate/how-to-apply
/study/postgraduate/how-to-apply
"
 
EXCLUDED_PATH_PREFIXES="
/study/undergraduate/clearing/
/study/international/
/study/college-courses
/study/degree-apprenticeships
/study/admissions
/study/open-day
/study/continuing-professional-development
"
 
# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=#course-page-title

COURSE_CLEAN_ENGINE=utopian

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Course overview :: #utopian-course-overview
Entry requirements :: #entry_requirements
Fees and funding :: #fees_and_funding
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
.hero-image
img
"

COURSE_CLEAN_EXPAND_TABS=true

# --- Course markdown cleanup (shared/course_markdown_cleanup.py) ---
COURSE_MARKDOWN_REMOVE_SECTIONS="
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
# --- uni_req source URLs (for JSON saves without browser URL metadata) ---
UNI_REQ_SOURCE_URLS="
bangladesh-entry :: https://www.aru.ac.uk/international/south-asia
english-requirements :: https://www.aru.ac.uk/international/entry-requirements
scholarships :: https://www.aru.ac.uk/student-life/preparing-for-study/help-with-finances/scholarships
deposit :: https://www.aru.ac.uk/international/how-to-apply/step-4---receive-our-decision-on-your-application
"