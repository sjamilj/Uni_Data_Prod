UNIVERSITY_NAME=University of Winchester

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- DEGREE_SCOPED_PAGINATED: listing page URLs ---
COURSE_LISTING_PAGE_1=https://www.winchester.ac.uk/study/Find-Your-Course/?courseType=Foundation+Year&courseType=Undergraduate&courseType=Postgraduate&courseType=Degree+Apprenticeship&courseType=Research+Degree&courseMode=Full-time&page=1
COURSE_LISTING_PAGE_2=https://www.winchester.ac.uk/study/Find-Your-Course/?courseType=Foundation+Year&courseType=Undergraduate&courseType=Postgraduate&courseType=Degree+Apprenticeship&courseType=Research+Degree&courseMode=Full-time&page=2

# --- ALL_COURSE (not used) ---
# COURSE_CATALOGUE_HTML=../course_listing/all_course.html

UNIVERSITY_BASE_URL=https://www.winchester.ac.uk

# Optional — only scan matching anchors (blank = all <a href>)
#COURSE_LINK_SELECTOR=

COURSE_PATH_PATTERNS="
^/study/(?:undergraduate|postgraduate)/Courses/[A-Za-z0-9\-]+/?$
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
/study/Find-Your-Course
"

EXCLUDED_PATH_PREFIXES="
/study/Find-Your-Course/
"



Course overview ::
Entry requirements ::
Fees and funding ::
"

script
noscript
"


4 :: With placement
4 :: With foundation year
3 :: UK students
"

bangladesh-entry :: https://www.winchester.ac.uk/international/International-Entry-Requirements/
english-requirements :: https://www.winchester.ac.uk/international/english-language-requirements/
scholarships :: https://www.winchester.ac.uk/student-life/Scholarships-bursaries-and-awards/International-scholarships-bursaries-and-awards/
"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=#main-content h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Course overview :: #uow-course-overview
Entry requirements :: #uow-course-entry-requirements-link
Fees :: #uow-course-tuition-fees
Course features :: #uow-course-features-link
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
.uow-course-content__nav
.clearing-banner
"

COURSE_CLEAN_EXPAND_TABS=true

# --- Course markdown cleanup (shared/course_markdown_cleanup.py) ---
COURSE_MARKDOWN_REMOVE_SECTIONS="
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
bangladesh-entry ::
english-requirements ::
scholarships ::
deposit ::
"
