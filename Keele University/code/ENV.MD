# Keele University — degree-scoped ALL_COURSE catalogues (one run for all scopes)
UNIVERSITY_NAME=Keele University

STRATEGY=ALL_COURSE

UNDERGRADUATE_COURSE_CATALOGUE_URL=https://www.keele.ac.uk/study/undergraduate/undergraduatecourses/
UNDERGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/Undergraduate courses 2027 A-Z - Keele University.html

POSTGRADUATE_COURSE_CATALOGUE_URL=https://www.keele.ac.uk/study/postgraduatestudy/postgraduatecourses/?subject=all
POSTGRADUATE_COURSE_CATALOGUE_HTML=../course_listing/Postgraduate courses - Keele University.html

FOUNDATION_COURSE_CATALOGUE_URL=https://www.keele.ac.uk/study/foundationyears/septemberstart/
FOUNDATION_COURSE_CATALOGUE_HTML=../course_listing/Foundation Year September start - Keele University.html

POSTGRADUATE_RESEARCH_COURSE_CATALOGUE_URL=https://www.keele.ac.uk/research/postgraduateresearch/researchareas/
POSTGRADUATE_RESEARCH_COURSE_CATALOGUE_HTML=../course_listing/Research areas - Keele University.html

UNIVERSITY_BASE_URL=https://www.keele.ac.uk

#COURSE_LINK_SELECTOR=

COURSE_PATH_PATTERNS="
^/study/undergraduate/undergraduatecourses/[^/]+$
^/study/postgraduatestudy/postgraduatecourses/[^/]+$
^/research/postgraduateresearch/researchareas/[^/]+$
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
^/research/postgraduateresearch/researchareas/
(?:^|[-_/])(?:phd|mres|engd|psychd|mphil)(?:[-_/]|$)
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
/research/postgraduateresearch/researchareas
/research/postgraduateresearch
"
EXCLUDED_PATH_PREFIXES="
/international/
/current-students/
/alumni
/information/
/about/
/news/
/events/
"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=#page-wrapper h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
# Comma-separated selectors are tried left-to-right (first match with content wins).
COURSE_CLEAN_BLOCKS="
Key information :: .module--key-facts-header .list-block, .module--key-facts-header, #tabpanel-overview
Course content :: .course-section--content, #tabpanel-course-content
Entry requirements :: .course-section--entry, #tabpanel-entry-requirements
Fees and funding :: .fees-details, .pgt-fees-v_3, .course-section--ffs, #tabpanel-additional-costs
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
# Keele-specific rules in code/course_markdown_cleanup.py:
#   Entry requirements → keep #### Bangladesh + ### English language requirements only.
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
english-requirements :: https://www.keele.ac.uk/study/undergraduate/apply/entryrequirements/internationalentryrequirements/englishlanguagerequirements/#english-language-tests-(groups)
scholarships :: page_type:
deposit :: page_type:
"

# --- LLM Stage 2 routing ---
# Entry + English from course markdown; uni english JSON maps Group A–G; LLM for scholarship + deposit.
LLM_STAGE2_UNI_PARTS=scholarship,deposit,english
LLM_STAGE2_ENTRY_SOURCE=course
LLM_STAGE2_ENGLISH_SOURCE=course
LLM_STAGE2_ENTRY_SECTIONS="
Entry requirements
"
LLM_STAGE2_ENGLISH_SECTIONS="
English language requirements
"
