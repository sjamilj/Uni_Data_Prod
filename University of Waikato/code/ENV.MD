UNIVERSITY_NAME=University of Waikato
STRATEGY=DEGREE_SCOPED_PAGINATED
LISTING_PROGRAMME=all
COURSE_LISTING_PAGE_1=https://www.waikato.ac.nz/study/qualifications/?page=1
COURSE_LISTING_PAGE_2=https://www.waikato.ac.nz/study/qualifications/?page=2
UNIVERSITY_BASE_URL=https://www.waikato.ac.nz
COURSE_PATH_PATTERNS="
^/study/qualifications/[^/?#]+/?$
"
UNDERGRADUATE_URL_PATTERNS="
(?:^|/)(?:bachelor|undergraduate|honours|diploma|certificate)(?:-|/)
"
POSTGRADUATE_URL_PATTERNS="
(?:^|/)(?:master|masters|postgraduate|graduate-diploma|graduate-certificate|pgdip|pgcert)(?:-|/)
"
POSTGRADUATE_RESEARCH_URL_PATTERNS="
(?:^|/)(?:phd|doctor-of|doctoral|doctorate)(?:-|/)
"
FOUNDATION_URL_PATTERNS="
(?:^|/)(?:foundation|certificate-in-foundation)(?:-|/)
"
EXCLUDED_COURSE_PATHS="
"
EXCLUDED_PATH_PREFIXES="
"
COURSE_CLEAN_ENGINE=generic
COURSE_PAGE_TITLE_SELECTOR=h1
COURSE_CLEAN_BLOCKS="
Course overview :: .qualification-page__summary
Key information :: .qualification-page__key-info--desktop
Entry requirements :: #entry-requirements
Fees and scholarships :: #fees-and-scholarships
"
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
"
COURSE_CLEAN_EXPAND_TABS=true
COURSE_MARKDOWN_REMOVE_SECTIONS="
"
UNI_REQ_SOURCE_URLS="
bangladesh-entry :: https://www.waikato.ac.nz/study/apply/international/entry-requirements-for-international-students/
english-requirements :: https://www.waikato.ac.nz/study/apply/international/entry-requirements-for-international-students/
scholarships :: https://www.waikato.ac.nz/study/scholarships/find-a-scholarship/vice-chancellors-international-excellence-scholarship/
deposit ::
"
