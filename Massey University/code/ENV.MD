UNIVERSITY_NAME=Massey University
STRATEGY=ALL_COURSE
COURSE_CATALOGUE_URL=https://www.massey.ac.nz/search/?size=n_366_n&filters%5B0%5D%5Bfield%5D=__search_type&filters%5B0%5D%5Bvalues%5D%5B0%5D=quals-specs&filters%5B0%5D%5Btype%5D=all&filters%5B1%5D%5Bfield%5D=is_international_available&filters%5B1%5D%5Bvalues%5D%5B0%5D=n_1_n&filters%5B1%5D%5Btype%5D=any&filters%5B2%5D%5Bfield%5D=study_level&filters%5B2%5D%5Bvalues%5D%5B0%5D=Undergraduate%20study&filters%5B2%5D%5Bvalues%5D%5B1%5D=Postgraduate%20study&filters%5B2%5D%5Btype%5D=any
COURSE_CATALOGUE_HTML=../course_listing/all_course.html
UNIVERSITY_BASE_URL=https://www.massey.ac.nz
COURSE_PATH_PATTERNS="
^/study/all-qualifications-and-degrees/[^/?#]+(?:/[^/?#]+)?/?$
"
UNDERGRADUATE_URL_PATTERNS="
bachelor-of
bachelor-
undergraduate
diploma
certificate
"
POSTGRADUATE_URL_PATTERNS="
master-of
postgraduate
post-graduate
graduate-diploma
graduate-certificate
postgrad
"
POSTGRADUATE_RESEARCH_URL_PATTERNS="
phd
doctor-of
doctoral
professional-doctorate
mres
"
FOUNDATION_URL_PATTERNS="
foundation
"
EXCLUDED_COURSE_PATHS="
"
EXCLUDED_PATH_PREFIXES="
"
COURSE_PAGE_TITLE_SELECTOR=h1
COURSE_CLEAN_ENGINE=generic
COURSE_CLEAN_BLOCKS="
Course overview :: .qual-intro__blurb
Key facts :: .key-facts
Entry requirements :: details:has(> summary#entry-requirements)
Fees and scholarships :: details:has(> summary#fees-scholarships)
"
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
nav
footer
"
COURSE_CLEAN_EXPAND_TABS=true
COURSE_MARKDOWN_REMOVE_SECTIONS="
"
# Future Food page-specific marketing/key-facts removal is handled conditionally
# in code/course_markdown_cleanup.py so other course pages retain their content.
UNI_REQ_SOURCE_URLS="
bangladesh-entry :: https://www.massey.ac.nz/study/entry-requirements-to-study-at-massey/entry-requirements-for-international-students/
english-requirements :: https://www.massey.ac.nz/study/entry-requirements-to-study-at-massey/entry-requirements-for-international-students/
scholarships :: https://www.massey.ac.nz/study/scholarships-and-awards/
deposit ::
"
