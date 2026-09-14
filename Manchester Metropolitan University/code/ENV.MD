UNIVERSITY_NAME=Manchester Metropolitan University

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- DEGREE_SCOPED_PAGINATED: Swiftype course search (saved sample: course_listing/pagination.html) ---
# Listing auto-paginates from PAGE_1 using "Displaying X-Y of Z results" (10 per page).
UNDERGRADUATE_COURSE_LISTING_PAGE_1=https://www.mmu.ac.uk/study/course-search/search/?page=1&sta=course&stl=Undergraduate,Postgraduate&study_mode=full_time
UNDERGRADUATE_COURSE_LISTING_PAGE_2=https://www.mmu.ac.uk/study/course-search/search/?page=2&sta=course&stl=Undergraduate,Postgraduate&study_mode=full_time

POSTGRADUATE_COURSE_LISTING_PAGE_1=
POSTGRADUATE_COURSE_LISTING_PAGE_2=

POSTGRADUATE_RESEARCH_COURSE_LISTING_PAGE_1=
POSTGRADUATE_RESEARCH_COURSE_LISTING_PAGE_2=

FOUNDATION_COURSE_LISTING_PAGE_1=
FOUNDATION_COURSE_LISTING_PAGE_2=

# Legacy single-programme keys (optional fallback):
# LISTING_PROGRAMME=undergraduate
# COURSE_LISTING_PAGE_1=
# COURSE_LISTING_PAGE_2=

# --- ALL_COURSE: offline smoke-test only (pagination.html SSR has ~10 course links on page 1) ---
# STRATEGY=ALL_COURSE
# COURSE_CATALOGUE_URL=https://www.mmu.ac.uk/study/course-search/search/?page=1&sta=course&stl=Undergraduate,Postgraduate&study_mode=full_time
# COURSE_CATALOGUE_HTML=../course_listing/pagination.html

UNIVERSITY_BASE_URL=https://www.mmu.ac.uk

UNIVERSITY_BASE_URL=https://www.mmu.ac.uk

# Cloudflare + CDP: code/CLOUDFLARE-CDP.md | docs/shared/cloudflare-course-download.md

# Course URL listing — browser pagination via CDP (see CLOUDFLARE-CDP.md)
COURSE_LISTING_FETCH=browser
# Swiftype fallback (no browser): COURSE_LISTING_FETCH=swiftype
SWIFTYPE_ENGINE_KEY=yxx_JtAeyygPkQNS-jYj

# Course page download — CDP (see CLOUDFLARE-CDP.md)
COURSE_DOWNLOAD_USE_DEVICE_PROFILE=false
COURSE_DOWNLOAD_CDP_URL=http://127.0.0.1:9222
COURSE_DOWNLOAD_BROWSER=brave
COURSE_DOWNLOAD_HEADLESS=false

# Optional — only scan matching anchors (blank = all <a href>)
COURSE_LINK_SELECTOR=.results-container a[href*="/study/undergraduate/course/"], .results-container a[href*="/study/postgraduate/course/"], .results-container a[href*="/study/postgraduate-research/course/"]

# Course detail paths (from pagination.html + course-details.html):
COURSE_PATH_PATTERNS="^/study/undergraduate/course/[a-z0-9][a-z0-9-]*$
^/study/postgraduate/course/[a-z0-9][a-z0-9-]*$
^/study/postgraduate-research/course/[a-z0-9][a-z0-9-]*$"

# --- Study-level URL split (path prefix + award tokens in slug) ---
UNDERGRADUATE_URL_PATTERNS="
^/study/undergraduate/course/
(?:^|[-_/])(?:bsc|ba|beng|llb|mbchb|moptom|mpharm)(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
^/study/postgraduate/course/
(?:^|[-_/])(?:msc|mba|llm|pgdip|pgcert|ma|march|mres)(?:[-_/]|$)
"

POSTGRADUATE_RESEARCH_URL_PATTERNS="
^/study/postgraduate-research/course/
(?:^|[-_/])(?:phd|mres|engd|psychd)(?:[-_/]|$)
"

FOUNDATION_URL_PATTERNS="
foundation
international/college
"

EXCLUDED_COURSE_PATHS="
/study/course-search
"

EXCLUDED_PATH_PREFIXES="
/study/undergraduate/before-you-apply
/study/postgraduate/how-to-apply
/study/open-days
/study/international/before-you-apply
"

# --- Course page cleaning (tune using course_detail/ samples) ---
COURSE_PAGE_TITLE_SELECTOR=#main-content h1

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=plugin

COURSE_CLEAN_BLOCKS="
Fact file :: section[aria-labelledby=fact-file-title]
Fees and funding :: #fees
Entry requirements :: #mmu-entry-requirements
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
"

# --- uni_req source URLs (JSON saves without browser URL metadata) ---
# html_stem :: canonical page URL (matches uni_req/*.html filename stem)
UNI_REQ_SOURCE_URLS="
bangladesh-entry :: https://www.mmu.ac.uk/study/international/international-students/bangladesh
english-requirements :: https://www.mmu.ac.uk/study/international/before-you-apply/english-language-requirements
scholarships :: https://www.mmu.ac.uk/study/international/before-you-apply/fees-and-funding/scholarships-and-funding
deposit :: https://www.mmu.ac.uk/study/international/when-you-have-an-offer/apply-for-cas
"

# --- LLM extract: reads output/clean/courses directly (not presetup / pre_setup_course) ---
# Index: output/courses.csv (auto-built from clean/courses; skips .md with no source_url in frontmatter)
#
# From repo root (Ollama running):
#   python -u "Manchester Metropolitan University/code/run_llm_from_clean.py" --all --resume
#   python -u "Manchester Metropolitan University/code/run_llm_from_clean.py" --limit 5
#
# Equivalent shared entry points:
#   python -u shared/run_course_pipeline.py --code-dir "Manchester Metropolitan University/code" --llm-only --all --resume
#   python -u shared/run_llm_to_dev_csv.py --code-dir "Manchester Metropolitan University/code" --resume
#
# Rebuild index only:
#   python -u "Manchester Metropolitan University/code/build_course_index.py"
#
# Uni clean must pass validate_uni_clean before extract (english-requirements needs JSON array).
# Temporary course-only smoke test: add --skip-uni-validation to shared/run_course_pipeline.py --llm-only
# (run_llm_from_clean.py does not pass that flag by default).
#
# Stage 2 — course IELTS priority (IELTS under Entry requirements on MMU course pages):
#   1) Stage 1 parser reads IELTS from full course markdown (wins on ieltsMinOverall/Section)
#   2) Stage 2 enrich uses course English before uni english-requirements.json
#   3) With ENGLISH_SOURCE=course, uni JSON is not used for English lookup
LLM_STAGE2_ENGLISH_SOURCE=course
LLM_STAGE2_UNI_PARTS=entry,scholarship,deposit
LLM_STAGE2_ENGLISH_SECTIONS="
Entry requirements
"
