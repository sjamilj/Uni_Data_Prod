# University of Auckland
UNIVERSITY_NAME=University of Auckland
# Catalogue strategy — single page listing all courses.

STRATEGY=ALL_COURSE

# Full URL of the catalogue page (from the saved-from comment in all_course.html)
COURSE_CATALOGUE_URL=https://www.auckland.ac.nz/en/study/study-options/find-a-study-option.html?programmeType=bachelors,bachelors-honours,doctorates,masters,undergraduate-diploma

# Offline saved catalogue HTML (put file in course_listing/)
COURSE_CATALOGUE_HTML=../course_listing/all_course.html

# Domain base for resolving relative course links
UNIVERSITY_BASE_URL=https://www.auckland.ac.nz

# Path regexes that identify a degree-level course page
COURSE_PATH_PATTERNS="
^/en/study/study-options/find-a-study-option/(?:executive-)?(?:bachelor|master|doctor)-[a-z0-9\-]+\.html$
"

# --- Study-level URL split (fallback when a catalogue is not degree-scoped) ---
UNDERGRADUATE_URL_PATTERNS="
(?:^|[-_/])bachelor(?:[-_/]|$)
"

POSTGRADUATE_URL_PATTERNS="
(?:^|[-_/])master(?:[-_/]|$)
"

POSTGRADUATE_RESEARCH_URL_PATTERNS="
(?:^|[-_/])(?:doctor|phd)(?:[-_/]|$)
"

FOUNDATION_URL_PATTERNS="
foundation
"

EXCLUDED_COURSE_PATHS="
/en/study/study-options
/en/study/study-options/find-a-study-option
/en/study/study-options/undergraduate-study-options
/en/study/study-options/postgraduate-study-options
/en/study/study-options/professional-development-and-short-courses
/en/study/study-options/course-information
/en/study/study-options/360-international
"
EXCLUDED_PATH_PREFIXES="
/en/news/
/en/about-us/
/en/students/
/en/research/
/en/on-campus/
/en/alumni
/en/staff
/en/giving
/en/library
"

# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---

COURSE_PAGE_TITLE_SELECTOR=h1.banner__heading

COURSE_CLEAN_ENGINE=generic

# Selectors are content-based (:has) rather than #section1/#section3 ids,
# because tab ids can shift between programmes.
COURSE_CLEAN_BLOCKS="
Quick facts :: .quick-facts
Entry requirements :: .uoa-tabs__content:has(.entry-req)
Fees and scholarships :: .uoa-tabs__content:has(.fees-box)
Key dates :: .uoa-tabs__content:has(.closing-dates__container)
"

COURSE_CLEAN_STRIP_WITHIN="
script
noscript
style
iframe
svg
.calendar-disclaimer
.prog-structure__expand-btn
#domestic-qualifications
.entry-req__section.always-shown
.entry-req__section:has(#area-country-selection)
"

COURSE_CLEAN_EXPAND_TABS=true

COURSE_CLEAN_EXPAND_TABS=true

COURSE_MARKDOWN_REMOVE_SECTIONS="
2 :: Programme overview
2 :: Programme structure
3 :: Sample programme structure
4 :: Student loans and allowances
4 :: Cost of living
3 :: Other important dates
2 :: Portfolio guidelines
2 :: Careers and further study
2 :: Where could this programme take you?
3 :: Jobs related to this programme
3 :: Further study options
3 :: Student career planning service
4 :: Scholarships and awards
3 :: Start dates
3 :: How to apply
"