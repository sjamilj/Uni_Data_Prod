UNIVERSITY_NAME=University of Hertfordshire

STRATEGY=DEGREE_SCOPED_PAGINATED

# --- DEGREE_SCOPED_PAGINATED: listing page URLs (one pair per programme per start month) ---
# PAGE_1/2 = September, PAGE_3/4 = January (courseStartDate facet).
# Or: scrape --append-urls --listing-start-date january (uses PAGE_1/2 templates only).
COURSE_LISTING_START_DATE=september

UNDERGRADUATE_COURSE_LISTING_PAGE_1=https://www.herts.ac.uk/courses/search?f.Start+date%7CcourseStartDate=september&facetScope=f.Tabs%7Cuoh%7Edxp-dev_ds-higher-education-courses%3DCourses&f.Open+to+International%7CcourseInternational=Yes&form=simple&profile=_default&f.Attendance%7CcourseStudyType=full+time&collection=uoh%7Edxp-dev_sp-higher-education-meta&f.Course+type%7CcourseType=undergraduate&displayMode=list&start_rank=0
UNDERGRADUATE_COURSE_LISTING_PAGE_2=https://www.herts.ac.uk/courses/search?f.Start+date%7CcourseStartDate=september&facetScope=f.Tabs%7Cuoh%7Edxp-dev_ds-higher-education-courses%3DCourses&f.Open+to+International%7CcourseInternational=Yes&form=simple&profile=_default&f.Attendance%7CcourseStudyType=full+time&collection=uoh%7Edxp-dev_sp-higher-education-meta&f.Course+type%7CcourseType=undergraduate&displayMode=list&start_rank=11
UNDERGRADUATE_COURSE_LISTING_PAGE_3=https://www.herts.ac.uk/courses/search?f.Start+date%7CcourseStartDate=january&facetScope=f.Tabs%7Cuoh%7Edxp-dev_ds-higher-education-courses%3DCourses&f.Open+to+International%7CcourseInternational=Yes&form=simple&profile=_default&f.Attendance%7CcourseStudyType=full+time&collection=uoh%7Edxp-dev_sp-higher-education-meta&f.Course+type%7CcourseType=undergraduate&displayMode=list&start_rank=0
UNDERGRADUATE_COURSE_LISTING_PAGE_4=https://www.herts.ac.uk/courses/search?f.Start+date%7CcourseStartDate=january&facetScope=f.Tabs%7Cuoh%7Edxp-dev_ds-higher-education-courses%3DCourses&f.Open+to+International%7CcourseInternational=Yes&form=simple&profile=_default&f.Attendance%7CcourseStudyType=full+time&collection=uoh%7Edxp-dev_sp-higher-education-meta&f.Course+type%7CcourseType=undergraduate&displayMode=list&start_rank=11

POSTGRADUATE_COURSE_LISTING_PAGE_1=https://www.herts.ac.uk/courses/search?f.Start+date%7CcourseStartDate=september&facetScope=f.Tabs%7Cuoh%7Edxp-dev_ds-higher-education-courses%3DCourses&f.Open+to+International%7CcourseInternational=Yes&form=simple&profile=_default&f.Attendance%7CcourseStudyType=full+time&collection=uoh%7Edxp-dev_sp-higher-education-meta&f.Course+type%7CcourseType=postgraduate&displayMode=list&start_rank=0
POSTGRADUATE_COURSE_LISTING_PAGE_2=https://www.herts.ac.uk/courses/search?f.Start+date%7CcourseStartDate=september&facetScope=f.Tabs%7Cuoh%7Edxp-dev_ds-higher-education-courses%3DCourses&f.Open+to+International%7CcourseInternational=Yes&form=simple&profile=_default&f.Attendance%7CcourseStudyType=full+time&collection=uoh%7Edxp-dev_sp-higher-education-meta&f.Course+type%7CcourseType=postgraduate&displayMode=list&start_rank=11
POSTGRADUATE_COURSE_LISTING_PAGE_3=https://www.herts.ac.uk/courses/search?f.Start+date%7CcourseStartDate=january&facetScope=f.Tabs%7Cuoh%7Edxp-dev_ds-higher-education-courses%3DCourses&f.Open+to+International%7CcourseInternational=Yes&form=simple&profile=_default&f.Attendance%7CcourseStudyType=full+time&collection=uoh%7Edxp-dev_sp-higher-education-meta&f.Course+type%7CcourseType=postgraduate&displayMode=list&start_rank=0
POSTGRADUATE_COURSE_LISTING_PAGE_4=https://www.herts.ac.uk/courses/search?f.Start+date%7CcourseStartDate=january&facetScope=f.Tabs%7Cuoh%7Edxp-dev_ds-higher-education-courses%3DCourses&f.Open+to+International%7CcourseInternational=Yes&form=simple&profile=_default&f.Attendance%7CcourseStudyType=full+time&collection=uoh%7Edxp-dev_sp-higher-education-meta&f.Course+type%7CcourseType=postgraduate&displayMode=list&start_rank=11

POSTGRADUATE_RESEARCH_COURSE_LISTING_PAGE_1=https://www.herts.ac.uk/courses/search?f.Start+date%7CcourseStartDate=september&facetScope=f.Tabs%7Cuoh%7Edxp-dev_ds-higher-education-courses%3DCourses&f.Open+to+International%7CcourseInternational=Yes&form=simple&profile=_default&f.Attendance%7CcourseStudyType=full+time&collection=uoh%7Edxp-dev_sp-higher-education-meta&f.Course+type%7CcourseType=research&displayMode=list&start_rank=0
POSTGRADUATE_RESEARCH_COURSE_LISTING_PAGE_2=https://www.herts.ac.uk/courses/search?f.Start+date%7CcourseStartDate=september&facetScope=f.Tabs%7Cuoh%7Edxp-dev_ds-higher-education-courses%3DCourses&f.Open+to+International%7CcourseInternational=Yes&form=simple&profile=_default&f.Attendance%7CcourseStudyType=full+time&collection=uoh%7Edxp-dev_sp-higher-education-meta&f.Course+type%7CcourseType=research&displayMode=list&start_rank=11
POSTGRADUATE_RESEARCH_COURSE_LISTING_PAGE_3=https://www.herts.ac.uk/courses/search?f.Start+date%7CcourseStartDate=january&facetScope=f.Tabs%7Cuoh%7Edxp-dev_ds-higher-education-courses%3DCourses&f.Open+to+International%7CcourseInternational=Yes&form=simple&profile=_default&f.Attendance%7CcourseStudyType=full+time&collection=uoh%7Edxp-dev_sp-higher-education-meta&f.Course+type%7CcourseType=research&displayMode=list&start_rank=0
POSTGRADUATE_RESEARCH_COURSE_LISTING_PAGE_4=https://www.herts.ac.uk/courses/search?f.Start+date%7CcourseStartDate=january&facetScope=f.Tabs%7Cuoh%7Edxp-dev_ds-higher-education-courses%3DCourses&f.Open+to+International%7CcourseInternational=Yes&form=simple&profile=_default&f.Attendance%7CcourseStudyType=full+time&collection=uoh%7Edxp-dev_sp-higher-education-meta&f.Course+type%7CcourseType=research&displayMode=list&start_rank=11

# Legacy single-programme keys (optional fallback):
# LISTING_PROGRAMME=undergraduate
# COURSE_LISTING_PAGE_1=
# COURSE_LISTING_PAGE_2=

# --- ALL_COURSE: saved catalogue HTML (use course_listing/ short names or full paths) ---
# STRATEGY=ALL_COURSE
# COURSE_CATALOGUE_URL=
# COURSE_CATALOGUE_HTML=../course_listing/all_course.html
# UNDERGRADUATE_COURSE_CATALOGUE_HTML=
# POSTGRADUATE_COURSE_CATALOGUE_HTML=
# POSTGRADUATE_RESEARCH_COURSE_CATALOGUE_HTML=
# FOUNDATION_COURSE_CATALOGUE_HTML=

UNIVERSITY_BASE_URL=https://www.herts.ac.uk

# --- Browser for listing scrape / course download ---
# CDP off: leave COURSE_DOWNLOAD_CDP_URL empty → Playwright launches its own Chromium.
# If herts.ac.uk blocks automation, set CDP again (see CLOUDFLARE-CDP.md).
COURSE_DOWNLOAD_USE_DEVICE_PROFILE=false
COURSE_DOWNLOAD_CDP_URL=
COURSE_DOWNLOAD_CLOUDFLARE_WARMUP=false
COURSE_DOWNLOAD_CLOUDFLARE_AUTO_CLICK=false
COURSE_DOWNLOAD_HEADLESS=false
COURSE_LISTING_FETCH=browser
COURSE_DOWNLOAD_CLOUDFLARE_WAIT_SECONDS=300

# Optional — only scan matching anchors (blank = all <a href>)
# COURSE_LINK_SELECTOR=a.course-card-link

# Course URL path regex (one per line). Leaf course paths from search results.
COURSE_PATH_PATTERNS="
^/courses/undergraduate/[^/]+$
^/courses/postgraduate-masters/[^/]+$
^/courses/research/[^/]+$
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
"

EXCLUDED_PATH_PREFIXES="
/courses/undergraduate-courses
/courses/postgraduate-masters-study
"

# --- Course page cleaning (tune using course_detail/course-details.html) ---
COURSE_PAGE_TITLE_SELECTOR=h1.course-hero-heading

# generic (default) | utopian (ARU) | plugin | auto
COURSE_CLEAN_ENGINE=generic

COURSE_CLEAN_BLOCKS="
Key course information :: #herts-stage1-facts
Entry requirements :: #entryRequirements
Fees and funding :: #fees
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
4 :: UK Students
4 :: EU Students
"

# --- uni_req source URLs (JSON saves without browser URL metadata) ---
# html_stem :: canonical page URL (matches uni_req/*.html filename stem)
UNI_REQ_SOURCE_URLS="
bangladesh-entry :: https://www.herts.ac.uk/international/apply/application-requirements
english-requirements :: https://www.herts.ac.uk/international/apply/application-requirements
scholarships :: https://www.herts.ac.uk/international/scholarships-and-fees/scholarships
deposit :: https://www.herts.ac.uk/international/apply/application-requirements
"
