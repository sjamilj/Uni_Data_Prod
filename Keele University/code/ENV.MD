# Keele University — degree-scoped ALL_COURSE catalogues (one run for all scopes)
UNIVERSITY_NAME=Keele University

STRATEGY=ALL_COURSE

UNDERGRADUATE_COURSE_CATALOGUE_URL=https://www.keele.ac.uk/study/undergraduate/undergraduatecourses/
UNDERGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/Undergraduate courses 2027 A-Z - Keele University.html

POSTGRADUATE_COURSE_CATALOGUE_URL=https://www.keele.ac.uk/study/postgraduatestudy/postgraduatecourses/?subject=all
POSTGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/Postgraduate courses - Keele University.html

FOUNDATION_COURSE_CATALOGUE_URL=https://www.keele.ac.uk/study/foundationyears/septemberstart/
FOUNDATION_COURSE_CATALOGUE_HTML=../course_listing/Foundation Year September start - Keele University.html

UNIVERSITY_BASE_URL=https://www.keele.ac.uk

#COURSE_LINK_SELECTOR=

COURSE_PATH_PATTERNS="
^/study/undergraduate/undergraduatecourses/[^/]+$
^/study/postgraduatestudy/postgraduatecourses/[^/]+$
"

# --- Study-level URL split (fallback when a catalogue is not degree-scoped) ---
UNDERGRADUATE_URL_PATTERNS="
^/study/undergraduate(?:/|$)
(?:^|[-_/])(?:bsc|ba|beng|llb|mbchb|moptom|mpharm)(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
^/study/postgraduatestudy(?:/|$)
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
/study/undergraduate/undergraduatecourses
/study/postgraduatestudy/postgraduatecourses
/study/foundationyears
/study/foundationyears/septemberstart
/study/foundationyears/foundationcourses
"
EXCLUDED_PATH_PREFIXES="
/international/
/current-students/
/alumni
/information/
/about/
/research/
/news/
/events/
"



"


"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=#page-wrapper h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Course overview :: .ug-summary-container
Course content :: .module.layout-content-module
Entry requirements :: .module--course
Fees and funding :: .module--coursekfacts
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
#related-courses-list
.auto-related-courses
.tab__button
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
bangladesh-entry :: https://www.keele.ac.uk/study/internationalstudents/yourcountry/asia/bangladesh/#postgraduate-taught-entry-requirements
english-requirements :: https://www.keele.ac.uk/study/undergraduate/apply/entryrequirements/internationalentryrequirements/englishlanguagerequirements/#english-language-tests-(groups)
scholarships :: page_type:
"
