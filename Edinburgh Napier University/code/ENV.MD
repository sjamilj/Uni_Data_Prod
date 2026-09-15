UNIVERSITY_NAME=Edinburgh Napier University

STRATEGY=ALL_COURSE

# --- ALL_COURSE: saved catalogue HTML ---
COURSE_CATALOGUE_HTML=../course_listing/all_course.html
COURSE_CATALOGUE_URL=https://www.napier.ac.uk/courses?ps=100

# ENUIC IS1 — progression degree + Foundation Year :: pathway page URL (from course_listing/International Stage One *.html)
FOUNDATION_COURSE_FETCH_URLS="
BSc (Hons) Biomedical Science with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-biosciences
BSc (Hons) Biological Science with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-biosciences
BSc (Hons) Spot and Exercise Science with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-biosciences
BSc (Hons) Physical Activity and Health with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-biosciences
BSc (Hons) Animal Conservation Biology with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-biosciences
BSc (hons) Marine and Freshwater Biology with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-biosciences
BA (Hons) Business Management with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-business
BA (Hons) Marketing Management with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-business
BA (Hons) Accounting with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-business
BA (Hons) Accounting with Corporate Finance with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-business
BA (Hons) Financial Services with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-business
BA (Hons) International Festival and Event Management with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-business
BA (Hons) International Hospitality Management with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-business
BA (Hons) International Tourism and Airline Management with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-business
BA (Hons) International Tourism Management with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-business
BEng (Hons) Network Engineering and Cyber Security with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-computing
BEng (Hons) Computing with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-computing
BEng (Hons) Cybersecurity and Forensics with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-computing
BSc (Hons) Computer Science with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-computing
BSc (Hons) Computer Science (AI) with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-computing
BEng (Hons) Software Engineering with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-computing
BSc (Hons) Games Development with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-computing
BSc (Hons) Web Design and Development with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-digital-media
BSc (Hons) Digital Media and Interaction Design with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-digital-media
BSc (Hons) User Experience (UX) Design with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-digital-media
BEng (Hons) Civil Engineering with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-engineering
BEng (Hons) Electrical and Electronic Engineering with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-engineering
BEng (Hons) Energy and Environmental Engineering with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-engineering
BEng (Hons) Mechanical Engineering with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-engineering
BA (Hons) Media and Communications with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-mass-communication
BA (Hons) Mass Communications with Advertising and Public Relations with Foundation Year :: https://www.napier.ac.uk/global/enuic/is1/is1-mass-communication
"

# --- DEGREE_SCOPED_PAGINATED (not used for ALL_COURSE) ---
# UNDERGRADUATE_COURSE_LISTING_PAGE_1=

UNIVERSITY_BASE_URL=https://www.napier.ac.uk

# Optional — only scan matching anchors (blank = all <a href>)
#COURSE_LINK_SELECTOR=

COURSE_PATH_PATTERNS="
^/courses/[a-z0-9\-]+$
^/global/enuic/is1/[a-z0-9\-]+$
"

# --- Study-level URL split (fallback when a catalogue is not degree-scoped) ---
UNDERGRADUATE_URL_PATTERNS="
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
/global/enuic/is1/
"

EXCLUDED_COURSE_PATHS="
/courses/study-areas
/courses
"

EXCLUDED_PATH_PREFIXES="
/courses/study-areas/
"

# Skip part-time / online-learning catalogue variants (keep full-time on-campus URLs for LLM)
COURSE_EXCLUDE_URL_PATTERNS="
*postgraduate-parttime*
*postgraduate-part-time*
*postgraduate-online-learning*
*undergraduate-parttime*
*undergraduate-part-time*
*undergraduate-online-learning*
*undergraduate-online-fulltime*
"

# Napier ALL_COURSE: some online courses use short slugs (e.g. /courses/master-of-public-health).
# Match the catalogue link title (h3 inside <a>).
COURSE_EXCLUDE_LINK_TEXT_PATTERNS="
*online learning*
*part-time*
"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=h1.courseHeaderText, h1.course-title

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
COURSE_CLEAN_BLOCKS="
Course overview :: section.courseOverview
Course details :: #courseDetails
Entry requirements :: #courseEntry
Fees :: #courseFees
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
.r-tabs-nav
.courseHeader
#toolbar-logo
"

COURSE_CLEAN_EXPAND_TABS=true

# ENUIC IS1 foundation: course name + Key information only — see code/course_markdown_cleanup.py

# --- Course markdown cleanup (shared/course_markdown_cleanup.py) ---
COURSE_MARKDOWN_REMOVE_SECTIONS="
2 :: Course details
2 :: Latest news
2 :: Be part of our community
2 :: Alumni services
2 :: *Read more news*
3 :: Year 2
3 :: Year 3
3 :: Year 4
3 :: Admissions policies
3 :: UK students
3 :: Contextual offers
3 :: Living costs
4 :: With placement
4 :: With foundation year
4 :: Important additional notes
4 :: *part-time*
5 :: UK students*
5 :: *part-time*
"

UNI_REQ_SOURCE_URLS="
bangladesh-entry :: https://www.napier.ac.uk/study-with-us/undergraduate/how-to-apply/understanding-our-entry-requirements
english-requirements :: https://www.napier.ac.uk/study-with-us/international-students/english-language/english-language-requirements
scholarships :: https://www.napier.ac.uk/global/enuic/fees-and-scholarships
deposit ::
"
