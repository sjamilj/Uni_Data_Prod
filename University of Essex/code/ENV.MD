UNIVERSITY_NAME=University of Essex

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- DEGREE_SCOPED_PAGINATED: all programmes in one run ---
UNDERGRADUATE_COURSE_LISTING_PAGE_1=https://www.essex.ac.uk/search?collection=essex~sp-all&f.Result%20type%7Cessex~ds-courses,essex~ds-cpd-courses=Courses&start_rank=1
UNDERGRADUATE_COURSE_LISTING_PAGE_2=https://www.essex.ac.uk/search?collection=essex~sp-all&f.Result%20type%7Cessex~ds-courses,essex~ds-cpd-courses=Courses&start_rank=11

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

UNIVERSITY_BASE_URL=https://www.essex.ac.uk
# Optional CSS selector — only scan these anchors (leave blank = all <a href>)
#COURSE_LINK_SELECTOR=

# CCCU course page paths under /study-here/courses/
COURSE_PATH_PATTERNS="
^/courses/(?:ug|pg)\d+/1/[a-z0-9][a-z0-9-]*$
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
"

EXCLUDED_COURSE_PATHS="
/search
/courses
"
EXCLUDED_PATH_PREFIXES="
/bookmarked-courses
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

COURSE_PAGE_TITLE_SELECTOR=#main-content h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

# One CSS selector per line; optional heading with :: or |
# Omit course-page marketing prose; keep entry requirements and fees only.
COURSE_CLEAN_BLOCKS="
Entry requirements :: section[id*="entry"]
Fees and funding :: section[id*="fee"]
"

# Noise removed inside each matched block before markdown conversion
COURSE_CLEAN_STRIP_WITHIN="
script
noscript
nav
"

COURSE_CLEAN_EXPAND_TABS=true

# --- Course markdown cleanup (shared/course_markdown_cleanup.py) ---
# Essex presetup/execute: drop overview, modules, teaching, and apply noise.
COURSE_MARKDOWN_REMOVE_SECTIONS="
2 :: Related courses
3 :: Applying
3 :: Auditioning
3 :: Visit Loughton Campus
3 :: Our expert staff
3 :: Specialist facilities
3 :: Your future
3 :: Course structure
3 :: Teaching
3 :: Assessment
3 :: Dissertation
3 :: What is the *
3 :: Why this course
3 :: Who should apply
3 :: What you'll learn
3 :: Your learning experience
3 :: Placements and internships
3 :: Study abroad opportunities
3 :: Careers
3 :: *Open Days*
3 :: Visit Colchester Campus
3 :: Virtual tours
3 :: International & EU entry requirements
3 :: Placement year
3 :: Study abroad
4 :: Components
4 :: Modules
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
bangladesh-entry :: https://www.essex.ac.uk/international/country-specific-information/south-asia#bangladesh
english-requirements :: https://www1.essex.ac.uk/documents/admissions/englishInternational.pdf
english-course-groups :: https://www.essex.ac.uk/-/media/documents/study/english_language_requirements.pdf
scholarships :: https://www.essex.ac.uk/undergraduate/fees-and-funding/scholarships-and-funding
deposit :: https://www.essex.ac.uk/-/media/documents/about/governance/contractual-documents/2026-27/tuition-fee-deposit-policy-oct-2026-jan-and-april-2027.pdf
"

# Stage 2 LLM: read English from course markdown (injected IELTS + TOEFL/PTE bullets)
LLM_STAGE2_ENGLISH_SOURCE=course
LLM_STAGE2_UNI_PARTS=entry,scholarship,deposit

# LLM extract uses output/clean/courses directly — no download/clean in --llm-only mode:
#   python shared/run_course_pipeline.py --code-dir "University of Essex/code" --llm-only --all --resume
# Or: python shared/run_llm_to_dev_csv.py --code-dir "University of Essex/code" --resume

# --- Essex-only helpers (run from repo root; scripts live in this code/ folder) ---
# python "University of Essex/code/build_essex_english_course_groups.py"
# python "University of Essex/code/dry_run_essex_english_groups.py"
# python "University of Essex/code/dry_run_essex_course_ielts.py" --json-out "University of Essex/output/english_ielts_variations.json"
# python "University of Essex/code/fetch_essex_missing_ielts_from_urls.py" --apply
# python "University of Essex/code/backfill_essex_course_ielts.py" --apply
# python "University of Essex/code/compare_essex_ielts_match.py"
# python "University of Essex/code/dry_run_essex_foundation_pathway_map.py"
# python "University of Essex/code/inject_essex_foundation_kaplan_ielts.py" --apply
# python "University of Essex/code/inject_essex_foundation_pte_toefl.py" --apply
# python "University of Essex/code/migrate_essex_courses_to_clean.py"
# python "University of Essex/code/build_course_urls_from_markdown.py"
