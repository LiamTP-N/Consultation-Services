"""
================================================================
SCRAPE.PY - automated job scraper for the jobs board (Phase 3)
================================================================

Purpose
-------
Pulls fresh job postings from multiple UK and Canadian sources,
tags each with applicable categories from a CV-anchored dictionary,
computes a per-job fit score weighted to Liam's profile, dedupes
across sources, and writes the result to jobs.json for the static
site (jobs.html) to render client-side.

Sources (Phase 3)
-----------------
UK:
  - Jobs.ac.uk RSS (12 feeds)
  - Adzuna API UK (opt-in)
  - Reed.co.uk Jobseeker API (opt-in)
  - Bluesky

Canada:
  - THEunijobs Canada RSS
  - HigherEdJobs RSS (2 category feeds)
  - University Affairs HTML
  - Adzuna API Canada (opt-in)

Industry (global, country inferred from location):
  - Greenhouse Job Board API (curated list of health-tech /
    sport-tech companies: WHOOP, Oura, Strava, Hinge Health,
    Sword Health, Catapult, Hudl, Stats Perform, etc.)
  - Lever Postings API (curated list: Eight Sleep, Polar, Garmin,
    STATSports, Kitman Labs, Output Sports, etc.)

Greenhouse and Lever both expose public, unauthenticated JSON
endpoints per company. Edit GREENHOUSE_COMPANIES / LEVER_COMPANIES
at the top of the file to add or remove employers.

Adzuna integration
------------------
Adzuna offers a free-tier REST API covering UK + Canada with 
generous rate limits. Activate by setting two GitLab CI variables:
  ADZUNA_APP_ID, ADZUNA_APP_KEY (register at developer.adzuna.com)
Without them the Adzuna step is silently skipped.

Reed integration
-----------------
Reed.co.uk offers a free Jobseeker API (UK only). Activate by setting
one GitLab CI variable:
  REED_API_KEY (register at https://www.reed.co.uk/developers/jobseeker)
Auth is HTTP Basic with the key as username and empty password.
Without it the Reed step is silently skipped. Added to close the
FE/college-sector coverage gap that the academic-skewed and US-skewed
sources miss.

Categorisation
--------------
CATEGORY_KEYWORDS dict maps each category to keyword list. A job is
tagged with every matching category. Zero matches => rejected.
EXCLUDE_KEYWORDS retained from Phase 1 (slimmed; clinical-medical
roles only).

Fit score (NEW in Phase 2)
--------------------------
Each job gets a numeric `fit_score` based on weighted category
matches. Weights live in CATEGORY_WEIGHTS at the top of the file.
Higher weights = roles Liam's CV most directly supports. The
frontend sorts and filters by fit_score so the strongest matches
surface first.

Output: jobs.json shape unchanged from Phase 1 except `fit_score`
field is added to each job (int, 0-100 normalised).
"""

import json
import os
import hashlib
import html as html_module
import time
import datetime
import re
import urllib.parse
from pathlib import Path
from email.utils import parsedate_to_datetime

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    raise SystemExit("Install dependencies: pip install requests beautifulsoup4 lxml")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
}

# ---------------------------------------------------------------------------
# KEYWORD MATCHING (Phase 4: word-boundary, 17 Jun 2026)
# ---------------------------------------------------------------------------
# Earlier phases used naive `kw in text` substring matching. That let short
# tokens match inside unrelated words and flooded the board:
#   "rse"  matched cou(rse), dive(rse), unive(rse), wo(rse)  -> 225 false hits,
#          dragging Finance/Sales/HVAC roles into `technician`.
#   "imu"  matched min(imu)m, opt(imu)m, st(imu)lating         -> 61 false hits
#          in `health_tech`.
# Fix: compile each keyword as a whole-token regex (\b...\b). Multi-word
# phrases ("sport science") still match as a contiguous phrase. Matching is
# cached per run.

_KW_RE_CACHE: dict = {}


def _kw_regex(kw: str):
    rx = _KW_RE_CACHE.get(kw)
    if rx is None:
        rx = re.compile(r"\b" + re.escape(kw) + r"\b")
        _KW_RE_CACHE[kw] = rx
    return rx


def kw_in(kw: str, text: str) -> bool:
    return _kw_regex(kw).search(text) is not None


# ---------------------------------------------------------------------------
# CATEGORY-TAGGED KEYWORDS (Phase 2)
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS = {
    "academic_sport": [
        "sport science", "sports science", "exercise science",
        "exercise physiology", "sport and exercise", "sports and exercise",
        "biomechanics", "biomechanist", "strength and conditioning",
        "sport psychology", "sports psychology", "sport coaching",
        "sport nutrition", "sports nutrition",
        # Sport/leisure leadership (council/trust/charity), so senior
        # "Head of Sport" posts score on fit, not just pass the filter.
        "head of sport", "head of physical activity",
        "sport and physical activity", "head of leisure",
    ],
    "academic_adjacent": [
        "kinesiology", "human kinetics", "human movement", "movement science",
        "motor control", "motor learning", "skill acquisition",
        "rehabilitation science", "rehabilitation research", "physical therapy research",
        "sport rehabilitation", "sports rehabilitation", "sport injury", "sports injury",
        "sport therapy", "sports therapy", "musculoskeletal health",
        "gerontology", "ageing research", "aging research", "healthy ageing", "healthy aging",
        "public health", "population health", "epidemiology",
        "physical activity", "physical education",
        "musculoskeletal research", "neuromuscular",
        # Phase 8 (19 Aug 2026): clinical / ageing strand. The board had no
        # clinical vocabulary beyond "rehabilitation science", so clinical
        # exercise physiology and BFR/ageing posts, i.e. Liam's actual research
        # population, were scoring on generic sport terms only. "clinical
        # exercise" and "older adults" are boilerplate-prone in university and
        # med-device blurb, so both sit in TITLE_ONLY_KEYWORDS below.
        "clinical exercise physiology", "clinical exercise",
        "cardiac rehabilitation", "pulmonary rehabilitation",
        "sarcopenia", "frailty", "falls prevention",
        "older adults", "long-term conditions",
        "blood flow restriction", "stroke rehabilitation",
        "clinical populations", "exercise oncology",
    ],
    "technician": [
        "lab technician", "laboratory technician", "research technician",
        "senior technician", "technical specialist", "technical officer",
        "lab manager", "laboratory manager", "facility manager",
        "research software engineer",
        "research assistant",
    ],
    "data_science": [
        "data scientist", "data science", "data analyst", "data engineer",
        "machine learning", "ml engineer", "ai engineer",
        "applied scientist", "research scientist",
        "python developer", "computational scientist",
        "quantitative analyst", "bioinformatic", "health data",
        "statistical programmer", "biostatistic",
    ],
    "health_tech": [
        "digital health", "health technology", "health tech",
        "medical device", "medical technology", "medtech",
        "mhealth", "ehealth", "telehealth", "telemedicine",
        "wearable", "wearables", "inertial sensor", "imu sensor",
        "clinical software", "clinical informatics", "nhs digital",
        "health informatics", "digital therapeutic",
        "computer vision health", "pose estimation",
        # Phase 7 (18 Aug 2026): measurement-technology vendor roles, i.e. the
        # kit Liam actually teaches and researches on. Word-boundary matching
        # keeps the short tokens ("emg", "hd-semg") safe.
        "motion capture", "markerless", "motion analysis",
        "optical tracking", "gait analysis",
        "emg", "hd-semg", "surface electromyography", "electromyography",
        "force plate", "force platform", "isokinetic",
    ],
    "fe_he_teaching": [
        "lecturer", "senior lecturer", "principal lecturer",
        "assistant professor", "associate professor", "professor",
        "teaching fellow", "teaching associate", "tutor",
        "course leader", "programme leader", "programme director",
        "curriculum developer", "curriculum designer", "curriculum lead",
        "internal quality assurance", "iqa", "external quality assurance", "eqa",
        "assessor", "internal verifier", "external verifier",
        "head of teaching", "head of department",
        "instructor", "academic skills",
        # FE/college-sector leadership (broadened with Reed source)
        "head of college", "head of faculty", "head of curriculum",
        "curriculum manager", "head of youth", "college leadership",
        "vice principal", "deputy principal", "head of school",
    ],
    "research_mgmt": [
        "research manager", "research coordinator", "research operations",
        "research administrator", "research office", "research officer",
        "grants officer", "grants manager", "research funding",
        "ethics officer", "ethics coordinator", "research integrity",
        "research impact", "knowledge exchange", "research development",
        "programme manager research", "research programme manager",
        "research strategy",
    ],
    "industry_applied": [
        "performance analyst", "performance scientist",
        "strength coach", "s&c coach", "conditioning coach",
        "sport scientist", "applied sport scientist",
        "consulting biomechanist", "movement specialist",
        "exercise specialist", "exercise physiologist",
        "athlete development",
        # Phase 3: industry sport-tech / health-tech roles
        "product manager health", "product manager sport",
        "sports technology", "sports tech",
        "applied research scientist", "applied scientist sport",
        "motion capture engineer", "biomechanics engineer",
        "sensor engineer", "wearable engineer",
        "computer vision engineer", "ml researcher sport",
        "physiology researcher industry", "fitness research",
        # Phase 8: "clinical exercise" MOVED to academic_adjacent (double-scored
        # here otherwise). Do not reinstate in this list.
        # Phase 7 (18 Aug 2026): elite / motorsport human-performance roles.
        # F1 and its suppliers file these under "human performance" or
        # "athlete performance" rather than "sport science", which is why no
        # existing keyword reached them.
        "human performance", "athlete performance", "driver performance",
        "performance coach", "performance physiologist",
        "motorsport", "human factors", "driver in the loop",
    ],
    "research_postdoc": [
        "research fellow", "postdoc", "postdoctoral",
        "research associate", "phd studentship", "doctoral researcher",
        "doctoral candidate", "studentship",
    ],
}

# Category weights for fit_score calculation.
# Higher = better match to Liam's CV/cover-letter profile. These are
# tunable - bias is currently toward academic+biomech and the data/
# health-tech crossover (Liam's strongest narratives), with FE teaching
# and pure industry weighted lower.
CATEGORY_WEIGHTS = {
    "academic_sport":    25,
    "academic_adjacent": 22,  # Phase 8: 18 -> 22, rehab/clinical/ageing IS the research
    "research_postdoc":  18,  # Phase 8: 15 -> 18, research trajectory is the logged gap
    "technician":        14,  # Phase 8: 20 -> 14, stays visible, stops topping the board
    "data_science":      18,  # Phase 8: 22 -> 18, a method not a destination
    "health_tech":       20,  # Phase 8: 22 -> 20, RBE app, MediaPipe, NHS pathway
    "fe_he_teaching":    18,  # Phase 8: 15 -> 18, SFHEA + DTF + ~500 students
    "research_mgmt":     10,  # Phase 8: 12 -> 10
    "industry_applied":  15,  # Phase 3: bumped from 10 (sport/health-tech industry weight)
}

# Cap to keep fit_score visually clean (0-100 scale)
FIT_SCORE_CAP = 100

# Title-only excludes (Phase 4, 17 Jun 2026). Some roles match a category
# only because the JOB DESCRIPTION mentions Liam-relevant phrases (e.g. a
# "Junior Sales Representative" at a medical-device firm, or a "Service
# Delivery Manager" whose blurb says "data science"). The role FUNCTION is
# wrong regardless of the employer's domain. These terms are matched against
# the TITLE only (word-boundary), so a genuine "Data Scientist" whose title
# lacks them is unaffected. Keep this list tight and title-shaped.
TITLE_EXCLUDE_KEYWORDS = [
    "sales representative", "sales executive", "sales advisor",
    "sales manager", "account executive", "account manager",
    "business development", "service delivery manager",
    "sales development", "product sales",
    "finance administrator", "finance coordinator",
    "finance manager", "finance analyst", "financial controller",
    "customer experience", "customer success",
    "store manager", "store associate", "retail",
    "recruitment", "talent acquisition",
]

EXCLUDE_KEYWORDS = [
    "clinical fellow", "junior fellow", "medical fellow", "surgical fellow",
    "haematology", "oncology", "cardiology", "anaesthetic", "radiographer",
    "pharmacist", "nurse", "nursing", "midwife",
    "physiotherapist", "occupational therapist",
    "urology", "gynaecology", "neurosurgery", "ophthalmology",
    "pathology", "dentist", "dental", "veterinary",
    "psychiatrist", "psychologist clinical",
    "speech and language", "speech therapist", "speech-language",
    "investment analyst", "financial analyst", "actuarial",
    "sales executive", "marketing executive", "hr business partner",
    "recruitment consultant",
    "tiktok", "anti-fraud",
]

# Title-only keywords (Phase 7, 18 Aug 2026). A dry run of the new Ashby source
# showed WHOOP alone putting 159 of its 263 postings on the board, including
# every iOS and Android engineer vacancy, because these particular phrases sit
# in the COMPANY BOILERPLATE that gets repeated in every description at a
# wearables or performance business: WHOOP describes itself as a "human
# performance company" and the word "wearable" appears in all of its blurbs. The
# phrases are still genuinely useful in a TITLE, which is where the F1 and
# elite-performance roles carry them ("Human Performance Coach", "Athlete
# Performance Scientist"), so rather than delete them they are restricted to
# title matching. Keep this list to phrases that are boilerplate-prone AND
# title-meaningful; anything else belongs in the ordinary keyword lists.
TITLE_ONLY_KEYWORDS = {
    "human performance", "athlete performance", "driver performance",
    "wearable", "wearables", "motorsport", "human factors",
    "sports technology", "sports tech", "fitness research",
    # Phase 8 (19 Aug 2026): same failure mode from the clinical strand.
    # "older adults" and "clinical exercise" appear in the boilerplate of
    # almost every university health-faculty advert and every med-device
    # blurb, so full-text matching would drag in unrelated administrative and
    # engineering posts. Both are meaningful in a TITLE ("Lecturer in Clinical
    # Exercise Physiology", "Research Fellow, Exercise in Older Adults").
    "older adults", "clinical exercise",
}

# Jobs.ac.uk (UK).
# Phase 5 (17 Jun 2026): the RSS service (`/jobs/{slug}/?format=rss`) began
# returning HTTP 500 on EVERY feed - confirmed from three independent networks
# while jobs.ac.uk's own RSS index still advertised those exact URLs, i.e. a
# broken/abandoned endpoint on their side, not a URL change. The `/jobs/{slug}/`
# HTML route 500s too. The working route is the search UI: `/search/{slug}`,
# which renders server-side HTML with job cards. Switched Jobs.ac.uk to an HTML
# scraper against that route (scrape_jobsac_html). Slugs are the academic
# subject-area slugs from https://www.jobs.ac.uk/feeds/subject-areas plus the
# professional-services slugs that exist under /search. If the RSS service comes
# back, the old JOBSAC_RSS_FEEDS list + scrape_jobsac_rss are retained below and
# can be reinstated in main().
JOBSAC_HTML_SLUGS = [
    "sport-and-leisure",
    "biological-sciences",
    "health-and-medical",
    "computer-sciences",
    "engineering-and-technology",
    "mathematics-and-statistics",
    "psychology",
    "senior-management",
    "project-management-and-consulting",
]

# Phase 6 (18 Jun 2026, corrected): result depth. scrape_jobsac_html originally
# read only the first results page per slug (25 cards). The first Phase-6 attempt
# appended `?page=N`, but jobs.ac.uk IGNORES that param (every page 2 returned
# the same 25 cards), so it was a no-op. The site's real mechanism, confirmed
# from the live "Next" link, is the canonical faceted search URL
#   /search/?academicDisciplineFacet[0]={slug}&pageSize=N&startIndex=M&sortOrder=1
# where pageSize sets results-per-page and startIndex is 1-based (1, 26, 51...).
# The friendly /search/{slug} alias is just this with pageSize=25,startIndex=1.
# We now request the canonical form with a larger pageSize so one fetch per slug
# returns up to JOBSAC_PAGE_SIZE cards instead of 25 - enough to catch on-profile
# roles filed under a busy discipline (e.g. a sport-rehab post indexed under
# biological-sciences / health-and-medical, which carry 250-400 jobs). sortOrder=1
# is Date Placed (newest first), so the freshest JOBSAC_PAGE_SIZE are covered.
JOBSAC_PAGE_SIZE = 100

# Retained (dormant) RSS feed list - reinstate if jobs.ac.uk fixes its RSS.
JOBSAC_RSS_FEEDS = [
    ("https://www.jobs.ac.uk/jobs/sport-and-leisure/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/laboratory-clinical-and-technician/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/health-and-medical/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/biological-sciences/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/nutrition/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/computer-sciences/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/professional-or-managerial/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/phds/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/studentships/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/engineering-and-technology/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/mathematics-and-statistics/?format=rss", "Jobs.ac.uk"),
]

# Canadian RSS feeds (THEunijobs Canada, HigherEdJobs)
CANADA_RSS_FEEDS = [
    (
        "https://www.timeshighereducation.com/unijobs/listings/canada/?format=rss",
        "THEunijobs",
    ),
    (
        "https://www.higheredjobs.com/rss/articleFeed.cfm?JobCat=161&Remote=0",
        "HigherEdJobs",
    ),
    (
        "https://www.higheredjobs.com/rss/articleFeed.cfm?JobCat=43&Remote=0",
        "HigherEdJobs",
    ),
]

BLUESKY_ACCOUNTS = [
    "jobsinsportscience.bsky.social",
]

# Phase 3: industry company ATS lists
# Greenhouse: free public API, no auth, no rate limit
# https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
# Tokens verified live as of 27 May 2026; prune dead ones from here
GREENHOUSE_COMPANIES = [
    # Health-tech / digital health
    ("oura", "Oura"),
    ("omadahealth", "Omada Health"),
    ("calm", "Calm"),
    ("myfitnesspal", "MyFitnessPal"),
    ("amwell", "Amwell"),
    ("doctolib", "Doctolib"),
    ("biofourmis", "Biofourmis"),
    ("hellofresh", "HelloFresh"),
    # Sport tech / performance
    ("catapultsports", "Catapult Sports"),
    ("hudl", "Hudl"),
    ("peloton", "Peloton"),
    ("tempo", "Tempo"),
    ("geniussports", "Genius Sports"),
    # AI / ML research (Liam's data-science narrative)
    ("deepmind", "DeepMind"),
    ("anthropic", "Anthropic"),
    # Phase 7 additions (18 Aug 2026), every token probed live and returning
    # a non-zero board on the day. Prune any that start logging HTTP 404.
    ("kinexon", "KINEXON"),          # sensor-based athlete tracking
    ("swordhealth", "Sword Health"),  # digital MSK rehab
    ("zwift", "Zwift"),
    ("iFIT", "iFIT"),                # NB token is case-sensitive
    ("gymshark", "Gymshark"),
]

# Lever: free public API, no auth
# https://api.lever.co/v0/postings/{client}?mode=json
# NB WHOOP was dropped 18 Aug 2026: its Lever board now returns 0 postings
# because the company has moved to Ashby (see ASHBY_COMPANIES).
LEVER_COMPANIES = [
    ("kitmanlabs", "Kitman Labs"),
]

# ---------------------------------------------------------------------------
# Phase 7 (18 Aug 2026): four more public ATS platforms
# ---------------------------------------------------------------------------
# Probing the measurement-technology, elite-performance and motorsport
# employers that matter most to Liam's profile showed that hardly any of them
# use Greenhouse or Lever, which is why the industry side of the board has been
# thin. They are spread across four other platforms, all of which expose an
# unauthenticated public endpoint in the same spirit as Greenhouse:
#   Ashby           https://api.ashbyhq.com/posting-api/job-board/{board}
#   SmartRecruiters https://api.smartrecruiters.com/v1/companies/{id}/postings
#   Recruitee       https://{account}.recruitee.com/api/offers/
#   Workable        https://apply.workable.com/api/v1/widget/accounts/{acct}
# Every identifier below was probed live on 18 Aug 2026 and returned a
# non-zero board. To add a company, find its identifier in the careers-page
# URL and append a tuple; a dead identifier logs a non-200 and is skipped.

ASHBY_COMPANIES = [
    ("whoop", "WHOOP"),
    ("teamworks", "Teamworks"),
    ("strava", "Strava"),
    ("tonal", "Tonal"),
    ("polar", "Polar"),
    ("egym", "eGym"),
]

# SmartRecruiters. Williams Racing is the one F1 team with a genuinely public
# postings API, so it is the only automatable route into an F1 team; the rest
# of the grid runs closed or JS-rendered portals and stays a manual watch-list.
# Red Bull is the whole drinks group rather than the race team, so it is high
# volume and mostly irrelevant - it is included because passes_filter is strict
# enough to bin the noise, and because the race team and Red Bull Technology
# postings do appear there. SMARTRECRUITERS_MAX_PAGES caps the quota cost.
SMARTRECRUITERS_COMPANIES = [
    ("williamsracing", "Williams Racing"),
    ("redbull", "Red Bull"),
    ("sportradar", "Sportradar"),
    ("kaiahealth", "Kaia Health"),
]
SMARTRECRUITERS_PAGE_SIZE = 100
SMARTRECRUITERS_MAX_PAGES = 3

# Recruitee. Movella is the parent of Xsens, whose IMU suites Liam teaches on,
# and both accounts serve the same board.
RECRUITEE_COMPANIES = [
    ("movella", "Movella (Xsens)"),
    ("alpine", "Alpine"),
    ("matrixfitness", "Matrix Fitness"),
]

# Workable. OptiTrack is optical motion capture, i.e. the direct comparator
# technology to the markerless work in MS05 Paper B.
WORKABLE_COMPANIES = [
    ("optitrack", "OptiTrack"),
    ("withings", "Withings"),
]

# Adzuna API: country code, country label, query list
# Queries chosen to span Liam's CV categories without burning quota.
# Lean 14-query UK-relevant set (10 Jun 2026): focused on sport/leisure +
# FE leadership, research/lab/technical, data/digital-health, and full
# lecturing + head-of-school/department teaching coverage. Kept lean to
# stay well inside the Adzuna free tier (14 queries x 2 countries/run).
# NB Find a Job (DWP) is Adzuna-powered, so this set also reaches much of
# that pool; Find a Job has no separate public feed to scrape.
ADZUNA_QUERIES = [
    # Research / lab / technical
    "research software engineer",
    "research technician",
    "data scientist health",
    "digital health",
    # Sport / exercise science
    "sport science",
    "biomechanics",
    "kinesiology",
    "sport rehabilitation",
    "assistant professor sport",
    # Sport / leisure / FE leadership
    "head of sport",
    "head of physical activity",
    "head of leisure",
    # Lecturing + head-of-school/department teaching
    "lecturer sport",
    "lecturer exercise",
    "head of department",
    "head of school",
]

# Adzuna Canada queries (Phase 7, 18 Aug 2026). Canada was previously run on
# the UK list, which searches for job titles Canadian employers do not use.
# Canadian sport/exercise departments are titled Kinesiology or Human Kinetics,
# the teaching ranks are assistant/associate professor and sessional/limited-term
# lecturer, and the technical-staff equivalent is core facility or lab
# coordinator. 16 queries, so quota use is unchanged.
ADZUNA_CA_QUERIES = [
    # Canadian academic naming conventions
    "kinesiology",
    "human kinetics",
    "assistant professor kinesiology",
    "assistant professor exercise",
    "sessional lecturer kinesiology",
    "limited term appointment kinesiology",
    "exercise physiology",
    "biomechanics",
    "rehabilitation science",
    # Research / technical / infrastructure
    "research technician",
    "laboratory coordinator",
    "core facility manager",
    "research associate exercise",
    # Data / health tech
    "data scientist health",
    "digital health",
    # Applied
    "sport scientist",
]

# Reed.co.uk Jobseeker API queries (UK only). Free key from
# https://www.reed.co.uk/developers/jobseeker, set REED_API_KEY env var.
# Broad coverage: CV-category terms PLUS FE/college-leadership terms that
# the academic-skewed sources (Jobs.ac.uk) and US-skewed sources
# (Greenhouse/Lever) systematically miss. Everything still passes through
# passes_filter (category match + exclude list) and fit scoring, so a wide
# net here does not flood the board with irrelevant commercial roles.
REED_QUERIES = [
    # CV categories
    "sport science",
    "biomechanics",
    "exercise physiology",
    "sport rehabilitation",
    "assistant professor sport",
    "research software engineer",
    "data scientist health",
    "digital health",
    "kinesiology",
    "research technician",
    "lab manager",
    "performance analyst",
    "strength and conditioning",
    # FE / HE college leadership (the gap that motivated this source)
    "head of college",
    "head of faculty",
    "head of department education",
    "college leadership",
    "curriculum manager",
    "head of curriculum",
    "lecturer sport",
    "programme leader",
    # Sport/leisure/active-wellbeing leadership (council, trust and charity
    # leisure posts: the role shape that the Glasgow Life advert exposed as a
    # gap; caught by academic_adjacent + fe_he_teaching once it arrives).
    "head of sport",
    "head of physical activity",
    "head of leisure",
    "head of sport and physical activity",
    "active wellbeing",
]

OUTPUT_FILE = Path("scraper/jobs.json")
MAX_DAYS_OLD = 20
MAX_FIELD_LEN = 500

# ---------------------------------------------------------------------------
# Indeed (UK) - best-effort, env-gated, OFF by default (Phase 6, 18 Jun 2026)
# ---------------------------------------------------------------------------
# Indeed was removed in Phase 1 (low signal/high noise) and the situation has
# since worsened: the free Publisher Jobs API (the only sanctioned job-search
# route) is deprecated, the site sits behind Cloudflare, a login wall kicks in
# from results page 2, and Indeed's ToS prohibits scraping. There is therefore
# NO clean free route. This scraper is a deliberate best-effort, ToS-grey
# fallback that reads ONLY the first server-rendered results page (the data
# Indeed still embeds in a JS blob before the Cloudflare/login wall) and never
# touches page 2+. Realistic expectation: from GitLab CI's shared/datacentre
# IPs it will frequently hit a Cloudflare interstitial and return 0; it is more
# likely to yield results when run from a residential IP (a local PC). It is
# OFF unless INDEED_ENABLE is set truthy, so a 0/blocked run never disrupts the
# pipeline and the grey-area request isn't made unless explicitly opted in.
#   Enable:  set CI/CD variable INDEED_ENABLE = 1   (and ideally run off-peak)
# If/when this proves unreliable, prefer a paid compliant API (Apify/HasData).
INDEED_ENABLE = os.environ.get("INDEED_ENABLE", "").strip().lower() in (
    "1", "true", "yes", "on"
)
INDEED_QUERIES = [
    "sport science",
    "sport rehabilitation",
    "exercise physiology",
    "biomechanics",
    "research technician",
    "lecturer sport",
]


def make_id(url: str, title: str) -> str:
    return hashlib.md5(f"{url}{title}".encode()).hexdigest()[:16]


def clean(text: str) -> str:
    if not text:
        return ""
    try:
        soup = BeautifulSoup(str(text), "html.parser")
        for bad in soup(["script", "style"]):
            bad.decompose()
        stripped = soup.get_text(separator=" ")
    except Exception:
        stripped = str(text)
    stripped = html_module.unescape(html_module.unescape(stripped))
    stripped = re.sub(r"\s+", " ", stripped).strip()
    stripped = "".join(ch for ch in stripped if ord(ch) >= 32 or ch in "\t")
    if len(stripped) > MAX_FIELD_LEN:
        stripped = stripped[:MAX_FIELD_LEN].rstrip() + "..."
    return stripped


def clean_url(url: str) -> str:
    if not url:
        return ""
    url = str(url).strip()
    if any(ord(ch) < 32 for ch in url):
        return ""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme.lower() in ("http", "https") and parsed.netloc:
            return urllib.parse.urlunparse(parsed)
    except Exception:
        pass
    return ""


def categorise(job: dict) -> list:
    text = (
        f"{job.get('title', '')} "
        f"{job.get('organisation', '')} "
        f"{job.get('type', '')} "
        f"{job.get('description', '')}"
    ).lower()
    title = (job.get("title", "") or "").lower()
    matched = []
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            # Phase 7: boilerplate-prone phrases only count in the title.
            haystack = title if kw in TITLE_ONLY_KEYWORDS else text
            if kw_in(kw, haystack):
                matched.append(cat)
                break
    return matched


def compute_fit_score(categories: list) -> int:
    """Sum the weights of all matched categories, cap at FIT_SCORE_CAP.
    A single strong match scores ~20-25; a multi-tagged crossover role
    (e.g. RSE on rehab apps tagged data_science + health_tech + technician)
    scores 60+."""
    if not categories:
        return 0
    total = sum(CATEGORY_WEIGHTS.get(c, 0) for c in categories)
    return min(total, FIT_SCORE_CAP)


def passes_filter(job: dict) -> bool:
    title = job.get("title", "").lower()
    for kw in TITLE_EXCLUDE_KEYWORDS:
        if kw_in(kw, title):
            return False
    text = (
        f"{job.get('title', '')} "
        f"{job.get('organisation', '')} "
        f"{job.get('type', '')} "
        f"{job.get('description', '')}"
    ).lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw_in(kw, text):
            return False
    cats = categorise(job)
    if not cats:
        return False
    job["categories"] = cats
    job["fit_score"] = compute_fit_score(cats)
    return True


def load_existing() -> dict:
    if OUTPUT_FILE.exists():
        try:
            return json.loads(OUTPUT_FILE.read_text())
        except Exception:
            pass
    return {"last_updated": None, "jobs": []}


def save(data: dict):
    data["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"
    OUTPUT_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"Saved {len(data['jobs'])} jobs to {OUTPUT_FILE}")


def prune_old(jobs: list) -> list:
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=MAX_DAYS_OLD)
    kept = []
    for j in jobs:
        dp = j.get("date_posted")
        if dp:
            try:
                if datetime.datetime.fromisoformat(dp.replace("Z", "")) > cutoff:
                    kept.append(j)
            except Exception:
                # Unparseable date -> treat as stale, drop it.
                pass
        # No date_posted at all -> stale/legacy, drop it. (Previously these
        # were kept forever, which is why the board grew past 1,000 jobs.)
    return kept


def backfill_categories(jobs: list) -> list:
    """Re-categorise + re-score every existing entry under the CURRENT keyword
    rules and matcher, then drop anything that no longer matches.

    Phase 4 (17 Jun 2026): this used to only fill categories on entries that
    lacked them, so when the matcher tightened (word-boundary) the ~900 jobs
    already tagged under the old naive substring rules kept their stale, often
    false-positive categories and never got cleaned. Now every run re-runs
    categorise() on the whole store, so a tightened rule self-heals the board
    on the next scrape. Entries that match nothing under the new rules are
    returned with an empty category list and removed below."""
    cleaned = []
    for j in jobs:
        title = j.get("title", "").lower()
        if any(kw_in(kw, title) for kw in TITLE_EXCLUDE_KEYWORDS):
            continue  # wrong-function role (sales/delivery/retail etc.)
        cats = categorise(j)
        if not cats:
            continue  # no longer relevant under current rules -> drop
        j["categories"] = cats
        j["fit_score"] = compute_fit_score(cats)
        cleaned.append(j)
    return cleaned


def deduplicate(jobs: list) -> list:
    """Union categories across duplicates and recompute fit_score from
    the unioned set."""
    seen = {}
    unique = []
    for j in jobs:
        key = (
            j.get("title", "").strip().lower(),
            j.get("organisation", "").strip().lower(),
            j.get("source", "").strip().lower(),
        )
        if key not in seen:
            seen[key] = j
            unique.append(j)
        else:
            existing_cats = set(seen[key].get("categories", []))
            new_cats = set(j.get("categories", []))
            merged = sorted(existing_cats | new_cats)
            seen[key]["categories"] = merged
            seen[key]["fit_score"] = compute_fit_score(merged)
    return unique


def get(url: str, timeout: int = 15) -> requests.Response | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"  GET failed {url[:80]}: {e}")
        return None


def parse_rss_date(date_str: str) -> str:
    if not date_str:
        return datetime.date.today().isoformat()
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.date().isoformat()
    except Exception:
        return datetime.date.today().isoformat()


def parse_reed_date(date_str: str) -> str:
    """Reed returns dates as dd/mm/yyyy. Convert to ISO yyyy-mm-dd. Falls
    back to today on anything unparseable so a bad value never crashes the
    run or trips prune_old's ISO parse."""
    if not date_str:
        return datetime.date.today().isoformat()
    s = str(date_str).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            continue
    return datetime.date.today().isoformat()


# ---------------------------------------------------------------------------
# Jobs.ac.uk - HTML scrape of /search/{slug} (UK) - Phase 5 (RSS replacement)
# ---------------------------------------------------------------------------

def _jobsac_parse_date(text: str) -> str:
    """Jobs.ac.uk cards show 'Date Placed: 15 May' with no year. Assume the
    current year; if that lands in the future (e.g. a December date scraped in
    January), roll back a year. Returns ISO yyyy-mm-dd, today on failure."""
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3,9})", text or "")
    if not m:
        return datetime.date.today().isoformat()
    day = int(m.group(1))
    mon_str = m.group(2)[:3].lower()
    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    mon = months.get(mon_str)
    if not mon:
        return datetime.date.today().isoformat()
    today = datetime.date.today()
    try:
        d = datetime.date(today.year, mon, day)
    except ValueError:
        return today.isoformat()
    if d > today + datetime.timedelta(days=2):  # small skew tolerance
        try:
            d = datetime.date(today.year - 1, mon, day)
        except ValueError:
            pass
    return d.isoformat()


def scrape_jobsac_html() -> list:
    """Scrape jobs.ac.uk via the server-rendered /search/{slug} pages.

    Card structure (verified 17 Jun 2026):
      <a href="/job/{REF}/{title-slug}">Job Title</a>
      <strong>Employer</strong>
      Location: <town>
      Salary: ...
      Date Placed: 15 May
    Each job link matches the path /job/<REF>/. We take the anchor text as the
    title and walk the card's container text for employer / location / date.

    Phase 6 (18 Jun 2026, corrected): result depth. We hit the canonical faceted
    URL `/search/?academicDisciplineFacet[0]={slug}&pageSize=JOBSAC_PAGE_SIZE&
    startIndex=1&sortOrder=1&activeFacet=academicDisciplineFacet` so one request
    per slug returns up to JOBSAC_PAGE_SIZE newest cards instead of the alias's
    default 25. (The earlier `?page=N` attempt was a no-op: jobs.ac.uk ignores
    that param.) seen_refs dedupes a job that appears under multiple slugs."""
    jobs = []
    seen_refs = set()
    for slug in JOBSAC_HTML_SLUGS:
        url = (
            "https://www.jobs.ac.uk/search/"
            f"?academicDisciplineFacet%5B0%5D={urllib.parse.quote(slug)}"
            "&activeFacet=academicDisciplineFacet"
            "&sortOrder=1"  # 1 = Date Placed, newest first
            f"&pageSize={JOBSAC_PAGE_SIZE}"
            "&startIndex=1"
        )
        print(f"  Jobs.ac.uk HTML: {slug} (pageSize={JOBSAC_PAGE_SIZE})")
        r = get(url, timeout=25)
        if not r:
            continue
        added_this_slug = 0
        try:
            soup = BeautifulSoup(r.text, "html.parser")
            anchors = soup.find_all("a", href=re.compile(r"^/job/[A-Za-z0-9]+/"))
            for a in anchors:
                try:
                    title = clean(a.get_text())
                    if not title or len(title) < 4:
                        continue
                    href_path = a.get("href", "")
                    ref_match = re.match(r"^/job/([A-Za-z0-9]+)/", href_path)
                    if not ref_match:
                        continue
                    ref = ref_match.group(1)
                    if ref in seen_refs:
                        continue  # same job listed under multiple slugs
                    seen_refs.add(ref)
                    added_this_slug += 1
                    href = clean_url("https://www.jobs.ac.uk" + href_path)
                    # Find this job's OWN card: climb to the highest ancestor
                    # that still contains exactly one /job/ link. Going further
                    # would swallow sibling cards and make every job inherit the
                    # first card's employer/location/date.
                    container = a
                    while container.parent is not None:
                        parent = container.parent
                        job_links = parent.find_all(
                            "a", href=re.compile(r"^/job/[A-Za-z0-9]+/")
                        )
                        if len(job_links) > 1:
                            break  # parent merges multiple cards; stop here
                        container = parent
                    card_text = container.get_text("\n", strip=True)
                    org = ""
                    loc = ""
                    # Employer extraction - the card markup varies (some cards
                    # have the employer as bold text, some link it, some put a
                    # department line first), so try several strategies in order
                    # of reliability.
                    # (1) Employer-search link: cards with a logo link to
                    #     /search/employer/{slug}; its text/title is the employer.
                    emp_link = container.find(
                        "a", href=re.compile(r"/search/employer/")
                    )
                    if emp_link:
                        org = clean(emp_link.get("title", "") or emp_link.get_text())
                    # (2) First <strong>/<b> that isn't a field label.
                    if not org:
                        for tag in container.find_all(["strong", "b", "h2", "h3"]):
                            cand = clean(tag.get_text())
                            low = cand.lower()
                            if (cand and len(cand) > 2
                                    and not low.startswith((
                                        "salary", "date", "placed", "location",
                                        "closes", "hours", "contract", "job ref"))
                                    and cand != title):
                                org = cand
                                break
                    # (3) Fall back to the text line directly after the title and
                    #     before the first "Location:"/"Salary:" label.
                    if not org:
                        lines = [ln.strip() for ln in card_text.splitlines() if ln.strip()]
                        for i, ln in enumerate(lines):
                            if ln == title and i + 1 < len(lines):
                                nxt = lines[i + 1]
                                if not re.match(r"(?i)(location|salary|date|placed|closes|hours|contract)\s*:", nxt):
                                    org = clean(nxt)
                                break
                    # Strip a trailing " - Department" so the org is just the employer.
                    if org and " - " in org:
                        org = org.split(" - ")[0].strip()
                    loc_m = re.search(r"Location:\s*\n?\s*(.+)", card_text)
                    if loc_m:
                        loc = clean(loc_m.group(1).splitlines()[0])
                    date_m = re.search(r"Date Placed:\s*\n?\s*(.+)", card_text)
                    date_str = _jobsac_parse_date(date_m.group(1) if date_m else "")
                    close_m = re.search(r"Closes\s+(.+)", card_text)
                    closing = clean(close_m.group(1).splitlines()[0]) if close_m else ""
                    jobs.append({
                        "id": make_id(href, title),
                        "title": title,
                        "organisation": org,
                        "location": loc or "UK",
                        "country": "UK",
                        "source": "Jobs.ac.uk",
                        "url": href,
                        "date_posted": date_str,
                        "closing_date": closing,
                        "type": "",
                        "description": "",
                    })
                except Exception as e:
                    print(f"    card parse error: {e}")
            print(f"    {slug}: +{added_this_slug} new (running total {len(jobs)})")
        except Exception as e:
            print(f"    feed parse error ({slug}): {e}")
        time.sleep(1)
    return jobs


# ---------------------------------------------------------------------------
# Jobs.ac.uk - Official RSS feeds (UK)
# ---------------------------------------------------------------------------

def scrape_jobsac_rss() -> list:
    jobs = []
    for feed_url, source in JOBSAC_RSS_FEEDS:
        print(f"  Jobs.ac.uk RSS: {feed_url.split('/')[-3]}")
        r = get(feed_url)
        if not r:
            continue
        try:
            soup = BeautifulSoup(r.text, "xml")
            for item in soup.find_all("item")[:50]:
                try:
                    title = clean(item.find("title").get_text()) if item.find("title") else ""
                    if not title:
                        continue
                    link = item.find("link")
                    # RSS 2.0 carries the URL as <link> text; the old next_sibling
                    # fallback only fired when <link> had no text, yielding an
                    # adjacent node clean_url rejects anyway (audit P5).
                    href = clean_url(link.get_text().strip() if link else "")
                    desc_el = item.find("description")
                    desc = BeautifulSoup(desc_el.get_text(), "html.parser").get_text() if desc_el else ""
                    org = ""
                    org_match = re.search(r"(?:Employer|Institution|Organisation):\s*(.+?)(?:\n|$)", desc, re.I)
                    if org_match:
                        org = clean(org_match.group(1))
                    loc = ""
                    loc_match = re.search(r"(?:Location|Place):\s*(.+?)(?:\n|$)", desc, re.I)
                    if loc_match:
                        loc = clean(loc_match.group(1))
                    closing = ""
                    close_match = re.search(r"(?:Closing date|Closes):\s*(.+?)(?:\n|$)", desc, re.I)
                    if close_match:
                        closing = clean(close_match.group(1))
                    pub_date = item.find("pubDate")
                    date_str = parse_rss_date(pub_date.get_text() if pub_date else "")
                    jobs.append({
                        "id": make_id(href, title),
                        "title": title,
                        "organisation": org,
                        "location": loc,
                        "country": "UK",
                        "source": source,
                        "url": href,
                        "date_posted": date_str,
                        "closing_date": closing,
                        "type": "",
                        "description": clean(desc),
                    })
                except Exception as e:
                    print(f"    item parse error: {e}")
        except Exception as e:
            print(f"    feed parse error: {e}")
        time.sleep(1)
    return jobs


# ---------------------------------------------------------------------------
# Canada - RSS feeds (THEunijobs, HigherEdJobs)
# ---------------------------------------------------------------------------

def scrape_canada_rss() -> list:
    jobs = []
    for feed_url, source in CANADA_RSS_FEEDS:
        print(f"  Canada RSS ({source}): {feed_url[:60]}...")
        r = get(feed_url)
        if not r:
            continue
        try:
            soup = BeautifulSoup(r.text, "xml")
            for item in soup.find_all("item")[:50]:
                try:
                    title = clean(item.find("title").get_text()) if item.find("title") else ""
                    if not title:
                        continue
                    link = item.find("link")
                    # RSS 2.0 carries the URL as <link> text; the old next_sibling
                    # fallback only fired when <link> had no text, yielding an
                    # adjacent node clean_url rejects anyway (audit P5).
                    href = clean_url(link.get_text().strip() if link else "")
                    desc_el = item.find("description")
                    desc = BeautifulSoup(desc_el.get_text(), "html.parser").get_text() if desc_el else ""
                    org = ""
                    org_match = re.search(
                        r"(?:Employer|Institution|Organisation|University|College):\s*(.+?)(?:\n|$)",
                        desc, re.I
                    )
                    if org_match:
                        org = clean(org_match.group(1))
                    pub_date = item.find("pubDate")
                    date_str = parse_rss_date(pub_date.get_text() if pub_date else "")
                    jobs.append({
                        "id": make_id(href, title),
                        "title": title,
                        "organisation": org,
                        "location": "Canada",
                        "country": "Canada",
                        "source": source,
                        "url": href,
                        "date_posted": date_str,
                        "closing_date": "",
                        "type": "",
                        "description": clean(desc),
                    })
                except Exception as e:
                    print(f"    item parse error: {e}")
        except Exception as e:
            print(f"    feed parse error ({source}): {e}")
        time.sleep(1)
    return jobs


# ---------------------------------------------------------------------------
# University Affairs - HTML scrape (Canada) - FIXED in Phase 2
# ---------------------------------------------------------------------------

def scrape_university_affairs() -> list:
    """DISABLED (8 Jul 2026). University Affairs now serves its ENTIRE job
    search behind Cloudflare Turnstile - an interactive bot challenge. A
    network-trace of /search-jobs/ confirmed the search submits as a POST to
    the page itself and the results come back inside that Turnstile-gated
    response; there is no separate clean JSON/HTML list endpoint. A headless
    requests call from CI cannot solve Turnstile, which is exactly why every
    run logged 401/403 ("Cloudflare again"). This is deliberate anti-bot
    architecture, not a markup problem, so the scraper cannot be made to work.

    UA remains the best Canadian academic board for a HUMAN - a browser passes
    the challenge fine - so use it via its own email Job Alert instead of
    scraping. Canadian academic coverage on the board is now carried by
    AcademicWork.ca (CAUT, clean HTML, added same day), Adzuna CA and
    HigherEdJobs. This stub is retained (returns []) so main() stays stable and
    the git history documents why UA was dropped; delete it once settled."""
    return []


# ---------------------------------------------------------------------------
# AcademicWork.ca - HTML scrape (Canada, CAUT) - added 8 Jul 2026
# ---------------------------------------------------------------------------
# Replacement for the Turnstile-walled University Affairs scraper. AcademicWork
# is CAUT's (Canadian Association of University Teachers) academic job board and
# the second-largest Canadian academic source after UA. Unlike UA it is fully
# server-rendered plain HTML with no bot challenge and working ?page=N
# pagination, so it scrapes cleanly.
#
# Listing structure (verified 8 Jul 2026), one block per job on the index:
#   <h2><a href="/jobs/{slug}">Job Title</a></h2>
#   <h3><a href="/institution/{slug}">Employer</a></h3>
#   Posted: <strong>Month DD, YYYY</strong>
#   <short description paragraph>
# The job detail page (/jobs/{slug}) carries the full description text (used for
# categorisation) and the employer as an <h3>. Location is in the body prose
# (province varies), so we default country to Canada and leave location coarse.

ACADEMICWORK_BASE = "https://www.academicwork.ca"
ACADEMICWORK_MAX_PAGES = 5  # 10 jobs/page; 5 pages = 50 newest, well inside the
                            # 20-day window (site currently lists ~126 total)


def _academicwork_parse_date(text: str) -> str:
    """AcademicWork shows 'Posted: July 08, 2026' (or 'Jul 8, 2026'). Parse to
    ISO yyyy-mm-dd; fall back to today on anything unparseable so prune_old's
    ISO parse never chokes."""
    s = (text or "").strip()
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            continue
    return datetime.date.today().isoformat()


def scrape_academicwork() -> list:
    """Scrape AcademicWork.ca (CAUT) index pages. One request per page up to
    ACADEMICWORK_MAX_PAGES; stops early on an empty page. Each job's own detail
    page is fetched once to pull the full description for categorisation."""
    jobs = []
    seen_urls = set()
    for page in range(1, ACADEMICWORK_MAX_PAGES + 1):
        url = ACADEMICWORK_BASE if page == 1 else f"{ACADEMICWORK_BASE}/?page={page}"
        print(f"  AcademicWork.ca: page {page}")
        r = get(url, timeout=25)
        if not r:
            break
        added_this_page = 0
        try:
            soup = BeautifulSoup(r.text, "html.parser")
            # Each job title is an <h2> wrapping an <a href="/jobs/{slug}">.
            for h2 in soup.find_all("h2"):
                try:
                    a = h2.find("a", href=re.compile(r"/jobs/"))
                    if not a or "/jobs/create" in a.get("href", ""):
                        continue
                    href_raw = a.get("href", "")
                    if href_raw.startswith("/"):
                        href = ACADEMICWORK_BASE + href_raw
                    elif href_raw.startswith("http"):
                        href = href_raw
                    else:
                        href = ACADEMICWORK_BASE + "/" + href_raw
                    href = clean_url(href)
                    if not href or href in seen_urls:
                        continue
                    seen_urls.add(href)
                    title = clean(a.get_text())
                    if not title or len(title) < 5:
                        continue
                    # Employer: the <h3> immediately following this <h2>.
                    org = ""
                    h3 = h2.find_next("h3")
                    if h3:
                        org = clean(h3.get_text())
                    # Posted date: scan the parent block text for "Posted: <date>".
                    date_str = datetime.date.today().isoformat()
                    block = h2.parent.get_text(" ", strip=True) if h2.parent else ""
                    dm = re.search(r"Posted:\s*([A-Za-z]+\.?\s+\d{1,2},\s*\d{4})", block)
                    if dm:
                        date_str = _academicwork_parse_date(dm.group(1))
                    # Fetch the detail page for the full description (better
                    # categorisation). Best-effort; skip on failure.
                    description = ""
                    dr = get(href, timeout=20)
                    if dr:
                        try:
                            dsoup = BeautifulSoup(dr.text, "html.parser")
                            main = dsoup.find("main") or dsoup
                            description = clean(main.get_text(" ", strip=True))
                        except Exception:
                            description = ""
                        time.sleep(0.5)
                    jobs.append({
                        "id": make_id(href, title),
                        "title": title,
                        "organisation": org,
                        "location": "Canada",
                        "country": "Canada",
                        "source": "AcademicWork",
                        "url": href,
                        "date_posted": date_str,
                        "closing_date": "",
                        "type": "",
                        "description": description,
                    })
                    added_this_page += 1
                except Exception as e:
                    print(f"    item parse error: {e}")
            print(f"    page {page}: +{added_this_page} (running total {len(jobs)})")
            if added_this_page == 0:
                break  # no jobs on this page -> past the last page
        except Exception as e:
            print(f"    page parse error ({page}): {e}")
            break
        time.sleep(1)
    return jobs


# ---------------------------------------------------------------------------
# Adzuna API (UK + Canada) - Phase 2 addition
# ---------------------------------------------------------------------------

def scrape_adzuna(country_code: str, country_label: str) -> list:
    """Adzuna REST API. Requires ADZUNA_APP_ID and ADZUNA_APP_KEY env vars.
    Silently returns [] if absent so deploy still works without them."""
    app_id = os.environ.get("ADZUNA_APP_ID", "").strip()
    app_key = os.environ.get("ADZUNA_APP_KEY", "").strip()
    if not app_id or not app_key:
        print(f"  Adzuna {country_label}: ADZUNA_APP_ID/KEY not set, skipping")
        return []
    # Phase 7 (18 Aug 2026): Canada gets its own query list. The UK set is
    # tuned to UK job-title conventions ("lecturer", "head of college") which
    # barely exist in Canadian postings, where the equivalents are "assistant
    # professor", "kinesiology" and "human kinetics", so the CA run was
    # effectively searching for the wrong words.
    queries = ADZUNA_CA_QUERIES if country_code == "ca" else ADZUNA_QUERIES
    jobs = []
    print(f"  Adzuna {country_label} ({country_code}): {len(queries)} queries")
    for query in queries:
        url = (
            f"https://api.adzuna.com/v1/api/jobs/{country_code}/search/1"
            f"?app_id={urllib.parse.quote(app_id)}"
            f"&app_key={urllib.parse.quote(app_key)}"
            f"&results_per_page=20"
            f"&what={urllib.parse.quote(query)}"
            f"&sort_by=date"
            f"&content-type=application/json"
        )
        try:
            r = requests.get(url, timeout=15, headers={"Accept": "application/json"})
            if r.status_code == 401:
                # Show first 200 chars of body to surface the actual auth
                # error - bad keys vs whitespace vs swapped id/key etc.
                body_preview = r.text[:200].replace("\n", " ")
                print(f"  Adzuna {country_label} 401: {body_preview}")
                return jobs  # no point hammering with bad creds
            r.raise_for_status()
            data = r.json()
            for item in data.get("results", []):
                try:
                    href = clean_url(item.get("redirect_url", ""))
                    title = clean(item.get("title", ""))
                    if not title or not href:
                        continue
                    company = item.get("company", {})
                    org = clean(company.get("display_name", "")) if isinstance(company, dict) else ""
                    location_obj = item.get("location", {})
                    loc = ""
                    if isinstance(location_obj, dict):
                        loc = clean(location_obj.get("display_name", ""))
                    created = item.get("created", "")
                    date_str = created[:10] if created else datetime.date.today().isoformat()
                    jobs.append({
                        "id": make_id(href, title),
                        "title": title,
                        "organisation": org,
                        "location": loc,
                        "country": country_label,
                        "source": "Adzuna",
                        "url": href,
                        "date_posted": date_str,
                        "closing_date": "",
                        "type": clean(item.get("contract_time", "") or item.get("contract_type", "")),
                        "description": clean(item.get("description", "")),
                    })
                except Exception as e:
                    print(f"    item parse error: {e}")
        except Exception as e:
            print(f"  GET failed Adzuna {country_label} q={query[:30]}: {e}")
        time.sleep(1)  # polite rate-limit
    return jobs


# ---------------------------------------------------------------------------
# Reed.co.uk Jobseeker API (UK) - Phase 3.2 addition
# ---------------------------------------------------------------------------

def scrape_reed() -> list:
    """Reed.co.uk Jobseeker API (UK). Requires REED_API_KEY env var.
    Auth is HTTP Basic with the key as username and an empty password.
    Silently returns [] if the key is absent so deploy still works without
    it (same pattern as Adzuna). UK-only coverage; country hard-set to UK.

    Added to close the FE/college-sector gap: the role that motivated this
    source (Head of Youth College) was live on Reed but never surfaced via
    the other sources, and Adzuna's claimed Reed aggregation did not cover
    it in practice."""
    api_key = os.environ.get("REED_API_KEY", "").strip()
    if not api_key:
        print("  Reed: REED_API_KEY not set, skipping")
        return []
    jobs = []
    print(f"  Reed ({len(REED_QUERIES)} queries)")
    seen_ids_local = set()
    for query in REED_QUERIES:
        url = (
            "https://www.reed.co.uk/api/1.0/search"
            f"?keywords={urllib.parse.quote(query)}"
            "&resultsToTake=100"
        )
        try:
            # Basic auth: key as username, blank password. requests builds
            # the header itself from the tuple, so the key is never placed
            # into the URL or any logged string.
            r = requests.get(
                url,
                timeout=15,
                headers={"Accept": "application/json"},
                auth=(api_key, ""),
            )
            if r.status_code == 401:
                print("  Reed 401: check REED_API_KEY value")
                return jobs  # bad creds, no point continuing
            r.raise_for_status()
            data = r.json()
            for item in data.get("results", []):
                try:
                    job_id = item.get("jobId")
                    if job_id is None or job_id in seen_ids_local:
                        continue
                    seen_ids_local.add(job_id)
                    title = clean(item.get("jobTitle", ""))
                    href = clean_url(item.get("jobUrl", "")
                                     or f"https://www.reed.co.uk/jobs/{job_id}")
                    if not title or not href:
                        continue
                    org = clean(item.get("employerName", ""))
                    loc = clean(item.get("locationName", ""))
                    date_raw = item.get("date", "") or item.get("datePosted", "")
                    date_str = parse_reed_date(date_raw)
                    closing = item.get("expirationDate", "") or ""
                    jobs.append({
                        "id": make_id(href, title),
                        "title": title,
                        "organisation": org,
                        "location": loc,
                        "country": "UK",
                        "source": "Reed",
                        "url": href,
                        "date_posted": date_str,
                        "closing_date": clean(closing),
                        "type": "",
                        "description": clean(item.get("jobDescription", "")),
                    })
                except Exception as e:
                    print(f"    item parse error: {e}")
        except Exception as e:
            print(f"  GET failed Reed q={query[:30]}: {e}")
        time.sleep(1)  # polite rate-limit
    return jobs


# ---------------------------------------------------------------------------
# Country inference (shared by Greenhouse + Lever)
# ---------------------------------------------------------------------------

_UK_CITY_TERMS = (
    "united kingdom", "london", "manchester", "edinburgh",
    "britain", "england", "scotland", "wales",
)
_CA_CITY_TERMS = (
    "canada", "toronto", "vancouver", "montreal", "ottawa", "calgary",
)
# Match the bare token "uk" only on word boundaries. The old `"uk" in loc_lower`
# test matched any location merely containing those two letters - e.g.
# "Tukwila, WA" (US) was tagged UK (audit P4, same class as news scraper H11).
_UK_WORD_RE = re.compile(r"\buk\b")


def infer_country(loc: str) -> str:
    """Infer 'UK' / 'Canada' / '' from a free-text location. Remote and
    unknown both return '' (the front end surfaces those in the All view)."""
    t = (loc or "").lower()
    if _UK_WORD_RE.search(t) or any(c in t for c in _UK_CITY_TERMS):
        return "UK"
    if any(c in t for c in _CA_CITY_TERMS):
        return "Canada"
    return ""


# ---------------------------------------------------------------------------
# Greenhouse Job Board API (industry health-tech / sport-tech)
# ---------------------------------------------------------------------------

def scrape_greenhouse() -> list:
    """Public job board API. No auth, no rate limit. Each company's token
    is the slug in their boards.greenhouse.io URL."""
    jobs = []
    print(f"  Greenhouse: {len(GREENHOUSE_COMPANIES)} companies")
    for token, label in GREENHOUSE_COMPANIES:
        if not token:
            continue
        url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
        try:
            r = requests.get(url, timeout=15, headers={"Accept": "application/json"})
            if r.status_code != 200:
                print(f"    {token}: HTTP {r.status_code}, skipping")
                continue
            data = r.json()
            for item in data.get("jobs", []):
                try:
                    title = clean(item.get("title", ""))
                    href = clean_url(item.get("absolute_url", ""))
                    if not title or not href:
                        continue
                    location_obj = item.get("location", {})
                    loc = ""
                    if isinstance(location_obj, dict):
                        loc = clean(location_obj.get("name", ""))
                    # Infer country from location text (audit P4: word-boundary
                    # "uk" so "Tukwila, WA" no longer mis-tags as UK; remote and
                    # unknown both fall through to "" = shown in the All view).
                    country = infer_country(loc)
                    updated = item.get("updated_at", "")
                    date_str = updated[:10] if updated else datetime.date.today().isoformat()
                    description = clean(item.get("content", ""))
                    jobs.append({
                        "id": make_id(href, title),
                        "title": title,
                        "organisation": label or token,
                        "location": loc,
                        "country": country,
                        "source": "Greenhouse",
                        "url": href,
                        "date_posted": date_str,
                        "closing_date": "",
                        "type": "",
                        "description": description,
                    })
                except Exception as e:
                    print(f"    {token} item parse error: {e}")
        except Exception as e:
            print(f"  GET failed Greenhouse {token}: {e}")
        time.sleep(0.5)
    return jobs


# ---------------------------------------------------------------------------
# Lever Postings API (industry sport-tech / wearables)
# ---------------------------------------------------------------------------

def scrape_lever() -> list:
    """Public postings API. No auth. Each company's client name is the slug
    in jobs.lever.co URLs."""
    jobs = []
    print(f"  Lever: {len(LEVER_COMPANIES)} companies")
    for client, label in LEVER_COMPANIES:
        url = f"https://api.lever.co/v0/postings/{client}?mode=json"
        try:
            r = requests.get(url, timeout=15, headers={"Accept": "application/json"})
            if r.status_code != 200:
                print(f"    {client}: HTTP {r.status_code}, skipping")
                continue
            data = r.json()
            for item in data:
                try:
                    title = clean(item.get("text", ""))
                    href = clean_url(item.get("hostedUrl", ""))
                    if not title or not href:
                        continue
                    categories = item.get("categories", {}) or {}
                    loc = clean(categories.get("location", ""))
                    country = infer_country(loc)  # audit P4: word-boundary "uk"
                    created = item.get("createdAt")
                    if created:
                        try:
                            date_str = datetime.datetime.utcfromtimestamp(created / 1000).date().isoformat()
                        except Exception:
                            date_str = datetime.date.today().isoformat()
                    else:
                        date_str = datetime.date.today().isoformat()
                    description = clean(item.get("descriptionPlain", "") or item.get("description", ""))
                    commitment = clean(categories.get("commitment", ""))
                    jobs.append({
                        "id": make_id(href, title),
                        "title": title,
                        "organisation": label or client,
                        "location": loc,
                        "country": country,
                        "source": "Lever",
                        "url": href,
                        "date_posted": date_str,
                        "closing_date": "",
                        "type": commitment,
                        "description": description,
                    })
                except Exception as e:
                    print(f"    {client} item parse error: {e}")
        except Exception as e:
            print(f"  GET failed Lever {client}: {e}")
        time.sleep(0.5)
    return jobs


# ---------------------------------------------------------------------------
# Ashby posting API (Phase 7) - elite performance / wearables
# ---------------------------------------------------------------------------

def scrape_ashby() -> list:
    """Public posting API, no auth. The board name is the slug in
    jobs.ashbyhq.com/{board}. Ashby returns ISO timestamps in publishedAt."""
    jobs = []
    print(f"  Ashby: {len(ASHBY_COMPANIES)} companies")
    for board, label in ASHBY_COMPANIES:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{board}"
        try:
            r = requests.get(url, timeout=15, headers={"Accept": "application/json"})
            if r.status_code != 200:
                print(f"    {board}: HTTP {r.status_code}, skipping")
                continue
            for item in (r.json() or {}).get("jobs", []):
                try:
                    title = clean(item.get("title", ""))
                    href = clean_url(item.get("jobUrl", "") or item.get("applyUrl", ""))
                    if not title or not href:
                        continue
                    loc = clean(item.get("location", ""))
                    published = item.get("publishedAt", "") or ""
                    date_str = published[:10] if len(published) >= 10 else datetime.date.today().isoformat()
                    jobs.append({
                        "id": make_id(href, title),
                        "title": title,
                        "organisation": label or board,
                        "location": loc,
                        "country": infer_country(loc),
                        "source": "Ashby",
                        "url": href,
                        "date_posted": date_str,
                        "closing_date": "",
                        "type": clean(item.get("employmentType", "")),
                        "description": clean(item.get("descriptionPlain", "")),
                    })
                except Exception as e:
                    print(f"    {board} item parse error: {e}")
        except Exception as e:
            print(f"  GET failed Ashby {board}: {e}")
        time.sleep(0.5)
    return jobs


# ---------------------------------------------------------------------------
# Oracle Recruiting Cloud (Phase 8, 19 Aug 2026) - UK universities
#
# The Russell Group audit found that UK HEIs are not each running a bespoke
# system; they cluster onto about a dozen applicant-tracking platforms. Oracle
# Recruiting Cloud is the cleanest of them: it exposes a completely
# unauthenticated JSON API on every tenant, in the same spirit as Greenhouse
# and Ashby, so a university is a CONFIG LINE rather than a new scraper.
#
# Endpoint shape (verified live 19 Aug 2026 against Edinburgh and Birmingham):
#   https://{pod}/hcmRestApi/resources/latest/recruitingCEJobRequisitions
#     ?onlyData=true&expand=requisitionList
#     &finder=findReqs;siteNumber={site},limit={n},offset={m}
#
# TWO GOTCHAS, both cost time to find:
#   1. `expand=requisitionList` is REQUIRED. Without it the response still
#      returns HTTP 200 with the facets and a TotalJobsCount, but the actual
#      postings are absent and the parse silently yields nothing.
#   2. `limit` and `offset` must go INSIDE the finder string, after the
#      semicolon, not as ordinary query parameters. A top-level &limit= is
#      accepted and ignored.
#
# The pod and site number are both visible in the careers-site URL the
# university links to, e.g. Edinburgh's
# elxw.fa.em3.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001
# gives pod `elxw.fa.em3.oraclecloud.com` and site `CX_1001`.
# ---------------------------------------------------------------------------

ORACLE_ORC_MAX_PAGES = 4
ORACLE_ORC_PAGE_SIZE = 100

# (pod, siteNumber, display name)
ORACLE_ORC_TENANTS = [
    ("elxw.fa.em3.oraclecloud.com", "CX_1001", "University of Edinburgh"),
    ("edzz.fa.em3.oraclecloud.com", "CX_6001", "University of Birmingham"),
]


def scrape_oracle_orc() -> list:
    """Public Oracle Recruiting Cloud JSON, no auth, no key. UK universities."""
    jobs = []
    print(f"  Oracle ORC: {len(ORACLE_ORC_TENANTS)} tenants")
    for pod, site, label in ORACLE_ORC_TENANTS:
        seen_ids = set()
        for page in range(ORACLE_ORC_MAX_PAGES):
            offset = page * ORACLE_ORC_PAGE_SIZE
            url = (
                f"https://{pod}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
                f"?onlyData=true&expand=requisitionList"
                f"&finder=findReqs;siteNumber={site},"
                f"limit={ORACLE_ORC_PAGE_SIZE},offset={offset}"
            )
            try:
                r = requests.get(url, timeout=30, headers={"Accept": "application/json"})
                if r.status_code != 200:
                    print(f"    {label}: HTTP {r.status_code}, skipping")
                    break
                items = (r.json() or {}).get("items") or []
                if not items:
                    break
                reqs = items[0].get("requisitionList") or []
                if not reqs:
                    break
                added = 0
                for item in reqs:
                    try:
                        req_id = str(item.get("Id", "") or "")
                        title = clean(item.get("Title", ""))
                        if not title or req_id in seen_ids:
                            continue
                        seen_ids.add(req_id)
                        href = clean_url(
                            f"https://{pod}/hcmUI/CandidateExperience/en/sites/"
                            f"{site}/job/{req_id}"
                        )
                        if not href:
                            continue
                        loc = clean(item.get("PrimaryLocation", ""))
                        posted = item.get("PostedDate", "") or ""
                        date_str = (
                            posted[:10] if len(posted) >= 10
                            else datetime.date.today().isoformat()
                        )
                        closing = item.get("PostingEndDate", "") or ""
                        # ShortDescriptionStr is usually empty on the list
                        # endpoint; the qualifications and responsibilities
                        # fields carry the real text and are what categorise()
                        # needs, so concatenate whatever is present rather than
                        # fetching each job detail page (which would be one
                        # request per posting).
                        desc = " ".join(
                            clean(item.get(k, "") or "")
                            for k in (
                                "ShortDescriptionStr",
                                "ExternalQualificationsStr",
                                "ExternalResponsibilitiesStr",
                                "JobFamily",
                                "JobFunction",
                                "Department",
                            )
                        ).strip()
                        jobs.append({
                            "id": make_id(href, title),
                            "title": title,
                            "organisation": label,
                            "location": loc,
                            "country": infer_country(loc) or "UK",
                            "source": "Oracle ORC",
                            "url": href,
                            "date_posted": date_str,
                            "closing_date": closing[:10] if len(closing) >= 10 else "",
                            "type": clean(item.get("JobType", "") or item.get("WorkerType", "")),
                            "description": desc,
                        })
                        added += 1
                    except Exception as e:
                        print(f"    {label} item parse error: {e}")
                print(f"    {label} p{page + 1}: +{added}")
                if added == 0 or len(reqs) < ORACLE_ORC_PAGE_SIZE:
                    break
            except Exception as e:
                print(f"  GET failed Oracle ORC {label}: {e}")
                break
            time.sleep(0.5)
    return jobs


# ---------------------------------------------------------------------------
# University of Cambridge RSS (Phase 8, 19 Aug 2026)
#
# Cambridge runs a bespoke in-house system rather than a commercial ATS, but
# unlike the other bespoke systems in the audit (Glasgow, QMUL) it publishes a
# working RSS feed. Cheap to poll and stable, so it is worth its own tiny
# adapter rather than relying on jobs.ac.uk syndication.
#
# CAUTION recorded for the next audit: the platform-detection sweep initially
# reported Cambridge, Bristol and Warwick as Eploy tenants. They are not. The
# regex `eploy` was matching inside the words "employ" and "employer" in the
# page body. This is EXACTLY the Phase 4 `rse`-inside-"course" bug in a new
# place. Bristol is in fact Lumesse/TalentLink and Warwick is tal.net. Any
# future platform sweep must use word-boundary matching, and a platform should
# be confirmed by a real host name in a link (e.g. cardiffuniweb.eploy.net) and
# never by a bare substring in body text.
# ---------------------------------------------------------------------------

CAMBRIDGE_RSS = "https://www.jobs.cam.ac.uk/job/?format=rss"


def scrape_cambridge() -> list:
    """University of Cambridge bespoke jobs system, RSS 2.0."""
    jobs = []
    print("  Cambridge RSS")
    r = get(CAMBRIDGE_RSS)
    if not r:
        return jobs
    try:
        soup = BeautifulSoup(r.text, "xml")
        for item in soup.find_all("item"):
            try:
                title_el = item.find("title")
                title = clean(title_el.get_text()) if title_el else ""
                link_el = item.find("link")
                href = clean_url(link_el.get_text().strip() if link_el else "")
                if not title or not href:
                    continue
                desc_el = item.find("description")
                desc = (
                    BeautifulSoup(desc_el.get_text(), "html.parser").get_text()
                    if desc_el else ""
                )
                pub = item.find("pubDate")
                date_str = parse_rss_date(pub.get_text() if pub else "")
                closing = ""
                cm = re.search(r"(?:Closing date|Closes):\s*(.+?)(?:\n|$)", desc, re.I)
                if cm:
                    closing = clean(cm.group(1))
                jobs.append({
                    "id": make_id(href, title),
                    "title": title,
                    "organisation": "University of Cambridge",
                    "location": "Cambridge, UK",
                    "country": "UK",
                    "source": "Cambridge",
                    "url": href,
                    "date_posted": date_str or datetime.date.today().isoformat(),
                    "closing_date": closing,
                    "type": "",
                    "description": clean(desc),
                })
            except Exception as e:
                print(f"    Cambridge item parse error: {e}")
    except Exception as e:
        print(f"  Cambridge parse failed: {e}")
    return jobs


# ---------------------------------------------------------------------------
# SmartRecruiters postings API (Phase 7) - Williams Racing, Red Bull, Sportradar
# ---------------------------------------------------------------------------

def scrape_smartrecruiters() -> list:
    """Public postings API, no auth. The company id is the slug in
    careers.smartrecruiters.com/{id}. Paginated by offset; capped at
    SMARTRECRUITERS_MAX_PAGES because Red Bull alone lists over a thousand
    postings and only a handful are ever relevant."""
    jobs = []
    print(f"  SmartRecruiters: {len(SMARTRECRUITERS_COMPANIES)} companies")
    for company, label in SMARTRECRUITERS_COMPANIES:
        for page in range(SMARTRECRUITERS_MAX_PAGES):
            offset = page * SMARTRECRUITERS_PAGE_SIZE
            url = (
                f"https://api.smartrecruiters.com/v1/companies/{company}/postings"
                f"?limit={SMARTRECRUITERS_PAGE_SIZE}&offset={offset}"
            )
            try:
                r = requests.get(url, timeout=20, headers={"Accept": "application/json"})
                if r.status_code != 200:
                    print(f"    {company}: HTTP {r.status_code}, skipping")
                    break
                content = (r.json() or {}).get("content", [])
                if not content:
                    break
                for item in content:
                    try:
                        title = clean(item.get("name", ""))
                        posting_id = clean(item.get("id", ""))
                        if not title or not posting_id:
                            continue
                        href = clean_url(
                            f"https://jobs.smartrecruiters.com/{company}/{posting_id}"
                        )
                        loc_obj = item.get("location", {}) or {}
                        loc = ", ".join(
                            p for p in (
                                clean(loc_obj.get("city", "")),
                                clean(loc_obj.get("region", "")),
                                clean(loc_obj.get("country", "")).upper(),
                            ) if p
                        )
                        released = item.get("releasedDate", "") or ""
                        date_str = released[:10] if len(released) >= 10 else datetime.date.today().isoformat()
                        dept = (item.get("department", {}) or {}).get("label", "")
                        jobs.append({
                            "id": make_id(href, title),
                            "title": title,
                            "organisation": label or company,
                            "location": loc,
                            "country": infer_country(loc),
                            "source": "SmartRecruiters",
                            "url": href,
                            "date_posted": date_str,
                            "closing_date": "",
                            "type": clean((item.get("typeOfEmployment", {}) or {}).get("label", "")),
                            "description": clean(dept),
                        })
                    except Exception as e:
                        print(f"    {company} item parse error: {e}")
                if len(content) < SMARTRECRUITERS_PAGE_SIZE:
                    break
            except Exception as e:
                print(f"  GET failed SmartRecruiters {company}: {e}")
                break
            time.sleep(0.5)
    return jobs


# ---------------------------------------------------------------------------
# Recruitee offers API (Phase 7) - Movella/Xsens, Alpine, Matrix Fitness
# ---------------------------------------------------------------------------

def scrape_recruitee() -> list:
    """Public offers API, no auth. The account is the subdomain in
    {account}.recruitee.com."""
    jobs = []
    print(f"  Recruitee: {len(RECRUITEE_COMPANIES)} companies")
    for account, label in RECRUITEE_COMPANIES:
        url = f"https://{account}.recruitee.com/api/offers/"
        try:
            r = requests.get(url, timeout=15, headers={"Accept": "application/json"})
            if r.status_code != 200:
                print(f"    {account}: HTTP {r.status_code}, skipping")
                continue
            for item in (r.json() or {}).get("offers", []):
                try:
                    title = clean(item.get("title", ""))
                    href = clean_url(item.get("careers_url", "") or item.get("url", ""))
                    if not title or not href:
                        continue
                    loc = ", ".join(
                        p for p in (
                            clean(item.get("city", "")),
                            clean(item.get("country_code", "")).upper(),
                        ) if p
                    )
                    published = item.get("published_at", "") or item.get("created_at", "") or ""
                    date_str = published[:10] if len(published) >= 10 else datetime.date.today().isoformat()
                    jobs.append({
                        "id": make_id(href, title),
                        "title": title,
                        "organisation": label or account,
                        "location": loc,
                        "country": infer_country(loc),
                        "source": "Recruitee",
                        "url": href,
                        "date_posted": date_str,
                        "closing_date": "",
                        "type": clean(item.get("employment_type_code", "")),
                        "description": clean(item.get("description", "")),
                    })
                except Exception as e:
                    print(f"    {account} item parse error: {e}")
        except Exception as e:
            print(f"  GET failed Recruitee {account}: {e}")
        time.sleep(0.5)
    return jobs


# ---------------------------------------------------------------------------
# Workable widget API (Phase 7) - OptiTrack, Withings
# ---------------------------------------------------------------------------

def scrape_workable() -> list:
    """Public widget endpoint, no auth. The account is the slug in
    apply.workable.com/{account}. Dates come back as 'YYYY-MM-DD' already."""
    jobs = []
    print(f"  Workable: {len(WORKABLE_COMPANIES)} companies")
    for account, label in WORKABLE_COMPANIES:
        url = f"https://apply.workable.com/api/v1/widget/accounts/{account}?details=true"
        try:
            r = requests.get(url, timeout=15, headers={"Accept": "application/json"})
            if r.status_code != 200:
                print(f"    {account}: HTTP {r.status_code}, skipping")
                continue
            for item in (r.json() or {}).get("jobs", []):
                try:
                    title = clean(item.get("title", ""))
                    href = clean_url(item.get("url", "") or item.get("application_url", ""))
                    if not title or not href:
                        continue
                    loc = ", ".join(
                        p for p in (
                            clean(item.get("city", "")),
                            clean(item.get("country", "")),
                        ) if p
                    )
                    date_str = clean(item.get("published_on", "")) or datetime.date.today().isoformat()
                    if len(date_str) > 10:
                        date_str = date_str[:10]
                    jobs.append({
                        "id": make_id(href, title),
                        "title": title,
                        "organisation": label or account,
                        "location": loc,
                        "country": infer_country(loc),
                        "source": "Workable",
                        "url": href,
                        "date_posted": date_str,
                        "closing_date": "",
                        "type": clean(item.get("employment_type", "")),
                        "description": clean(item.get("description", "")),
                    })
                except Exception as e:
                    print(f"    {account} item parse error: {e}")
        except Exception as e:
            print(f"  GET failed Workable {account}: {e}")
        time.sleep(0.5)
    return jobs


# ---------------------------------------------------------------------------
# Indeed (UK) - best-effort first-page scrape (env-gated, OFF by default)
# ---------------------------------------------------------------------------

def _indeed_extract_jobcards(html_text: str) -> list:
    """Indeed embeds first-page results as JSON in a script blob
    (window.mosaic.providerData['mosaic-provider-jobcards']). Pull the
    'results' array out of it. Returns [] on any structural mismatch (the
    markup changes often and Cloudflare may serve an interstitial instead)."""
    # Locate the jobcards provider blob, then balance braces from the first '{'
    # after it to capture the JSON object even though it's embedded in JS.
    idx = html_text.find("mosaic-provider-jobcards")
    if idx == -1:
        return []
    start = html_text.find("{", idx)
    if start == -1:
        return []
    depth = 0
    end = -1
    for i in range(start, min(len(html_text), start + 2_000_000)):
        c = html_text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end == -1:
        return []
    blob = html_text[start:end]
    try:
        data = json.loads(blob)
    except Exception:
        return []
    # The results array lives at metaData.mosaicProviderJobCardsModel.results
    # in current markup; fall back to a recursive search for a 'results' list
    # of dicts if the path differs.
    try:
        return (data.get("metaData", {})
                    .get("mosaicProviderJobCardsModel", {})
                    .get("results", [])) or _indeed_find_results(data)
    except Exception:
        return _indeed_find_results(data)


def _indeed_find_results(obj) -> list:
    """Recursively hunt for a 'results' key whose value is a list of job-like
    dicts (have a 'title' or 'displayTitle'). Defensive fallback for markup
    drift."""
    if isinstance(obj, dict):
        r = obj.get("results")
        if isinstance(r, list) and r and isinstance(r[0], dict) and (
            "title" in r[0] or "displayTitle" in r[0]
        ):
            return r
        for v in obj.values():
            found = _indeed_find_results(v)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _indeed_find_results(v)
            if found:
                return found
    return []


def scrape_indeed() -> list:
    """Best-effort first-page Indeed (UK) scrape. OFF unless INDEED_ENABLE is
    set. Reads only page 1 of each query's server-rendered results; never
    paginates (page 2+ is behind a login wall). Frequently returns 0 from
    datacentre IPs due to Cloudflare - that's expected and harmless."""
    if not INDEED_ENABLE:
        print("  Indeed: INDEED_ENABLE not set, skipping (best-effort source, off by default)")
        return []
    jobs = []
    seen_keys = set()
    print(f"  Indeed UK ({len(INDEED_QUERIES)} queries, best-effort first page)")
    ind_headers = dict(HEADERS)
    ind_headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    ind_headers["Referer"] = "https://uk.indeed.com/"
    for query in INDEED_QUERIES:
        url = (
            "https://uk.indeed.com/jobs"
            f"?q={urllib.parse.quote(query)}"
            "&sort=date"
            "&fromage=14"
        )
        try:
            r = requests.get(url, headers=ind_headers, timeout=20)
            if r.status_code != 200:
                print(f"    q={query[:24]}: HTTP {r.status_code} (likely Cloudflare/anti-bot), skipping")
                time.sleep(2)
                continue
            results = _indeed_extract_jobcards(r.text)
            if not results:
                print(f"    q={query[:24]}: 0 cards (blocked or markup drift)")
                time.sleep(2)
                continue
            added = 0
            for item in results:
                try:
                    title = clean(item.get("displayTitle") or item.get("title", ""))
                    jk = item.get("jobkey") or item.get("jobKey") or ""
                    if not title or not jk or jk in seen_keys:
                        continue
                    seen_keys.add(jk)
                    href = clean_url(f"https://uk.indeed.com/viewjob?jk={jk}")
                    if not href:
                        continue
                    org = clean(item.get("company") or item.get("companyName", ""))
                    loc = clean(
                        item.get("formattedLocation")
                        or item.get("jobLocationCity", "")
                    )
                    # Indeed gives an age in ms since epoch (pubDate) on some
                    # cards; fall back to today.
                    pub = item.get("pubDate")
                    if isinstance(pub, (int, float)):
                        try:
                            date_str = datetime.datetime.utcfromtimestamp(
                                pub / 1000
                            ).date().isoformat()
                        except Exception:
                            date_str = datetime.date.today().isoformat()
                    else:
                        date_str = datetime.date.today().isoformat()
                    snippet = item.get("snippet") or item.get("jobDescription", "")
                    jobs.append({
                        "id": make_id(href, title),
                        "title": title,
                        "organisation": org,
                        "location": loc or "UK",
                        "country": "UK",
                        "source": "Indeed",
                        "url": href,
                        "date_posted": date_str,
                        "closing_date": "",
                        "type": "",
                        "description": clean(snippet),
                    })
                    added += 1
                except Exception as e:
                    print(f"    card parse error: {e}")
            print(f"    q={query[:24]}: +{added} (running total {len(jobs)})")
        except Exception as e:
            print(f"  GET failed Indeed q={query[:24]}: {e}")
        time.sleep(2)  # extra-polite: best-effort grey-area source
    return jobs


# ---------------------------------------------------------------------------
# Bluesky - public AT Protocol API
# ---------------------------------------------------------------------------

def scrape_bluesky() -> list:
    jobs = []
    for handle in BLUESKY_ACCOUNTS:
        print(f"  Bluesky: {handle}")
        try:
            resolve_url = f"https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle?handle={handle}"
            r = get(resolve_url)
            if not r:
                continue
            did = r.json().get("did", "")
            if not did:
                continue
            feed_url = (
                f"https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"
                f"?actor={did}&limit=100&filter=posts_no_replies"
            )
            r = get(feed_url)
            if not r:
                continue
            feed = r.json().get("feed", [])
            for item in feed:
                try:
                    post = item.get("post", {})
                    record = post.get("record", {})
                    text = record.get("text", "")
                    if not text:
                        continue
                    created_at = record.get("createdAt", "")
                    date_str = created_at[:10] if created_at else datetime.date.today().isoformat()
                    uri = post.get("uri", "")
                    rkey = uri.split("/")[-1] if uri else ""
                    post_url = f"https://bsky.app/profile/{handle}/post/{rkey}" if rkey else f"https://bsky.app/profile/{handle}"
                    job_url = post_url
                    embed = record.get("embed", {})
                    if embed:
                        external = embed.get("external", {})
                        if external and external.get("uri"):
                            job_url = external["uri"]
                    for facet in record.get("facets", []):
                        for feature in facet.get("features", []):
                            if feature.get("$type") == "app.bsky.richtext.facet#link":
                                uri_val = feature.get("uri", "")
                                if uri_val and not uri_val.startswith("https://bsky.app"):
                                    job_url = uri_val
                                    break
                    job_url = clean_url(job_url) or clean_url(post_url)
                    post_url = clean_url(post_url)
                    first_line = text.split("\n")[0].strip()
                    title = clean(first_line[:120] if first_line else text[:120])
                    if not title:
                        continue
                    jobs.append({
                        "id": make_id(post_url, title),
                        "title": title,
                        "organisation": clean(handle.replace(".bsky.social", "")),
                        "location": "",
                        "country": "",
                        "source": "Bluesky",
                        "url": job_url,
                        "date_posted": date_str,
                        "closing_date": "",
                        "type": "Social post" if job_url == post_url else "Job listing",
                        "description": clean(text),
                    })
                except Exception as e:
                    print(f"    post parse error: {e}")
        except Exception as e:
            print(f"  ERROR bluesky {handle}: {e}")
        time.sleep(1)
    return jobs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== JobScan scraper starting (Phase 7: + Ashby, SmartRecruiters, "
          "Recruitee, Workable; Canada-specific Adzuna queries) ===")
    existing = load_existing()
    existing["jobs"] = backfill_categories(existing.get("jobs", []))
    existing_ids = {j["id"] for j in existing["jobs"]}
    new_jobs = []

    print("  Running Jobs.ac.uk HTML scraper (/search/{slug})...")
    try:
        results = scrape_jobsac_html()
        added = 0
        for j in results:
            if j["id"] not in existing_ids and passes_filter(j):
                new_jobs.append(j)
                existing_ids.add(j["id"])
                added += 1
        print(f"    +{added} new from Jobs.ac.uk HTML")
    except Exception as e:
        print(f"  ERROR jobs.ac.uk HTML: {e}")

    print("  Running Canadian RSS scrapers (THEunijobs, HigherEdJobs)...")
    try:
        results = scrape_canada_rss()
        added = 0
        for j in results:
            if j["id"] not in existing_ids and passes_filter(j):
                new_jobs.append(j)
                existing_ids.add(j["id"])
                added += 1
        print(f"    +{added} new from Canadian RSS feeds")
    except Exception as e:
        print(f"  ERROR Canadian RSS: {e}")

    print("  Running AcademicWork.ca scraper (CAUT, Canada academic)...")
    try:
        results = scrape_academicwork()
        added = 0
        for j in results:
            if j["id"] not in existing_ids and passes_filter(j):
                new_jobs.append(j)
                existing_ids.add(j["id"])
                added += 1
        print(f"    +{added} new from AcademicWork.ca")
    except Exception as e:
        print(f"  ERROR AcademicWork.ca: {e}")

    print("  Running Adzuna API scraper (UK)...")
    try:
        results = scrape_adzuna("gb", "UK")
        added = 0
        for j in results:
            if j["id"] not in existing_ids and passes_filter(j):
                new_jobs.append(j)
                existing_ids.add(j["id"])
                added += 1
        print(f"    +{added} new from Adzuna UK")
    except Exception as e:
        print(f"  ERROR Adzuna UK: {e}")

    print("  Running Adzuna API scraper (Canada)...")
    try:
        results = scrape_adzuna("ca", "Canada")
        added = 0
        for j in results:
            if j["id"] not in existing_ids and passes_filter(j):
                new_jobs.append(j)
                existing_ids.add(j["id"])
                added += 1
        print(f"    +{added} new from Adzuna Canada")
    except Exception as e:
        print(f"  ERROR Adzuna Canada: {e}")

    print("  Running Reed.co.uk API scraper (UK)...")
    try:
        results = scrape_reed()
        added = 0
        for j in results:
            if j["id"] not in existing_ids and passes_filter(j):
                new_jobs.append(j)
                existing_ids.add(j["id"])
                added += 1
        print(f"    +{added} new from Reed")
    except Exception as e:
        print(f"  ERROR Reed: {e}")

    print("  Running Indeed scraper (UK, best-effort, env-gated)...")
    try:
        results = scrape_indeed()
        added = 0
        for j in results:
            if j["id"] not in existing_ids and passes_filter(j):
                new_jobs.append(j)
                existing_ids.add(j["id"])
                added += 1
        print(f"    +{added} new from Indeed")
    except Exception as e:
        print(f"  ERROR Indeed: {e}")

    print("  Running Greenhouse scraper (industry health/sport tech)...")
    try:
        results = scrape_greenhouse()
        added = 0
        for j in results:
            if j["id"] not in existing_ids and passes_filter(j):
                new_jobs.append(j)
                existing_ids.add(j["id"])
                added += 1
        print(f"    +{added} new from Greenhouse")
    except Exception as e:
        print(f"  ERROR Greenhouse: {e}")

    print("  Running Lever scraper (industry sport-tech / wearables)...")
    try:
        results = scrape_lever()
        added = 0
        for j in results:
            if j["id"] not in existing_ids and passes_filter(j):
                new_jobs.append(j)
                existing_ids.add(j["id"])
                added += 1
        print(f"    +{added} new from Lever")
    except Exception as e:
        print(f"  ERROR Lever: {e}")

    for label, fn in (
        ("Ashby", scrape_ashby),
        ("SmartRecruiters", scrape_smartrecruiters),
        ("Recruitee", scrape_recruitee),
        ("Workable", scrape_workable),
        # Phase 8 (19 Aug 2026): UK university ATS platforms. Same loop, same
        # filter, same dedup - a university is just another employer endpoint.
        ("Oracle ORC", scrape_oracle_orc),
        ("Cambridge", scrape_cambridge),
    ):
        print(f"  Running {label} scraper...")
        try:
            results = fn()
            added = 0
            for j in results:
                if j["id"] not in existing_ids and passes_filter(j):
                    new_jobs.append(j)
                    existing_ids.add(j["id"])
                    added += 1
            print(f"    +{added} new from {label}")
        except Exception as e:
            print(f"  ERROR {label}: {e}")

    print("  Running Bluesky scraper...")
    try:
        bsky_results = scrape_bluesky()
        added = 0
        for j in bsky_results:
            if j["id"] not in existing_ids:
                cats = categorise(j)
                j["categories"] = cats if cats else ["industry_applied"]
                j["fit_score"] = compute_fit_score(j["categories"])
                new_jobs.append(j)
                existing_ids.add(j["id"])
                added += 1
        print(f"    +{added} new from Bluesky")
    except Exception as e:
        print(f"  ERROR bluesky: {e}")

    all_jobs = existing["jobs"] + new_jobs
    all_jobs = prune_old(all_jobs)
    all_jobs = deduplicate(all_jobs)
    all_jobs.sort(key=lambda j: j.get("date_posted") or "", reverse=True)

    print(f"\nTotal jobs: {len(all_jobs)} ({len(new_jobs)} new)")
    save({"jobs": all_jobs})


if __name__ == "__main__":
    main()
