"""
================================================================================
RFP_SCRAPE.PY - Automated tender/RFP scraper for Edgewise Environmental
================================================================================

OVERVIEW (read this first)
--------------------------
This script runs once a day on GitHub Actions. It visits a list of
public procurement websites, looks for tender notices that mention
marine/seabird/MMO/PAM keywords or use one of Edgewise's tracked
procurement category codes, and writes the matches to `rfps.json`.

The static page `rfps.html` then reads that JSON and renders the
results in a private, password-free, search-engine-blocked tracker
that lives at:

    https://liamtp-n.github.io/Consultation-Services/edgewise/Edgewise_rfps.html

Nothing in this script touches a login-walled portal. Every source
listed below publishes its tenders publicly. If a portal we want
sits behind a login (SAP Ariba, Sofia Wind, ABCMI, etc.) it is NOT
scraped here - it appears in the static "portals" list inside
rfps.json instead, as a quick-link tile.

WHO THIS IS FOR
---------------
- Liam Pearson-Noseworthy (site owner) - keeps it running
- Ashley Noseworthy (Edgewise CEO) - the user
- Kyla Graham (Edgewise) - the user
- Anyone else at Edgewise, present or future
- Any LLM / AI assistant they paste this file into for help

If you are an AI assistant reading this: the file is fully
self-documenting. Treat the comments here as instructions on how
the user wants you to help them tune, debug, or extend the script.

WHAT EACH PORTAL LOOKS LIKE
---------------------------
Procurement portals fall into three categories. Knowing which
category a portal is in tells you whether we can scrape it:

  1. OPEN-DATA FEED (best case)
       The portal publishes its tenders as a downloadable file
       (CSV, JSON, RSS/XML) updated regularly. We just download
       and parse. No login, no scraping HTML.
       Examples here: CanadaBuys (CSV), UK Find a Tender (JSON),
       UK Contracts Finder (JSON), World Bank (JSON API),
       TED (EU, JSON API), SAM.gov (US, JSON API).

  2. PUBLIC HTML LISTINGS (medium case)
       The portal shows its tenders on a public web page. No
       login required to see basic info (title, due date, link).
       We download the HTML and parse it with BeautifulSoup.
       Examples: BC Bid public portal, Government of
       Nunavut (nunavuttenders.ca), IMO open tenders, NL Hydro on bidsandtenders.
       Even most procurement portals that REQUIRE login to
       SUBMIT a bid will let you VIEW the basic tender info
       publicly. We grab whatever's public.

  2a. JS-RENDERED LISTINGS (Playwright)
       The portal renders its tender list via JavaScript and
       cannot be read with a plain HTTP request. We launch a
       headless Chromium browser (Playwright), wait for the
       page to fully render, then parse the resulting HTML.
       Example: SPREP (Drupal JS-rendered view).

  3. AUTH-WALLED (skipped)
       Tenders only visible after login (SAP Ariba, members-only
       industry associations like ABCMI). Cannot scrape. These
       appear in the static portals list only.

ADDING A NEW PORTAL
-------------------
1. Find out which of the three categories above it falls into.
2. If category 3, just add it to rfps.json's "portals" array.
3. If category 1 or 2, add a new scrape_xxx() function below.
   Each function returns a list of dicts in the standard record
   shape (see "Output: rfps.json" below). Mirror the existing
   functions - they all follow the same pattern.
4. Append your function name to the SCRAPERS list near the bottom
   of the file (in main()).
5. Add the source name string to SCRAPER_SOURCES.
6. Test locally with `python edgewise/Edgewise_rfp_scrape.py` before pushing.

TUNING WHAT GETS THROUGH THE FILTER
-----------------------------------
There are four lists you can edit from the in-page editor on
Edgewise_rfps.html (or directly in Edgewise_filters.json):

  MARINE_KEYWORDS    Strings to look for in titles/descriptions.
                     If ANY match, the tender is kept. Add
                     keywords that would describe Edgewise work.

  CPV_CODES          Procurement category codes. Covers both
                     Canadian UNSPSC codes (CanadaBuys) and true
                     EU CPV codes (TED, UK FTS). A tender tagged
                     with one of these codes gets kept if it also
                     contains a marine context word.

  EXCLUDE_KEYWORDS   Hard rejects. If ANY of these match the
                     title or description, the tender is dropped
                     even if it matched a keyword.

  MARINE_CONTEXT_WORDS
                     Gate words for the CPV path only. A
                     CPV-tagged tender must also contain at least
                     one of these to pass.

You don't need to be exhaustive. The page on rfps.html has its
own search box and filters - this script is just a coarse
first-pass to keep the JSON file from being thousands of rows.

OUTPUT: rfps.json
-----------------
Two top-level arrays:

  "rfps":    The scraped + manual tender records.
  "portals": A static list of portal quick-links shown at the
             bottom of rfps.html. Edited by hand in rfps.json -
             this script preserves it untouched.

Each "rfps" record has this shape:

  {
    "id":        "16-char hash of url+ref+title - used for dedup",
    "project":   "Project / tender title",
    "entity":    "Buying entity (department, agency, company)",
    "region":    "Canada / UK / Pacific / USA / EU / etc.",
    "status":    "open | watching | bidding | submitted | won | lost | closed",
    "due_date":  "YYYY-MM-DD or empty string",
    "budget":    "Free-text budget if known",
    "reference": "Solicitation/tender reference number",
    "source":    "Name of the source (CanadaBuys, SPREP, etc.)",
    "url":       "Direct link to the public tender notice",
    "summary":   "Short description, max 600 chars",
    "why_fits":  "Auto-filled with which keyword/code matched",
    "notes":     "Free-text notes (manual or auto)",
    "tags":      ["array", "of", "tags"],
    "added":     "YYYY-MM-DD when first scraped"
  }

PRESERVING YOUR MANUAL EDITS
----------------------------
You can hand-edit rfps.json between scraper runs. Three things
the scraper preserves across runs (it does NOT overwrite them):

  1. The entire "portals" array - never touched.
  2. Any RFP whose `source` is not in our scraper list (e.g.
     entries you added from a Gemini scout output). Kept whole.
  3. The `status` field on scraped entries, IF you've changed
     it from "open" to one of the active states. Matched by the
     stable `id` hash. Same for `notes`.

So: the scraper finds new tenders and refreshes details on the
ones it's seen before, but never blows away your annotations.

RETENTION
---------
prune_old() drops anything past its due date by more than 90
days, or scraped more than 90 days ago if no due date. Keeps
rfps.json from growing forever.

SCHEDULING
----------
Configured in .github/workflows/Edgewise_rfp_scrape.yml to run
daily at 10:30 UTC. That's:
  - 08:00 NDT (Newfoundland Daylight Time) Mar-Nov
  - 07:00 NST (Newfoundland Standard Time) Nov-Mar
GitHub Actions cron is fixed to UTC and does not handle DST.
Adjust the cron in the YAML if you'd rather a different time.

To run manually (locally on your laptop):
    python edgewise/Edgewise_rfp_scrape.py

Dependencies (pip install ...):
    requests, beautifulsoup4, lxml, playwright
    (plus: playwright install chromium --with-deps)

To trigger a manual GitHub Actions run without waiting for the
schedule: GitHub repo > Actions tab > "Daily RFP Scrape" >
"Run workflow" button.

TROUBLESHOOTING
---------------
"My favourite portal stopped showing up after the scraper ran"
    A scraper for an HTML-listings portal probably broke after a
    redesign. Check the workflow run log - the function name will
    appear with "fetch failed" or "parse error". Open the portal
    in a browser, view source, find the new HTML structure, and
    update the corresponding scrape_xxx() function. Each scraper
    is isolated - one breaking does NOT break the others.

"I'm getting too many results"
    Tighten MARINE_KEYWORDS (remove broad ones) and/or expand
    EXCLUDE_KEYWORDS. Both can be done from the in-page filter
    editor without touching this file.

"I'm getting too few results"
    Loosen MARINE_KEYWORDS (add synonyms), check that the source
    websites are actually publishing what you expect by opening
    them in a browser, and check the GitHub Actions log for
    "(pre-filter)" counts vs "Passed filter:" - if pre-filter
    is high but post-filter is low, you need broader keywords.
    If pre-filter is also low, the portal is the problem.
"""

# --------------------------------------------------------------------
# Imports
# --------------------------------------------------------------------

import csv             # CanadaBuys CSV parsing
import hashlib         # Stable id hashing
import io              # In-memory CSV buffer
import json            # Output writing, OCDS API parsing
import os              # Reading DOFFIN_API_KEY from environment
import re              # Date parsing, regex matching
import sys             # Exit codes
import time            # Polite delays between paginated requests
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import requests        # HTTP client for everything
from bs4 import BeautifulSoup     # HTML/XML parsing


# --------------------------------------------------------------------
# Output file and global config
# --------------------------------------------------------------------

OUTPUT_FILE = "edgewise/Edgewise_rfps.json"   # Written to edgewise/ subfolder, served by GitHub Pages.
MAX_FIELD_LEN = 600         # Truncate summaries longer than this.
MAX_DAYS_OLD = 90           # Drop closed tenders older than 90 days.
HTTP_TIMEOUT = 30           # Seconds before giving up on a slow source.
SCRAPE_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
}


# --------------------------------------------------------------------
# Filter lists - fallbacks used only when Edgewise_filters.json
# is missing or malformed. Edit keywords from the in-page editor
# or directly in Edgewise_filters.json instead of here.
# --------------------------------------------------------------------

MARINE_KEYWORDS_FALLBACK = [
    # ---- Marine fauna observation - Edgewise core service ----
    "marine mammal", " mmo ", " mmso ", "marine mammal observer",
    "seabird", "sea bird", " sbo ", "seabird observer",
    "protected species observer", " pso ",
    "marine fauna", "marine wildlife",

    # ---- Acoustics and noise - Edgewise specialism ----
    "passive acoustic", " pam ", "pam operator", "pam-",
    "acoustic monitoring", "acoustic mitigation", "bioacoustic",
    "underwater noise", "underwater radiated noise", " urn ",
    "anthropogenic noise", "noise mitigation", "noise impact",
    "noise modelling", "noise modeling",
    "sound source verification", " ssv ",
    "sound source characterisation", "sound source characterization",
    "hydroacoustic", "hydroacoustics",

    # ---- Surveys Edgewise can crew or assess ----
    "seismic survey", "marine geophysical", "marine geotechnical",
    "marine survey", "underwater survey", "subsea cable",
    "marine baseline", "marine monitoring",
    "benthic survey", "benthic habitat",
    "vessel-based survey", "vessel based survey",

    # ---- Environmental assessments / reporting ----
    "environmental effects monitoring", " eem ",
    "marine ecology", "marine conservation",
    "environmental baseline",
    " eia ",

    # ---- Sectors Edgewise targets ----
    "offshore wind", "marine renewable", "tidal energy", "wave energy",
    "subsea", "ocean energy", "blue economy",
    "offshore oil", "offshore gas", "offshore environmental",
    "decommissioning", "metocean",
    "site characterisation", "site characterization",

    # ---- Specific service lines ----
    "abandoned vessel", "abandoned boat", "vessel assessment",
    "oil spill", "spill response", "emergency environmental response",
    "bird handling", "oiled wildlife",
    "marine ornithology", "marine ornithologist",
    "marine spatial planning",
    "marine protected area", " mpa ",
    "species at risk", " sara ",
    "right whale", "north atlantic right whale", " narw ",
    "incidental take",
    "marine licence", "marine license",
    "habitats regulations assessment", " hra ",
    "crown estate", " boem ", "noaa fisheries",
    "aquaculture environmental", "mariculture",
    "dredging", "capital dredging",
    "joint nature conservation", " jncc ",
    "cefas",
]

# CPV_CODES covers both Canadian UNSPSC codes (used by CanadaBuys)
# and true EU CPV codes (used by TED and UK Find a Tender / Contracts Finder).
# The scraper substring-matches against `reference + category_code`, so
# adding EU CPV codes here improves filtering on the UK and EU feeds.
#
# Canadian UNSPSC:
#   70101602 = Wildlife studies
#   70101601 = Animal preservation services
#   70101604 = Habitat conservation
#   70100000 = Forestry, fisheries, wildlife management services
#   77101500 = Environmental management
#
# EU CPV:
#   90711000 = Environmental impact assessment
#   90712000 = Environmental planning
#   90713000 = Environmental issues consultancy
#   90720000 = Environmental protection
#   73111000 = Research laboratory services
#   73210000 = Research consultancy services
#   71351000 = Geological, geophysical, prospecting services
#   71351900 = Geological survey services
#   71351923 = Bathymetric surveying services
#   71351924 = Hydrographic survey services
CPV_CODES_FALLBACK = [
    # Canadian UNSPSC
    "70101602",
    "70101601",
    "70101604",
    "70100000",
    "77101500",
    # EU CPV
    "90711000",
    "90712000",
    "90713000",
    "90720000",
    "73111000",
    "73210000",
    "71351000",
    "71351900",
    "71351923",
    "71351924",
]

EXCLUDE_KEYWORDS_FALLBACK = [
    # ---- Generic facilities ----
    "janitorial", "cleaning service", "catering", "food service",
    "stationery", "office supplies", "printer toner",
    "uniform", "laundry", "office furniture",
    "pest control", "snow removal", "landscaping",
    "lawn maintenance", "silviculture", "grass cutting",
    "vehicle rental", "fuel supply",
    "translation service", "interpreter",
    "medical supplies", "pharmaceutical",

    # ---- IT and digital services ----
    "it support", "software licence", "software license",
    "legal software", "legal solution", "case management software",
    "software solution", "im/it", "im/ it", "data centre",
    "cloud service", "saas", "cyber",

    # ---- Construction and trades ----
    "accommodation", "accommodations", "barracks", "housing",
    "bridge replacement", "culvert", "paving", "paving program",
    "chimney replacement", "library cooling", "cooling tower",
    "roof replacement", "roofing", "kitchen construction",
    "electrical upgrade", "lighting upgrade", "plumbing",
    "building materials", "domestic appliance",
    "modular bridge", "panel bridge",

    # ---- Defence equipment ----
    "heavy equipment replacement", "heavy support equipment",
    "armoured", "armored", "shipbuilding", "shipyard",

    # ---- Misc admin and logistics ----
    "detention guard", "non-emergency towing", "moving services",
    "guest accommodation", "rental trailer",
    "electoral material", "wooden ruler", "plastic bag",
    "metal frame", "parking sign",
    "satellite equipment",
    "freeze dryer",

    # ---- Out-of-scope environmental work ----
    "contaminated site", "remediation construction",
    "hazmat", "hazardous material", "tank assessment",
    "petroleum storage tank", "asbestos",
    "topographic lidar",
    "aerial photography",
    "hazardous waste",

    # ---- Correctional / prison services ----
    "correctional service", "penitentiary", "institution",
    "inmate", "offender", "healing lodge",
    "detention", "rcmp ", "prison",

    # ---- Health / clinical services ----
    "dental",
    "psychiatric", "psychiatry", "psychological",
    "physiotherapy", "physician service", "primary care",
    "dermatology", "medical radiation", "urinalysis",
    "mental health", "exit interview", "pre-employment",
    "ribbon", "boots, ankle", "ankle boot", "boot", "footwear",

    # ---- Defence equipment / military ----
    "ground vehicle", "uncrewed ground", "unmanned ground",
    "military training", "role playing", "role-playing",
    "parachute instructor", "parachutist",
    "signal generator", "agile signal",
    "helicopter", "polar helicopter", "aviation fuel",
    "explosive ordnance", "explosive threat",
    "intelligence enterprise", "command and control",
    "c4isr", "defence intelligence",

    # ---- Furniture / facilities ----
    "furniture for", "furniture fixtures",
    "mobile shelving", "shelving",
    "alarm system", "security management system",
    "perimeter intrusion", "perimeter security",
    "elevator", "elevating device",
    "hvac", "boiler replacement", "boiler heating",

    # ---- Equipment / tools ----
    "fluke insulation", "fluke multimeter", "multimeter",
    "insulation meter",
    "cables and wires", "wire and cable",
    "backhoe", "skid steer", "tractor loader",
    "fertilizer", "fertiliser",
    "static mixer",
    "electric vehicle supply", "evse",
    "buses, electric", "electric bus",
    "automated liquid handler", "aptamer",

    # ---- Grounds / mowing ----
    "mowing", "grounds maintenance",

    # ---- Construction tendering ----
    "building construction services",
    "airport terminal", "terminal renovation",
    "exhibition fit-out", "exhibition fit out",
    "teaching & learning", "teaching and learning",

    # ---- Education / community ----
    "early years", "pre-school", "preschool",
    "education provision", "early years education",
    "refugee", "refugee resettlement",
    "museum", "art gallery", "cultural heritage",

    # ---- Generic professional services frameworks ----
    "professional audit", "task professional services",
    "solutions professional services", "tsps",
    "media monitoring", "printing service",
    "change management consultant",
    "indigenous artist", "indigenous business capacity",

    # ---- Fire / forestry ----
    "sustained action crew",
    "fire suppression",

    # ---- IT / admin noise ----
    "ats replacement", "system support",

    # ---- Generic admin / misc ----
    "tractor",
    "vessel recycling",
    "proservices method of supply",
    "method of supply",
    "audit and support services",
    "pass rfsa", "pass refresh",
    "tspsh", "tssb",
    "industry day",
    "loi - industry",

    # ---- Legal / policy ----
    "article 23", "land claims agreement",
    "independent review of",
]

MARINE_CONTEXT_WORDS_FALLBACK = [
    "marine", "ocean", "oceanic", "vessel", "vessels",
    "subsea", "underwater", "offshore",
    "whale", "dolphin", "porpoise", "cetacean", "pinniped",
    "seal ", "walrus",
    "narwhal", "beluga", "bowhead",
    "seabird", "sea bird",
    "fish",
    "coastal", "estuarine", "intertidal",
    "nearshore", "inshore", "foreshore", "shoreline",
    "harbour", "harbor", "port ", "wharf", "jetty",
    "bay", "inlet", "fjord",
    "shipping", "maritime",
    "hydrographic", "bathymetric",
    "acoustic",
    "spill", "oil spill",
    "water sampling", "water column",
    "benthic", "pelagic", "reef", "shelf", "continental shelf",
    "tidal", " tide ", "tidewater",
    "dredge", "dredging",
    "aquaculture", "mariculture",
    "arctic", "subarctic", "sub-arctic",
    " ice ", "sea ice", "pack ice", "icebreaker", "polar",
]


# --------------------------------------------------------------------
# Filter loader - reads keyword lists from Edgewise_filters.json
# --------------------------------------------------------------------

FILTERS_FILE = "edgewise/Edgewise_filters.json"


def load_filters():
    """Load keyword lists from Edgewise_filters.json. Returns a tuple
    (marine_keywords, cpv_codes, exclude_keywords, marine_context_words).
    Falls back to the in-file _FALLBACK lists on any error."""
    try:
        with open(FILTERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        mk = data.get("marine_keywords") or MARINE_KEYWORDS_FALLBACK
        cc = data.get("cpv_codes") or CPV_CODES_FALLBACK
        ek = data.get("exclude_keywords") or EXCLUDE_KEYWORDS_FALLBACK
        mc = data.get("marine_context_words") or MARINE_CONTEXT_WORDS_FALLBACK
        if not all(isinstance(x, list) and x for x in (mk, cc, ek, mc)):
            raise ValueError("one or more keyword lists is empty or wrong type")
        log(f"Loaded filters from {FILTERS_FILE}: "
            f"{len(mk)} marine, {len(cc)} CPV, {len(ek)} exclude, "
            f"{len(mc)} context words")
        return mk, cc, ek, mc
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        log(f"WARNING: could not load {FILTERS_FILE} ({e}); "
            f"using in-file fallback keyword lists")
        return (MARINE_KEYWORDS_FALLBACK, CPV_CODES_FALLBACK,
                EXCLUDE_KEYWORDS_FALLBACK, MARINE_CONTEXT_WORDS_FALLBACK)


# --------------------------------------------------------------------
# Generic helpers used by every scraper
# --------------------------------------------------------------------

def log(msg):
    """Print a timestamped line. Visible in GitHub Actions run logs."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def make_id(*parts):
    """Stable 16-char md5 hash used for dedup across runs."""
    raw = "|".join(str(p or "") for p in parts).lower().strip()
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def truncate(text, n=MAX_FIELD_LEN):
    """Strip whitespace and cap length. Returns empty string for None."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", str(text)).strip()
    if len(text) <= n:
        return text
    return text[: n - 1].rstrip() + "\u2026"


def parse_iso_date(s):
    """Accept any ISO-ish string, return YYYY-MM-DD or empty."""
    if not s:
        return ""
    try:
        s = re.sub(r"[Tt].*$", "", str(s).strip())
        return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return ""


def parse_uk_date(s):
    """Parse '11 May 2026', '11/05/2026', or '11-May-2026'. Falls back to ISO."""
    if not s:
        return ""
    s = s.strip()
    for fmt in ("%d %B %Y", "%d %b %Y", "%d/%m/%Y", "%d-%m-%Y", "%d-%B-%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return parse_iso_date(s)


def matches_marine(text):
    """Return matched keyword (str) or None. Case-insensitive substring."""
    if not text:
        return None
    t = text.lower()
    for kw in MARINE_KEYWORDS:
        if kw.lower() in t:
            return kw
    return None


def matches_cpv(text):
    """Return matched CPV/UNSPSC code (str) or None."""
    if not text:
        return None
    t = str(text)
    for code in CPV_CODES:
        if code in t:
            return code
    return None


def is_excluded(text):
    """True if any exclude keyword matches."""
    if not text:
        return False
    t = text.lower()
    return any(kw in t for kw in EXCLUDE_KEYWORDS)


def has_marine_context(text):
    """True if the text contains at least one generic marine word.
    Used to gate CPV-only matches."""
    if not text:
        return False
    t = text.lower()
    return any(w in t for w in MARINE_CONTEXT_WORDS)


def passes_filter(rec):
    """The single decision point: should this record be kept?
    Returns (bool, reason_string).

    Logic:
    1. EXCLUDE keyword anywhere -> reject
    2. MARINE_KEYWORD match -> accept
    3. CPV/UNSPSC code match AND marine context word present -> accept
    4. Otherwise -> reject
    """
    haystack = " ".join([
        rec.get("project", ""),
        rec.get("summary", ""),
        rec.get("entity", ""),
        " ".join(rec.get("tags", [])),
    ])
    if is_excluded(haystack):
        return False, None
    kw = matches_marine(haystack)
    if kw:
        clean_kw = kw.strip()
        return True, f"matched marine keyword: \"{clean_kw}\""
    code = matches_cpv(rec.get("reference", "") + " " + rec.get("category_code", ""))
    if code and has_marine_context(haystack):
        return True, f"matched CPV code {code} with marine context"
    return False, None


def build_record(**kwargs):
    """Construct a record with all fields defaulted."""
    return {
        "id": kwargs.get("id") or make_id(
            kwargs.get("url"), kwargs.get("reference"), kwargs.get("project")
        ),
        "project": truncate(kwargs.get("project", ""), 200),
        "entity": truncate(kwargs.get("entity", ""), 150),
        "region": kwargs.get("region", ""),
        "status": kwargs.get("status", "open"),
        "due_date": kwargs.get("due_date", ""),
        "budget": kwargs.get("budget", ""),
        "reference": kwargs.get("reference", ""),
        "source": kwargs.get("source", ""),
        "url": kwargs.get("url", ""),
        "summary": truncate(kwargs.get("summary", "")),
        "why_fits": kwargs.get("why_fits", ""),
        "notes": kwargs.get("notes", ""),
        "tags": kwargs.get("tags", []) or [],
        "added": kwargs.get("added", SCRAPE_DATE),
        "category_code": kwargs.get("category_code", ""),
    }


def safe_get(url, **kwargs):
    """requests.get wrapper that never raises - returns None on failure."""
    try:
        kwargs.setdefault("headers", HEADERS)
        kwargs.setdefault("timeout", HTTP_TIMEOUT)
        r = requests.get(url, **kwargs)
        r.raise_for_status()
        return r
    except requests.RequestException as e:
        log(f"  HTTP error on {url}: {e}")
        return None


# Load filter lists (must happen after helpers are defined).
MARINE_KEYWORDS, CPV_CODES, EXCLUDE_KEYWORDS, MARINE_CONTEXT_WORDS = load_filters()


# ====================================================================
# SCRAPERS - one function per source
# ====================================================================


# --------------------------------------------------------------------
# 1. CanadaBuys - federal Canadian government tenders
# --------------------------------------------------------------------
# Type: OPEN-DATA FEED (CSV)
# Refresh: PSPC updates the CSV every 2 hours, 06:15-22:15 ET.
# Login required: No.

CANADABUYS_CSV = (
    "https://canadabuys.canada.ca/opendata/pub/"
    "openTenderNotice-ouvertAvisAppelOffres.csv"
)


def scrape_canadabuys():
    log("CanadaBuys: fetching open tender notices CSV")
    out = []
    r = safe_get(CANADABUYS_CSV)
    if not r:
        return out

    text = r.content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    count = 0
    for row in reader:
        title = (row.get("title-titre-eng") or row.get("title-titre") or "")
        desc = (row.get("tenderDescription-descriptionAppelOffres-eng")
                or row.get("noticeDescription-descriptionAvis-eng") or "")
        buyer = (row.get("contractingEntityName-nomEntiteContractante-eng")
                 or row.get("buyerName") or "")
        ref = (row.get("referenceNumber-numeroReference")
               or row.get("solicitationNumber-numeroSollicitation") or "")
        url = (row.get("noticeURL-URLavis-eng")
               or row.get("tenderNoticeURL-URLavisAppelOffres-eng") or "")
        # Fallback: build the public tender-notice URL from the reference number.
        # Pattern confirmed: https://canadabuys.canada.ca/en/tender-opportunities/tender-notice/{ref}
        if not url and ref:
            url = "https://canadabuys.canada.ca/en/tender-opportunities/tender-notice/" + ref.lower()
        due = parse_iso_date(
            row.get("expiryDate-dateExpiration")
            or row.get("tenderClosingDate-dateClotureSoumissions") or ""
        )
        cat_code = row.get("procurementCategoryCode-codeCategorieAchats", "")
        region = (row.get("regionsOfDeliveryName-nomRegionsLivraison-eng")
                  or row.get("regionsOfOpportunityName-nomRegionsOpportunite-eng")
                  or "Canada")

        if not title:
            continue

        out.append(build_record(
            project=title, entity=buyer or "Government of Canada",
            region="Canada" + (f" ({region})" if region and region != "Canada" else ""),
            due_date=due, reference=ref,
            source="CanadaBuys", url=url, summary=desc,
            category_code=cat_code,
        ))
        count += 1

    log(f"CanadaBuys: {count} open tenders pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 2. UK Find a Tender - UK above-threshold contracts (>~£139,688)
# --------------------------------------------------------------------
# Type: OPEN-DATA FEED (OCDS JSON API)
# Login required: No.

FIND_A_TENDER_API = "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages"


def scrape_find_a_tender():
    log("Find a Tender (UK): fetching OCDS releases (last 14d)")
    return _ocds_scrape(
        FIND_A_TENDER_API, source_name="Find a Tender (UK)",
        url_template="https://www.find-tender.service.gov.uk/Notice/{id}",
    )


# --------------------------------------------------------------------
# 3. UK Contracts Finder - UK below-threshold contracts
# --------------------------------------------------------------------
# Type: OPEN-DATA FEED (OCDS JSON API)
# Login required: No.

CONTRACTS_FINDER_API = (
    "https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search"
)
CONTRACTS_FINDER_TIMEOUT = 60


def scrape_contracts_finder():
    log("Contracts Finder (UK): fetching OCDS releases (last 14d)")
    return _ocds_scrape(
        CONTRACTS_FINDER_API, source_name="Contracts Finder (UK)",
        url_template="https://www.contractsfinder.service.gov.uk/Notice/{id}",
        timeout=CONTRACTS_FINDER_TIMEOUT,
    )


def _ocds_scrape(api_url, source_name, url_template, timeout=None):
    """Shared OCDS parser used by UK Find a Tender and Contracts Finder."""
    out = []
    since = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%dT00:00:00")
    params = {"updatedFrom": since, "limit": 100, "stages": "tender"}
    cursor = None
    pages = 0

    try:
        while pages < 10:
            if cursor:
                params["cursor"] = cursor
            kwargs = {"params": params}
            if timeout:
                kwargs["timeout"] = timeout
            r = safe_get(api_url, **kwargs)
            if not r:
                break
            pkg = r.json()
            for rel in pkg.get("releases", []):
                rec = _ft_release_to_record(rel, source_name, url_template)
                if rec:
                    out.append(rec)
            nxt = (pkg.get("links", {}) or {}).get("next")
            if not nxt:
                break
            m = re.search(r"cursor=([^&]+)", nxt)
            if not m:
                break
            cursor = m.group(1)
            pages += 1
            time.sleep(0.5)
    except (ValueError, KeyError) as e:
        log(f"{source_name}: parse error - {e}")

    log(f"{source_name}: {len(out)} releases pulled (pre-filter)")
    return out


def _ft_release_to_record(rel, source_name, url_template):
    """Convert one OCDS release into our record shape."""
    tender = rel.get("tender") or {}
    title = tender.get("title") or ""
    if not title:
        return None
    desc = tender.get("description") or ""

    buyer = ""
    for p in (rel.get("parties") or []):
        if "buyer" in (p.get("roles") or []):
            buyer = p.get("name", "")
            break
    if not buyer:
        buyer = (rel.get("buyer") or {}).get("name", "")

    closing = (tender.get("tenderPeriod") or {}).get("endDate", "")

    value = tender.get("value") or {}
    budget = ""
    if value.get("amount"):
        try:
            budget = f"{value.get('currency','')} {float(value['amount']):,.0f}".strip()
        except (TypeError, ValueError):
            pass

    cat_code = str((tender.get("classification") or {}).get("id") or "")
    notice_id = rel.get("id") or rel.get("ocid") or ""
    docs = tender.get("documents") or []
    url = docs[0].get("url") if docs else ""
    if not url and notice_id:
        url = url_template.format(id=notice_id)

    return build_record(
        id=make_id(notice_id, title),
        project=title, entity=buyer or "UK Government", region="UK",
        due_date=parse_iso_date(closing), budget=budget,
        reference=notice_id, source=source_name, url=url,
        summary=desc, category_code=cat_code,
    )


# --------------------------------------------------------------------
# 4. TED (Tenders Electronic Daily) - EU above-threshold procurement
# --------------------------------------------------------------------
# Type: OPEN-DATA FEED (JSON search API v3)
# Login required: No.
# Coverage: All EU member-state public procurement above threshold,
#           plus EEA. Catches Irish, Norwegian, Dutch, Belgian and
#           other European offshore wind and marine environmental work.
#           Also picks up UK FTS notices cross-listed on TED.
#
# API docs: https://ted.europa.eu/api/latest/swagger-ui/index.html
# The v3 search endpoint accepts a POST with a JSON query body.
# We search by publication date (last 14 days) and let the marine
# keyword filter do the heavy lifting - fetching all notices and
# filtering locally is more reliable than TED's free-text search,
# which requires Lucene syntax and has unpredictable stemming.

TED_API = "https://ted.europa.eu/api/latest/notices/search"
TED_PAGE_SIZE = 100   # max allowed per request


def scrape_ted():
    """Scrape TED (EU) for notices published in the last 14 days."""
    log("TED (EU): fetching notices published in last 14 days")
    out = []

    since = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y%m%d")
    today = datetime.now(timezone.utc).strftime("%Y%m%d")

    query_body = {
        "query": f"publication-date>={since} AND publication-date<={today}",
        "fields": [
            "title",
            "notice-type",
            "contracting-body",
            "contract-nature",
            "deadline-for-submission",
            "value-estimated",
            "currency",
            "cpv",
            "place-of-performance",
            "description",
            "document-url",
        ],
        "page": 1,
        "pageSize": TED_PAGE_SIZE,
        "scope": "ALL",
        "language": "EN",
        "onlyLatestVersions": True,
    }

    page = 1
    max_pages = 20   # safety cap - TED can return many thousands of notices

    try:
        while page <= max_pages:
            query_body["page"] = page
            r = requests.post(
                TED_API,
                json=query_body,
                headers={**HEADERS, "Content-Type": "application/json"},
                timeout=HTTP_TIMEOUT,
            )
            if not r.ok:
                log(f"TED: HTTP {r.status_code} on page {page}")
                break

            data = r.json()
            notices = data.get("notices") or data.get("results") or []
            if not notices:
                break

            for notice in notices:
                rec = _ted_notice_to_record(notice)
                if rec:
                    out.append(rec)

            total = data.get("total", 0)
            if page * TED_PAGE_SIZE >= total:
                break
            page += 1
            time.sleep(0.5)

    except (ValueError, KeyError, requests.RequestException) as e:
        log(f"TED: error - {e}")

    log(f"TED (EU): {len(out)} notices pulled (pre-filter)")
    return out


def _ted_notice_to_record(notice):
    """Convert one TED notice dict to our record shape.

    TED v3 API field names are kebab-case strings. The exact schema
    varies slightly by notice type; we use .get() throughout for
    resilience."""
    # Title - TED returns a dict keyed by language code
    title_obj = notice.get("title") or {}
    title = (
        title_obj.get("EN") or title_obj.get("en") or
        next(iter(title_obj.values()), "") if isinstance(title_obj, dict) else str(title_obj)
    )
    if not title:
        return None

    # Description
    desc_obj = notice.get("description") or {}
    if isinstance(desc_obj, dict):
        desc = desc_obj.get("EN") or desc_obj.get("en") or next(iter(desc_obj.values()), "")
    else:
        desc = str(desc_obj)

    # Contracting body
    body = notice.get("contracting-body") or {}
    if isinstance(body, list):
        body = body[0] if body else {}
    entity = body.get("officialName") or body.get("name") or "EU Contracting Authority"

    # Country / place of performance -> region
    place = notice.get("place-of-performance") or {}
    if isinstance(place, list):
        place = place[0] if place else {}
    country_code = place.get("countryCode") or place.get("country") or ""
    region = f"EU ({country_code})" if country_code else "EU"

    # Deadline
    deadline = parse_iso_date(notice.get("deadline-for-submission") or "")

    # Budget
    value = notice.get("value-estimated") or 0
    currency = notice.get("currency") or "EUR"
    budget = ""
    if value:
        try:
            budget = f"{currency} {float(value):,.0f}"
        except (TypeError, ValueError):
            pass

    # CPV codes - list of strings like "90711000-3"
    cpvs = notice.get("cpv") or []
    if isinstance(cpvs, str):
        cpvs = [cpvs]
    # Strip the check digit (last two chars after hyphen) for matching
    cat_code = " ".join(c.split("-")[0] for c in cpvs if c)

    # Notice ID and URL
    notice_id = notice.get("noticeNumber") or notice.get("id") or ""
    url = notice.get("document-url") or ""
    if not url and notice_id:
        url = f"https://ted.europa.eu/en/notice/-/detail/{notice_id}"

    return build_record(
        id=make_id(notice_id, title),
        project=title,
        entity=entity,
        region=region,
        due_date=deadline,
        budget=budget,
        reference=notice_id,
        source="TED (EU)",
        url=url,
        summary=desc,
        category_code=cat_code,
        tags=["EU", "TED"] + ([country_code] if country_code else []),
    )


# --------------------------------------------------------------------
# 5. SAM.gov - US federal procurement
# --------------------------------------------------------------------
# Type: OPEN-DATA FEED (JSON API)
# Login required: No (public search API; full data needs API key but
#                 basic notice search is open).
# Coverage: All US federal agencies. Key buyers for Edgewise:
#   - BOEM (Bureau of Ocean Energy Management) - offshore wind
#     environmental studies, MMO/PAM contract vehicles
#   - NOAA Fisheries / NMFS - marine mammal surveys, acoustics
#   - USACE (Army Corps) - EIA/EEM for coastal infrastructure
#   - NSF - polar/Antarctic marine research
#
# API docs: https://open.gsa.gov/api/get-opportunities-public-api/
# The public opportunities search endpoint needs no API key for
# basic searches. We query for opportunities posted in the last 14
# days with type "p" (presolicitation) or "o" (solicitation).

SAMGOV_API = "https://api.sam.gov/opportunities/v2/search"
SAMGOV_PAGE_SIZE = 100


def scrape_samgov():
    """Scrape SAM.gov for US federal opportunities posted in the last 14 days."""
    log("SAM.gov (US): fetching opportunities posted in last 14 days")
    out = []

    since = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%m/%d/%Y")
    today = datetime.now(timezone.utc).strftime("%m/%d/%Y")

    params = {
        "api_key": "DEMO_KEY",   # DEMO_KEY allows ~30 req/hr; sufficient for daily run
        "postedFrom": since,
        "postedTo": today,
        "ptype": "o,p,k",        # o=solicitation, p=presolicitation, k=combined synopsis
        "limit": SAMGOV_PAGE_SIZE,
        "offset": 0,
    }

    try:
        while True:
            r = safe_get(SAMGOV_API, params=params)
            if not r:
                break

            data = r.json()
            opportunities = data.get("opportunitiesData") or []
            if not opportunities:
                break

            for opp in opportunities:
                rec = _samgov_opp_to_record(opp)
                if rec:
                    out.append(rec)

            total = data.get("totalRecords", 0)
            params["offset"] += SAMGOV_PAGE_SIZE
            if params["offset"] >= total or params["offset"] >= 2000:
                # Hard cap at 2000 records to avoid rate-limit exhaustion.
                # The marine filter will reduce this dramatically.
                break
            time.sleep(0.5)

    except (ValueError, KeyError, requests.RequestException) as e:
        log(f"SAM.gov: error - {e}")

    log(f"SAM.gov (US): {len(out)} opportunities pulled (pre-filter)")
    return out


def _samgov_opp_to_record(opp):
    """Convert one SAM.gov opportunity dict to our record shape."""
    title = (opp.get("title") or "").strip()
    if not title:
        return None

    entity = (opp.get("departmentName") or opp.get("subtierName") or "US Federal Government").strip()
    desc = (opp.get("description") or opp.get("typeOfSetAsideDescription") or "").strip()

    # Location
    place = opp.get("placeOfPerformance") or {}
    state = place.get("state", {}).get("code") or place.get("state", {}).get("name") or ""
    country = place.get("country", {}).get("code") or "USA"
    if country == "USA" and state:
        region = f"USA ({state})"
    else:
        region = "USA"

    # Dates
    response_deadline = parse_iso_date(opp.get("responseDeadLine") or "")
    archive_date = parse_iso_date(opp.get("archiveDate") or "")
    due = response_deadline or archive_date

    notice_id = opp.get("noticeId") or opp.get("solicitationNumber") or ""
    sol_number = opp.get("solicitationNumber") or ""
    url = opp.get("uiLink") or ""
    if not url and notice_id:
        url = f"https://sam.gov/opp/{notice_id}/view"

    # NAICS code - analogous to CPV for US federal procurement
    naics = opp.get("naicsCode") or ""

    return build_record(
        id=make_id(notice_id or sol_number, title),
        project=title,
        entity=entity,
        region=region,
        due_date=due,
        reference=sol_number or notice_id,
        source="SAM.gov (US)",
        url=url,
        summary=desc,
        category_code=naics,
        tags=["USA", "SAM.gov"] + ([entity.split()[0]] if entity else []),
    )


# --------------------------------------------------------------------
# 6. SPREP - Pacific environmental tenders
# --------------------------------------------------------------------
# Type: JS-rendered Drupal page - requires Playwright headless Chromium.
# Login required: No.
# Coverage: Pacific Regional Environment Programme tenders. Low volume
# (~2-5 marine-relevant per year) but directly on-priority for
# Edgewise seabird/marine work in the Pacific.

SPREP_TENDERS_URL = "https://www.sprep.org/tenders"


def scrape_sprep():
    log("SPREP: fetching tenders via Playwright headless Chromium")
    out = []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("SPREP: Playwright not installed - skipping")
        return out

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                )
            )
            page.goto(SPREP_TENDERS_URL, wait_until="networkidle", timeout=60000)
            try:
                page.wait_for_selector("a[href*='/tender/']", timeout=20000)
            except Exception:
                log("SPREP: no tender links appeared after 20s - page may be empty or structure changed")
                browser.close()
                return out
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "lxml")
        seen = set()

        for a in soup.find_all("a", href=re.compile(r"/tender/")):
            href = a["href"]
            if not href.startswith("http"):
                href = "https://www.sprep.org" + href
            if href in seen:
                continue
            seen.add(href)

            title = a.get_text(strip=True)
            if not title or len(title) < 10:
                parent_text = a.parent.get_text(" ", strip=True) if a.parent else ""
                title = parent_text[:200] or title
            if not title or len(title) < 10:
                continue

            parent_text = a.parent.get_text(" ", strip=True) if a.parent else ""
            due = ""
            m = re.search(r"(\d{1,2}\s+\w+\s+\d{4})", parent_text)
            if m:
                due = parse_uk_date(m.group(1))

            out.append(build_record(
                project=title,
                entity="SPREP (Pacific Regional Environment Programme)",
                region="Pacific",
                due_date=due,
                source="SPREP",
                url=href,
                tags=["SPREP", "Pacific"],
            ))

        log(f"SPREP: {len(out)} tenders pulled (pre-filter)")
    except Exception as e:
        log(f"SPREP: Playwright scrape failed - {e}")

    return out


# --------------------------------------------------------------------
# 7. World Bank - Procurement Notices
# --------------------------------------------------------------------
# Type: OPEN-DATA FEED (JSON API v2)
# Login required: No.

WORLDBANK_API = "https://search.worldbank.org/api/v2/procnotices"


def scrape_worldbank():
    log("World Bank: fetching procurement notices (JSON API v2)")
    out = []
    params = {
        "format": "json",
        "rows": 100,
        "srt": "submission_deadline_date",
        "order": "desc",
        "apilang": "en",
        "srce": "both",
    }
    r = safe_get(WORLDBANK_API, params=params)
    if not r:
        return out

    try:
        data = r.json()
    except ValueError:
        log("World Bank: response was not valid JSON")
        return out

    SKIP_KEYS = {"total", "rows", "os", "page"}
    for notice_id, item in data.items():
        if notice_id in SKIP_KEYS or not isinstance(item, dict):
            continue
        title = (item.get("project_name") or item.get("bid_description") or "").strip()
        if not title:
            continue
        country = (item.get("project_ctry_name") or item.get("country_name") or "International").strip()
        deadline = item.get("submission_deadline_date") or ""
        url = f"https://projects.worldbank.org/en/projects-operations/procurement-detail/{notice_id}"
        desc = (item.get("bid_description") or item.get("project_name") or "").strip()
        notice_type = item.get("notice_type") or ""

        out.append(build_record(
            project=title, entity="World Bank", region=country,
            source="World Bank", url=url, summary=desc,
            reference=notice_id,
            notes=f"Type: {notice_type}" if notice_type else "",
            due_date=parse_iso_date(deadline),
            tags=["World Bank"] + ([country] if country and country != "International" else []),
        ))

    log(f"World Bank: {len(out)} notices pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 8. International Maritime Organisation (IMO)
# --------------------------------------------------------------------
# Type: PUBLIC HTML LISTINGS
# Login required: No.

IMO_TENDERS_URL = "https://www.imo.org/en/About/Procurement/Pages/Open-Tenders.aspx"


def scrape_imo():
    log("IMO: scraping open tenders page")
    out = []
    r = safe_get(IMO_TENDERS_URL)
    if not r:
        return out

    soup = BeautifulSoup(r.content, "lxml")
    seen = set()
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        if not text or len(text) < 15:
            continue
        if not re.search(r"\b(tender|rfp|consultancy|services|RFQ|EOI)\b", text, re.I):
            continue
        url = urljoin(IMO_TENDERS_URL, a["href"])
        if url in seen or "imo.org" not in url:
            continue
        seen.add(url)

        parent_text = a.parent.get_text(" ", strip=True) if a.parent else ""
        m = re.search(r"clos\w*[^\d]+(\d{1,2}\s+\w+\s+\d{4})", parent_text, re.I)
        due = parse_uk_date(m.group(1)) if m else ""

        out.append(build_record(
            project=text, entity="International Maritime Organisation",
            region="International", due_date=due,
            source="IMO", url=url, summary=parent_text,
            tags=["IMO", "Maritime"],
        ))

    log(f"IMO: {len(out)} entries pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 9. Caribbean Development Bank
# --------------------------------------------------------------------
# Type: PUBLIC HTML LISTINGS
# Login required: No.

CARIBBEAN_DB_URL = (
    "https://www.caribank.org/work-with-us/procurement/general-procurement-notices"
)


def scrape_caribbean_db():
    log("Caribbean DB: scraping procurement notices")
    out = []
    r = safe_get(CARIBBEAN_DB_URL)
    if not r:
        return out

    soup = BeautifulSoup(r.content, "lxml")
    seen = set()
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        if not text or len(text) < 15:
            continue
        href = a["href"]
        if not re.search(r"/(procurement|document|notice)/", href, re.I):
            continue
        url = urljoin(CARIBBEAN_DB_URL, href)
        if url in seen:
            continue
        seen.add(url)
        out.append(build_record(
            project=text, entity="Caribbean Development Bank",
            region="Caribbean", source="Caribbean Development Bank",
            url=url, tags=["CarDB", "Caribbean"],
        ))

    log(f"Caribbean DB: {len(out)} entries pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 10. BC Bid - British Columbia public sector procurement
# --------------------------------------------------------------------
# Type: PUBLIC HTML LISTINGS
# Login required: No (to view; yes to bid).

BC_BID_URL = "https://www.bcbid.gov.bc.ca/page.aspx/en/rfp/request_browse_public"


def scrape_bc_bid():
    log("BC Bid: scraping public opportunities")
    out = []
    r = safe_get(BC_BID_URL)
    if not r:
        return out

    soup = BeautifulSoup(r.content, "lxml")
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not re.search(r"(rfp_|request_|opportunity)", href, re.I):
            continue
        text = a.get_text(strip=True)
        if not text or len(text) < 10:
            continue
        url = urljoin(BC_BID_URL, href)
        if url in seen:
            continue
        seen.add(url)
        out.append(build_record(
            project=text, entity="BC Public Sector (via BC Bid)",
            region="Canada (BC)", source="BC Bid", url=url,
            tags=["BC", "Canada"],
        ))

    log(f"BC Bid: {len(out)} entries pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 11. NL Hydro - bidsandtenders.ca platform
# --------------------------------------------------------------------

NL_HYDRO_URL = "https://nlhydro.bidsandtenders.ca/Module/Tenders/en"


def scrape_nl_hydro():
    return _scrape_bidsandtenders(
        NL_HYDRO_URL, "NL Hydro",
        "Newfoundland and Labrador Hydro", "Canada (NL)",
    )


BIDSANDTENDERS_NAV_NOISE = {
    "bids homepage", "create account", "sign in", "login", "log in",
    "vendor guide", "buyer guide", "register", "support",
    "open bids", "closed bids", "awarded bids", "all bids",
    "browse bids", "view all", "home", "contact us",
}


def _scrape_bidsandtenders(url, source_name, entity, region):
    """Generic bidsandtenders.ca scraper."""
    log(f"{source_name}: scraping {url}")
    out = []
    r = safe_get(url)
    if not r:
        return out

    soup = BeautifulSoup(r.content, "lxml")
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        href_lower = href.lower()
        if "/module/tenders" not in href_lower:
            continue
        has_guid = bool(re.search(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            href_lower
        ))
        has_detail_or_view = "tender/detail" in href_lower or "tender/view" in href_lower
        if not (has_guid or has_detail_or_view):
            continue
        text = a.get_text(strip=True)
        if not text or len(text) < 10:
            continue
        if text.lower().strip() in BIDSANDTENDERS_NAV_NOISE:
            continue
        full = urljoin(url, href)
        if full in seen or full == url:
            continue
        seen.add(full)
        out.append(build_record(
            project=text, entity=entity, region=region,
            source=source_name, url=full, tags=[source_name],
        ))

    log(f"{source_name}: {len(out)} tenders pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 12. Government of Nova Scotia - Procurement Portal
# --------------------------------------------------------------------

NS_PROCUREMENT_URL = "https://procurement.novascotia.ca/ns-tenders.aspx"


def scrape_ns_procurement():
    log("Nova Scotia Procurement: scraping public notices")
    out = []
    r = safe_get(NS_PROCUREMENT_URL)
    if not r:
        return out

    soup = BeautifulSoup(r.content, "lxml")
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not re.search(r"(tender|rfp|notice)", href, re.I):
            continue
        text = a.get_text(strip=True)
        if not text or len(text) < 10:
            continue
        full = urljoin(NS_PROCUREMENT_URL, href)
        if full in seen:
            continue
        seen.add(full)
        out.append(build_record(
            project=text, entity="Government of Nova Scotia",
            region="Canada (NS)", source="NS Procurement",
            url=full, tags=["NS", "Canada"],
        ))

    log(f"NS Procurement: {len(out)} entries pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 13. Government of Nunavut - nunavuttenders.ca
# --------------------------------------------------------------------
# Type: PUBLIC HTML LISTINGS (ASP.NET table, no JS challenge)
# Login required: No (to view; yes to submit a bid via the portal).
# Note: www.gov.nu.ca/en/business/tenders is Cloudflare-protected, but
# nunavuttenders.ca serves the same data without any bot protection.
# Captures GN departmental tenders including environmental services,
# aerial wildlife surveys, marine infrastructure, and Arctic logistics.

NUNAVUT_TENDERS_URL = "https://www.nunavuttenders.ca/"
NUNAVUT_TENDERS_BASE = "https://www.nunavuttenders.ca"


def scrape_nunavut():
    log("Nunavut Tenders: scraping nunavuttenders.ca")
    out = []
    r = safe_get(
        NUNAVUT_TENDERS_URL,
        headers={**HEADERS, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
    )
    if not r:
        return out

    soup = BeautifulSoup(r.content, "lxml")
    seen = set()

    # Page renders one main ASP.NET GridView table with 8 fixed columns:
    # Ref# | Description | FOB Point Or Location | Issued Date |
    # Contact Person | Phone/Email | Closing Date And Time | Submit
    table = None
    for t in soup.find_all("table"):
        rows = t.find_all("tr")
        if len(rows) > 3:
            header_cells = [c.get_text(strip=True) for c in rows[0].find_all(["td", "th"])]
            if "Description" in header_cells and "Closing Date And Time" in header_cells:
                table = t
                break

    if not table:
        log("Nunavut Tenders: could not find tenders table - page structure may have changed")
        return out

    rows = table.find_all("tr")
    for row in rows[1:]:
        cells = row.find_all("td")
        if len(cells) < 7:
            continue
        texts = [c.get_text(strip=True) for c in cells]

        ref = texts[0]
        title = texts[1]
        location = texts[2]
        closing_raw = texts[6] if len(texts) > 6 else ""

        if not title or len(title) < 5:
            continue

        link_tag = cells[0].find("a", href=True)
        if not link_tag:
            link_tag = row.find("a", href=re.compile(r"op=lnk"))
        href = link_tag["href"] if link_tag else ""
        if href and not href.startswith("http"):
            href = NUNAVUT_TENDERS_BASE + "/" + href.lstrip("/")
        url = href or NUNAVUT_TENDERS_URL

        if url in seen:
            continue
        seen.add(url)

        # Closing date format: "2026-05-15 16:00 ET"
        due = parse_iso_date(closing_raw[:10]) if closing_raw else ""

        out.append(build_record(
            project=title,
            entity="Government of Nunavut",
            region="Canada (NU)",
            due_date=due,
            reference=ref,
            source="Nunavut Tenders",
            url=url,
            notes=f"Location: {location}" if location else "",
            tags=["Nunavut", "Arctic", "Canada", "GN"],
        ))

    log(f"Nunavut Tenders: {len(out)} tenders pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 14. BC Ferries - Procurement
# --------------------------------------------------------------------

BC_FERRIES_URL = "https://www.bcferries.com/our-company/procurement"


def scrape_bc_ferries():
    log("BC Ferries: scraping procurement page")
    out = []
    r = safe_get(BC_FERRIES_URL)
    if not r:
        return out

    soup = BeautifulSoup(r.content, "lxml")
    seen = set()
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        if not text or len(text) < 10:
            continue
        if not re.search(r"\b(RFP|RFT|RFQ|tender|opportunity|expression)\b",
                         text + " " + href, re.I):
            continue
        full = urljoin(BC_FERRIES_URL, href)
        if full in seen:
            continue
        seen.add(full)
        out.append(build_record(
            project=text, entity="BC Ferries",
            region="Canada (BC)", source="BC Ferries",
            url=full, tags=["BC Ferries", "Marine"],
        ))

    log(f"BC Ferries: {len(out)} entries pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 15. LNG Canada - Contracting & Procurement
# --------------------------------------------------------------------

LNG_CANADA_URL = "https://www.lngcanada.ca/opportunities/contracting-procurement/"


def scrape_lng_canada():
    log("LNG Canada: scraping contracting page")
    out = []
    r = safe_get(LNG_CANADA_URL)
    if not r:
        return out

    soup = BeautifulSoup(r.content, "lxml")
    seen = set()
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        if not text or len(text) < 10:
            continue
        if not re.search(r"\b(RFP|RFT|RFQ|tender|opportunity|contract|expression)\b",
                         text + " " + href, re.I):
            continue
        full = urljoin(LNG_CANADA_URL, href)
        if full in seen:
            continue
        seen.add(full)
        out.append(build_record(
            project=text, entity="LNG Canada",
            region="Canada (BC)", source="LNG Canada",
            url=full, tags=["LNG Canada", "BC"],
        ))

    log(f"LNG Canada: {len(out)} entries pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 16. MERX - Government of NL solicitations
# --------------------------------------------------------------------

MERX_NL_URL = "https://www.merx.com/govnl/solicitations/open-bids?pageNumber=1"

MERX_NAV_NOISE = {
    "open solicitations", "closed solicitations", "awarded solicitations",
    "all solicitations", "bids homepage", "homepage", "search",
    "filter", "sort", "next", "previous",
}


def scrape_merx_nl():
    log("MERX NL: scraping public bid listings")
    out = []
    r = safe_get(MERX_NL_URL)
    if not r:
        return out

    soup = BeautifulSoup(r.content, "lxml")
    seen = set()
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        if not text or len(text) < 15:
            continue
        if text.lower().strip() in MERX_NAV_NOISE:
            continue
        if "/solicitations/" not in href and "/solicitation-detail/" not in href:
            continue
        if not re.search(r"/\d{6,}(?:[/?#]|$)", href):
            continue
        full = urljoin(MERX_NL_URL, href)
        if full in seen:
            continue
        seen.add(full)
        out.append(build_record(
            project=text, entity="Government of Newfoundland and Labrador",
            region="Canada (NL)", source="MERX (NL)",
            url=full,
            notes="MERX may require Pay-as-you-go to download full bid docs.",
            tags=["NL", "Canada", "MERX"],
        ))

    log(f"MERX NL: {len(out)} entries pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 17. Public Contracts Scotland - Crown Estate Scotland, NatureScot,
#     Marine Scotland, ScotWind-related work
# --------------------------------------------------------------------
# Type: RSS feeds (CPV-filtered)
# Login required: No.

PCS_SCOTLAND_CPV_TARGETS = [
    "90711000", "90712000", "90713000", "90714000",
    "71313000", "71313400", "71313440", "71313450",
    "73000000", "73110000", "73210000",
    "71351000", "71355000",
]
PCS_SCOTLAND_RSS_BASE = (
    "https://www.publiccontractsscotland.gov.uk/Search/Search_RSS.aspx"
)


def scrape_pcs_scotland():
    log("PCS Scotland: fetching RSS feeds by CPV")
    out = []
    seen = set()

    for cpv in PCS_SCOTLAND_CPV_TARGETS:
        r = safe_get(
            PCS_SCOTLAND_RSS_BASE,
            params={"CPV": cpv},
            headers={**HEADERS, "Accept": "application/rss+xml, application/xml, text/xml"},
        )
        if not r:
            continue

        soup = BeautifulSoup(r.content, "lxml-xml")
        for item in soup.find_all("item"):
            title = (item.find("title") or {}).get_text(strip=True)
            link = (item.find("link") or {}).get_text(strip=True)
            desc = (item.find("description") or {}).get_text(strip=True)
            pub_date = (item.find("pubDate") or {}).get_text(strip=True)
            guid = (item.find("guid") or {}).get_text(strip=True)

            if not title or not link:
                continue
            if link in seen:
                continue
            seen.add(link)

            # PCS items often embed closing date in description as "Closing Date: DD/MM/YYYY"
            due = ""
            m = re.search(r"[Cc]losing\s+[Dd]ate[:\s]+(\d{2}/\d{2}/\d{4})", desc)
            if m:
                due = parse_uk_date(m.group(1))

            # Extract buyer from description if present
            entity = ""
            m2 = re.search(r"[Cc]ontracting\s+[Aa]uthority[:\s]+([^\n<]+)", desc)
            if m2:
                entity = m2.group(1).strip()

            out.append(build_record(
                project=title,
                entity=entity or "Scottish Public Body",
                region="UK (Scotland)",
                due_date=due,
                reference=guid or link,
                source="PCS Scotland",
                url=link,
                summary=truncate(desc, 400),
                category_code=cpv,
                tags=["Scotland", "UK", "PCS"],
            ))

    log(f"PCS Scotland: {len(out)} entries pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 18. New Brunswick Opportunities Network (NBON)
# --------------------------------------------------------------------
# Type: PUBLIC HTML LISTINGS
# Login required: No (to view; yes to download documents).
# Coverage: NB Power, DNRED Fisheries and Aquaculture, Bay of Fundy,
#           Saint John Harbour, provincial departments.

NBON_URL = "https://nbon-rpanb.gnb.ca/PublicTenderOpportunities.aspx"
NBON_BASE = "https://nbon-rpanb.gnb.ca"


def scrape_nbon():
    log("NBON (New Brunswick): scraping public tender listings")
    out = []
    r = safe_get(NBON_URL)
    if not r:
        return out

    soup = BeautifulSoup(r.content, "lxml")
    seen = set()

    # NBON uses a gridview table; rows have alternating CSS classes
    table = soup.find("table", id=re.compile(r"GridView|gvTenders|tblTenders", re.I))
    if not table:
        # Fall back: any table with more than 5 rows
        tables = soup.find_all("table")
        table = next((t for t in tables if len(t.find_all("tr")) > 5), None)

    if not table:
        log("NBON: no tender table found - page structure may have changed")
        return out

    rows = table.find_all("tr")
    for row in rows[1:]:   # skip header
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        texts = [c.get_text(strip=True) for c in cells]
        link_tag = row.find("a", href=True)
        href = link_tag["href"] if link_tag else ""
        if href and not href.startswith("http"):
            href = NBON_BASE + "/" + href.lstrip("/")

        # Column order varies; take the longest cell as title if no link text
        title = link_tag.get_text(strip=True) if link_tag else texts[1] if len(texts) > 1 else texts[0]
        if not title or len(title) < 8:
            continue
        if href in seen:
            continue
        seen.add(href or title)

        # Last column is usually closing date
        due_raw = texts[-1]
        due = parse_uk_date(due_raw) or parse_iso_date(due_raw)

        out.append(build_record(
            project=title,
            entity="Government of New Brunswick",
            region="Canada (NB)",
            due_date=due,
            reference=texts[0] if texts else "",
            source="NBON",
            url=href or NBON_URL,
            tags=["NB", "Canada", "NBON"],
        ))

    log(f"NBON: {len(out)} tenders pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 19. Government of Northwest Territories (GNWT)
# --------------------------------------------------------------------
# Type: PUBLIC HTML LISTINGS (via OpenNWT mirror)
# Login required: No.
# Coverage: Inuvialuit Settlement Region, Beaufort Sea, GNWT
#           Environment & Climate Change, NWT Power Corporation.

GNWT_URL = "https://contracts.opennwt.ca/tenders/?status=open"
GNWT_BASE = "https://contracts.opennwt.ca"
GNWT_OFFICIAL = "https://contracts.fin.gov.nt.ca/"


def scrape_gnwt():
    log("GNWT (Northwest Territories): scraping OpenNWT mirror")
    out = []
    r = safe_get(GNWT_URL)
    if not r:
        # Fall back to official portal HTML
        r = safe_get(GNWT_OFFICIAL)
        if not r:
            return out

    soup = BeautifulSoup(r.content, "lxml")
    seen = set()

    # OpenNWT renders tenders as cards or table rows
    for card in soup.select(".tender, .tender-card, article.post, tr"):
        title_el = card.select_one("h2, h3, h4, .title, .tender-title, td a")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not title or len(title) < 8:
            continue

        link_el = title_el if title_el.name == "a" else title_el.find("a")
        if not link_el:
            link_el = card.find("a", href=True)
        href = (link_el or {}).get("href", "") if link_el else ""
        if href and not href.startswith("http"):
            href = GNWT_BASE + href

        if href in seen:
            continue
        seen.add(href or title)

        ddl_el = card.select_one(".deadline, .closes, .close-date, time, .date")
        due_raw = ddl_el.get_text(strip=True) if ddl_el else ""
        due = parse_uk_date(due_raw) or parse_iso_date(due_raw)

        org_el = card.select_one(".buyer, .department, .org, .organization")
        entity = org_el.get_text(strip=True) if org_el else "Government of Northwest Territories"

        ref_el = card.select_one(".reference, .ref, .bid-number")
        ref = ref_el.get_text(strip=True) if ref_el else ""

        out.append(build_record(
            project=title,
            entity=entity,
            region="Canada (NT)",
            due_date=due,
            reference=ref,
            source="GNWT",
            url=href or GNWT_OFFICIAL,
            tags=["NWT", "Arctic", "Canada", "GNWT"],
        ))

    log(f"GNWT: {len(out)} tenders pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 20. SEAO Quebec - Système électronique d'appel d'offres
# --------------------------------------------------------------------
# Type: OPEN-DATA FEED (weekly JSON via Données Québec CKAN catalog)
# Login required: No.
# Coverage: Hydro-Québec, Société du Plan Nord, MELCCFP (environment
#           ministry), municipalities along Gulf of St. Lawrence.

SEAO_CATALOG_URL = (
    "https://www.donneesquebec.ca/recherche/api/3/action/package_show"
    "?id=d23b2e02-085d-43e5-9e6e-e1d558ebfdd5"
)


def scrape_seao_qc():
    log("SEAO Quebec: fetching weekly JSON from Données Québec")
    out = []

    # Step 1: resolve current weekly resource URL from catalog
    r = safe_get(SEAO_CATALOG_URL)
    if not r:
        return out
    try:
        pkg = r.json().get("result", {})
    except ValueError:
        log("SEAO Quebec: catalog JSON parse error")
        return out

    resources = pkg.get("resources", [])
    json_resources = [
        res for res in resources
        if (res.get("format", "").upper() == "JSON"
            and ("hebdo_" in (res.get("url") or "") or "hebdo_" in (res.get("name") or "")))
    ]
    if not json_resources:
        # Fall back: any JSON resource
        json_resources = [res for res in resources if res.get("format", "").upper() == "JSON"]
    if not json_resources:
        log("SEAO Quebec: no JSON resource found in catalog")
        return out

    json_resources.sort(key=lambda x: x.get("last_modified", ""), reverse=True)
    feed_url = json_resources[0]["url"]
    log(f"SEAO Quebec: fetching {feed_url}")

    # Step 2: download the weekly file (can be large - use streaming read)
    feed_r = safe_get(feed_url, timeout=180)
    if not feed_r:
        return out
    try:
        data = feed_r.json()
    except ValueError:
        log("SEAO Quebec: weekly feed JSON parse error")
        return out

    # The weekly file is either a list of notices or a dict with a list key
    notices = data if isinstance(data, list) else (
        data.get("avis") or data.get("releases") or data.get("notices") or []
    )

    for n in notices:
        title = n.get("titre") or n.get("title") or ""
        if not title:
            continue
        org = n.get("organisme") or (n.get("buyer") or {}).get("name") or ""
        ref = n.get("numeroSeao") or n.get("ocid") or n.get("numeroReference") or ""
        ddl = (
            n.get("dateFermeture") or n.get("dateCloture")
            or (n.get("tender") or {}).get("tenderPeriod", {}).get("endDate") or ""
        )
        url = (
            n.get("url") or n.get("lien")
            or (f"https://www.seao.ca/OpportunitePublication/UniqueAvis.aspx?ItemId={ref}" if ref else "")
        )
        unspsc = n.get("unspsc") or n.get("classification") or ""
        category_code = (
            " ".join(unspsc) if isinstance(unspsc, list) else str(unspsc)
        )

        out.append(build_record(
            project=title,
            entity=org or "Québec Public Body",
            region="Canada (QC)",
            due_date=parse_iso_date(ddl) or parse_uk_date(ddl),
            reference=str(ref),
            source="SEAO Quebec",
            url=url,
            category_code=category_code,
            tags=["QC", "Canada", "SEAO"],
        ))

    log(f"SEAO Quebec: {len(out)} notices pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 21. eTenders Ireland - Marine Institute, MARA, NPWS, IFI
# --------------------------------------------------------------------
# Type: OPEN-DATA FEED (OCDS-style CSV/JSON via data.gov.ie CKAN)
# Login required: No.
# Coverage: Marine Institute Ireland, Maritime Area Regulatory
#           Authority (MARA), NPWS, Inland Fisheries Ireland.
#           Celtic Sea floating-wind consenting work.

ETENDERS_IE_CATALOG = (
    "https://data.gov.ie/api/3/action/package_show"
    "?id=contract-notices-published-on-etenders"
)
ETENDERS_IE_FALLBACK = (
    "https://www.etenders.gov.ie/epps/cft/listContractNotices.do"
)


def scrape_etenders_ie():
    log("eTenders Ireland: fetching OCDS feed from data.gov.ie")
    out = []

    r = safe_get(ETENDERS_IE_CATALOG, timeout=45)
    if not r:
        return out
    try:
        pkg = r.json().get("result", {})
    except ValueError:
        log("eTenders Ireland: catalog JSON parse error")
        return out

    resources = pkg.get("resources", [])
    feed_resources = [
        res for res in resources
        if res.get("format", "").upper() in ("CSV", "JSON")
    ]
    if not feed_resources:
        log("eTenders Ireland: no CSV/JSON resources in catalog")
        return out

    feed_resources.sort(key=lambda x: x.get("last_modified", ""), reverse=True)
    target = feed_resources[0]
    feed_url = target["url"]
    log(f"eTenders Ireland: fetching {feed_url}")

    feed_r = safe_get(feed_url, timeout=120)
    if not feed_r:
        return out

    rows = []
    if target["format"].upper() == "JSON":
        try:
            data = feed_r.json()
            rows = data if isinstance(data, list) else (
                data.get("releases") or data.get("data") or []
            )
        except ValueError:
            log("eTenders Ireland: JSON parse error on feed")
            return out
    else:
        try:
            rows = list(csv.DictReader(io.StringIO(
                feed_r.content.decode("utf-8-sig", errors="replace")
            )))
        except Exception as e:
            log(f"eTenders Ireland: CSV parse error - {e}")
            return out

    for row in rows:
        if isinstance(row, dict):
            title = (
                row.get("title") or row.get("Title")
                or row.get("notice_title") or row.get("BT-21-Lot") or ""
            )
            org = (
                row.get("buyer_name") or row.get("ContractingAuthority")
                or row.get("organisation") or ""
            )
            ref = (
                row.get("notice_id") or row.get("ID") or row.get("ocid")
                or row.get("noticeId") or ""
            )
            ddl = (
                row.get("deadline") or row.get("ClosingDate")
                or row.get("closing_date") or ""
            )
            cpv = row.get("cpv") or row.get("CPV") or row.get("cpvCode") or ""
            url = (
                row.get("url") or row.get("URL") or row.get("link")
                or (f"https://www.etenders.gov.ie/epps/cft/listContractNotices.do?ID={ref}" if ref else ETENDERS_IE_FALLBACK)
            )
        else:
            # OCDS release object
            tender = (row.get("tender") or {}) if isinstance(row, dict) else {}
            title = tender.get("title") or ""
            org = (row.get("buyer") or {}).get("name") or ""
            ref = row.get("ocid") or ""
            ddl = (tender.get("tenderPeriod") or {}).get("endDate") or ""
            cpv = str((tender.get("classification") or {}).get("id") or "")
            url = ETENDERS_IE_FALLBACK

        if not title:
            continue

        out.append(build_record(
            project=title,
            entity=org or "Irish Public Body",
            region="Ireland",
            due_date=parse_iso_date(ddl) or parse_uk_date(ddl),
            reference=str(ref),
            source="eTenders Ireland",
            url=url,
            category_code=cpv,
            tags=["Ireland", "EU", "eTenders"],
        ))

    log(f"eTenders Ireland: {len(out)} notices pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 22. Sell2Wales - Natural Resources Wales, Welsh Government Marine
# --------------------------------------------------------------------
# Type: RSS feeds (CPV-filtered, same Proactis platform as PCS)
# Login required: No.
# Coverage: NRW (Natural Resources Wales), Welsh Government Marine
#           Directorate, Celtic Sea floating-wind authorities.

SELL2WALES_CPV_TARGETS = [
    "90711000", "90712000", "90713000",
    "71313000", "71313440", "71313450",
    "73000000", "73110000", "73210000",
    "71351000", "71355000",
]
SELL2WALES_RSS_BASE = "https://www.sell2wales.gov.wales/Search/Search_RSS.aspx"


def scrape_sell2wales():
    log("Sell2Wales: fetching RSS feeds by CPV")
    out = []
    seen = set()

    for cpv in SELL2WALES_CPV_TARGETS:
        r = safe_get(
            SELL2WALES_RSS_BASE,
            params={"CPV": cpv},
            headers={**HEADERS, "Accept": "application/rss+xml, application/xml, text/xml"},
        )
        if not r:
            continue

        soup = BeautifulSoup(r.content, "lxml-xml")
        for item in soup.find_all("item"):
            title = (item.find("title") or {}).get_text(strip=True)
            link = (item.find("link") or {}).get_text(strip=True)
            desc = (item.find("description") or {}).get_text(strip=True)
            guid = (item.find("guid") or {}).get_text(strip=True)

            if not title or not link:
                continue
            if link in seen:
                continue
            seen.add(link)

            due = ""
            m = re.search(r"[Cc]losing\s+[Dd]ate[:\s]+(\d{2}/\d{2}/\d{4})", desc)
            if m:
                due = parse_uk_date(m.group(1))

            entity = ""
            m2 = re.search(r"[Cc]ontracting\s+[Aa]uthority[:\s]+([^\n<]+)", desc)
            if m2:
                entity = m2.group(1).strip()

            out.append(build_record(
                project=title,
                entity=entity or "Welsh Public Body",
                region="UK (Wales)",
                due_date=due,
                reference=guid or link,
                source="Sell2Wales",
                url=link,
                summary=truncate(desc, 400),
                category_code=cpv,
                tags=["Wales", "UK", "Sell2Wales"],
            ))

    log(f"Sell2Wales: {len(out)} entries pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 23. Asian Development Bank (ADB) - procurement notices
# --------------------------------------------------------------------
# Type: PUBLIC HTML LISTINGS
# Login required: No.
# Coverage: ADB-financed projects across Asia and the Pacific. Some
#           Pacific island marine work, fisheries projects, coastal
#           climate adaptation. Geography is mostly Asia but Pacific
#           islands occasionally appear and are on-priority for
#           Edgewise's seabird/marine work.

ADB_NOTICES_URL = (
    "https://www.adb.org/site/business-opportunities/operational-procurement/"
    "goods-services/notices-current"
)
ADB_BASE = "https://www.adb.org"


def scrape_adb():
    log("ADB: scraping current procurement notices")
    out = []
    r = safe_get(ADB_NOTICES_URL)
    if not r:
        return out

    soup = BeautifulSoup(r.content, "lxml")
    seen = set()

    # ADB renders notices as table rows or list items linking to detail pages
    # whose URLs sit under /projects/<id>/* or /tenders/<id>.
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        if not text or len(text) < 15:
            continue
        if not re.search(r"/(projects|tenders|business-opportunities)/", href, re.I):
            continue
        # Skip nav/category links (very short URLs)
        if href.rstrip("/").count("/") < 3:
            continue
        full = urljoin(ADB_BASE, href)
        if full in seen:
            continue
        seen.add(full)

        parent_text = a.parent.get_text(" ", strip=True) if a.parent else ""
        # ADB rows often include a country and a closing date as plain text
        country_match = re.search(
            r"\b(Bangladesh|Bhutan|Cambodia|China|Fiji|India|Indonesia|"
            r"Kazakhstan|Kiribati|Lao|Malaysia|Maldives|Marshall|Micronesia|"
            r"Mongolia|Myanmar|Nauru|Nepal|Pakistan|Palau|Papua|Philippines|"
            r"Samoa|Solomon|Sri Lanka|Tajikistan|Thailand|Timor|Tonga|"
            r"Turkmenistan|Tuvalu|Uzbekistan|Vanuatu|Viet Nam|Vietnam)\b",
            parent_text, re.I,
        )
        country = country_match.group(1) if country_match else ""
        ddl_match = re.search(
            r"(\d{1,2}\s+\w+\s+\d{4})", parent_text,
        )
        due = parse_uk_date(ddl_match.group(1)) if ddl_match else ""

        out.append(build_record(
            project=text,
            entity="Asian Development Bank",
            region="Asia-Pacific" + (f" ({country})" if country else ""),
            due_date=due,
            source="ADB",
            url=full,
            summary=parent_text[:400],
            tags=["ADB", "Asia-Pacific"] + ([country] if country else []),
        ))

    log(f"ADB: {len(out)} entries pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 24. African Development Bank (AfDB) - corporate procurement
# --------------------------------------------------------------------
# Type: PUBLIC HTML LISTINGS
# Login required: No.
# Coverage: AfDB-financed projects across Africa. Coastal/marine work
#           is rarer than ADB but does include West African and East
#           African coastal climate-adaptation studies and small-scale
#           fisheries work.

AFDB_NOTICES_URL = (
    "https://www.afdb.org/en/about-us/corporate-procurement/"
    "procurement-notices/current-solicitations"
)
AFDB_BASE = "https://www.afdb.org"


def scrape_afdb():
    log("AfDB: scraping current solicitations")
    out = []
    r = safe_get(AFDB_NOTICES_URL)
    if not r:
        return out

    soup = BeautifulSoup(r.content, "lxml")
    seen = set()

    # AfDB lists solicitations with reference numbers like
    # "ADB/RFP/TCGS/2026/0041" plus a publication and deadline date.
    for row in soup.find_all(["article", "div", "li", "tr"]):
        text = row.get_text(" ", strip=True)
        if not text or len(text) < 20:
            continue
        ref_match = re.search(
            r"\b(?:ADB|AfDB|AFDB)/[A-Z0-9/-]+/\d{4}/\d{3,5}\b", text
        )
        if not ref_match:
            continue
        ref = ref_match.group(0)
        a = row.find("a", href=True)
        if not a:
            continue
        href = a["href"]
        full = urljoin(AFDB_BASE, href)
        if full in seen:
            continue
        seen.add(full)

        title = a.get_text(strip=True)
        if not title or len(title) < 10:
            # Fall back to the reference if the link text is too thin
            title = ref
        ddl_match = re.search(
            r"Deadline\s*[Dd]ate\s*:?\s*(\d{1,2}[-/\s]\w+[-/\s]\d{4})", text,
        )
        due = parse_uk_date(ddl_match.group(1)) if ddl_match else ""

        out.append(build_record(
            project=title,
            entity="African Development Bank",
            region="Africa",
            due_date=due,
            reference=ref,
            source="AfDB",
            url=full,
            summary=text[:400],
            tags=["AfDB", "Africa"],
        ))

    log(f"AfDB: {len(out)} entries pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 25. UN Global Marketplace (UNGM)
# --------------------------------------------------------------------
# Type: PUBLIC SEARCH ENDPOINT (returns HTML fragments via POST)
# Login required: No.
# Coverage: 54 UN organisations and UN-affiliated bodies publish their
#           procurement notices here, including UNDP, UNEP, UNOPS, FAO,
#           WFP, WHO, UNESCO, UNICEF, UNHCR, IMO, IAEA, UNFCCC, plus
#           World Bank, ADB, AfDB and others that publish notices to
#           UNGM in addition to their own portals.
# How it works: the public Notice page is JavaScript-rendered, but the
#           AJAX endpoint it calls (POST /Public/Notice/Search with a
#           JSON body) is reachable directly. The server returns a
#           pre-rendered HTML table fragment which we parse with
#           BeautifulSoup. Each page returns up to 15 rows regardless
#           of PageSize requested, so we paginate.

UNGM_SEARCH_URL = "https://www.ungm.org/Public/Notice/Search"
UNGM_NOTICE_URL = "https://www.ungm.org/Public/Notice/{id}"
UNGM_MAX_PAGES = 20   # 20 x 15 = up to 300 most recent active notices


def scrape_ungm():
    """UNGM - UN Global Marketplace. Active procurement opportunities."""
    log("UNGM: fetching active procurement opportunities")
    out = []

    headers = {
        **HEADERS,
        "Content-Type": "application/json",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://www.ungm.org",
        "Referer": "https://www.ungm.org/Public/Notice",
    }

    seen_ids = set()
    page = 0

    try:
        while page < UNGM_MAX_PAGES:
            body = {
                "PageIndex": page,
                "PageSize": 100,           # server caps at ~15; we still ask
                "SortField": "DatePublished",
                "SortAscending": False,
                "NoticeStatuses": ["Active"],
            }
            r = requests.post(
                UNGM_SEARCH_URL, json=body, headers=headers,
                timeout=HTTP_TIMEOUT,
            )
            if not r.ok:
                log(f"UNGM: HTTP {r.status_code} on page {page}")
                break

            soup = BeautifulSoup(r.content, "lxml")
            rows = soup.select("div.tableRow.dataRow")
            if not rows:
                break

            new_on_page = 0
            for row in rows:
                nid = row.get("data-noticeid")
                if not nid or nid in seen_ids:
                    continue
                seen_ids.add(nid)
                new_on_page += 1

                title_el = row.select_one(".resultTitle")
                title = ""
                if title_el:
                    # The cell contains a sustainability tooltip <span> whose
                    # text leaks into the cell's get_text() output. Strip it
                    # by removing all info-tooltip spans first.
                    for tip in title_el.select(".info-tooltip"):
                        tip.decompose()
                    title = title_el.get_text(" ", strip=True)
                if not title:
                    continue

                deadline_el = row.select_one('.resultInfo1.deadline')
                deadline_raw = deadline_el.get_text(" ", strip=True) if deadline_el else ""
                # Format on UNGM is e.g. "29-May-2026 15:00 (GMT 2.00) ..."
                m = re.match(r"(\d{1,2}-\w+-\d{4})", deadline_raw)
                due = parse_uk_date(m.group(1)) if m else ""

                agency_el = row.select_one(".resultAgency")
                agency = agency_el.get_text(" ", strip=True) if agency_el else ""

                ref_el = row.select_one('.resultInfo1[data-description="Reference"]')
                ref = ref_el.get_text(" ", strip=True) if ref_el else ""

                # Beneficiary country, when present, shows up as another
                # cell with data-description="Beneficiary country".
                country_el = row.select_one('[data-description="Beneficiary country"]')
                country = country_el.get_text(" ", strip=True) if country_el else ""
                region = "International (UN)" + (f" - {country}" if country else "")

                url = UNGM_NOTICE_URL.format(id=nid)

                out.append(build_record(
                    project=title,
                    entity=agency or "UN Agency",
                    region=region,
                    due_date=due,
                    reference=ref or nid,
                    source="UNGM",
                    url=url,
                    tags=["UN", "UNGM"] + ([agency] if agency else []),
                ))

            if new_on_page == 0:
                break
            page += 1
            time.sleep(0.5)

    except (requests.RequestException, ValueError) as e:
        log(f"UNGM: error - {e}")

    log(f"UNGM: {len(out)} notices pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 28. Doffin (Norway)
# --------------------------------------------------------------------
# Type: PUBLIC JSON API (free Azure subscription key required)
# Login required: No, but a free API key must be registered at
#   https://dof-notices-prod-api.developer.azure-api.net/
# The key is read from the DOFFIN_API_KEY environment variable, which
# is populated by a GitHub Actions secret. If the key is missing the
# scraper logs a single warning and returns an empty list - the rest
# of the daily run is unaffected.
#
# Above-threshold Norwegian notices already cross-post to TED (which
# we scrape separately). The value-add of Doffin is sub-threshold
# Norwegian work - Sørlige Nordsjø II / Utsira Nord offshore wind,
# Norwegian Environment Agency, Equinor sub-threshold direct contracts.
# Titles are mostly Norwegian; the marine keyword filter still applies.

DOFFIN_API_URL = "https://betaapi.doffin.no/public/v2/notices"
DOFFIN_NOTICE_URL = "https://www.doffin.no/notices/{id}"
DOFFIN_PAGE_SIZE = 100
DOFFIN_MAX_PAGES = 10


def scrape_doffin():
    """Doffin - Norwegian public procurement database.

    Pulls active notices via the public REST API. Above-threshold
    notices duplicate TED entries, so the value-add is sub-threshold
    Norwegian work."""
    log("Doffin: fetching active notices")
    out = []

    api_key = os.environ.get("DOFFIN_API_KEY", "").strip()
    if not api_key:
        log("Doffin: DOFFIN_API_KEY not set - skipping (sign up at "
            "https://dof-notices-prod-api.developer.azure-api.net/ "
            "and add the key as a GitHub Actions secret)")
        return out

    headers = {
        **HEADERS,
        "Accept": "application/json",
        "Ocp-Apim-Subscription-Key": api_key,
    }

    seen = set()
    for page in range(DOFFIN_MAX_PAGES):
        params = {
            "numHitsPerPage": DOFFIN_PAGE_SIZE,
            "page": page,
            "status": "ACTIVE",
            "sortBy": "PUBLICATION_DATE_DESC",
        }
        try:
            r = requests.get(
                DOFFIN_API_URL, params=params, headers=headers,
                timeout=HTTP_TIMEOUT,
            )
        except requests.RequestException as e:
            log(f"Doffin: HTTP error on page {page} - {e}")
            break

        if not r.ok:
            log(f"Doffin: HTTP {r.status_code} on page {page} - {r.text[:200]}")
            break

        try:
            data = r.json()
        except ValueError:
            log(f"Doffin: non-JSON response on page {page}")
            break

        # API returns either {"hits": [...]} or {"results": [...]} depending
        # on version; handle both. Each hit is a notice object.
        hits = data.get("hits") or data.get("results") or data.get("notices") or []
        if not hits:
            break

        new_on_page = 0
        for h in hits:
            nid = (h.get("id") or h.get("doffinId") or
                   h.get("noticeId") or h.get("identifier"))
            if not nid or nid in seen:
                continue
            seen.add(nid)
            new_on_page += 1

            title = (h.get("title") or h.get("heading") or "").strip()
            if not title:
                continue

            buyer = ""
            buyer_obj = h.get("buyer") or h.get("organization") or {}
            if isinstance(buyer_obj, dict):
                buyer = buyer_obj.get("name") or buyer_obj.get("officialName") or ""
            elif isinstance(buyer_obj, str):
                buyer = buyer_obj

            deadline_raw = (h.get("deadline") or h.get("submissionDeadline") or
                            h.get("tenderDeadline") or "")
            due = parse_iso_date(deadline_raw)

            description = (h.get("description") or h.get("shortDescription") or
                           h.get("summary") or "")

            cpv_codes = h.get("cpvCodes") or h.get("cpv") or []
            if isinstance(cpv_codes, list):
                category_code = " ".join(str(c) for c in cpv_codes)
            else:
                category_code = str(cpv_codes)

            url = DOFFIN_NOTICE_URL.format(id=nid)

            out.append(build_record(
                project=title,
                entity=buyer or "Norwegian public buyer",
                region="Norway",
                due_date=due,
                reference=str(nid),
                source="Doffin",
                url=url,
                summary=description,
                category_code=category_code,
                tags=["Norway", "Doffin", "Europe"],
            ))

        if new_on_page == 0:
            break
        time.sleep(0.5)

    log(f"Doffin: {len(out)} notices pulled (pre-filter)")
    return out


# ====================================================================
# Filter, dedup, retention, output
# ====================================================================

def deduplicate(records):
    """Merge by stable id; later wins so freshest copy is kept."""
    seen = {}
    for rec in records:
        seen[rec["id"]] = rec
    return list(seen.values())


def prune_old(records):
    """Drop entries past their due date by more than MAX_DAYS_OLD,
    or scraped more than MAX_DAYS_OLD ago if no due date was found."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_DAYS_OLD)
    kept = []
    for r in records:
        try:
            if r.get("due_date"):
                d = datetime.strptime(r["due_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if d < cutoff:
                    continue
            elif r.get("added"):
                d = datetime.strptime(r["added"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if d < cutoff:
                    continue
        except (ValueError, TypeError):
            pass
        kept.append(r)
    return kept


def load_existing():
    """Load the current rfps.json. Returns dict with rfps and portals."""
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"last_updated": "", "rfps": [], "portals": []}


# All sources our scrapers produce. Used to identify which existing
# records are scraped (overwritten each run) vs manual (preserved).
# IMPORTANT: when adding a new scrape_xxx() function, add its source
# string to this set as well.
SCRAPER_SOURCES = {
    "CanadaBuys", "Find a Tender (UK)", "Contracts Finder (UK)",
    "TED (EU)", "SAM.gov (US)",
    "SPREP", "World Bank", "IMO", "Caribbean Development Bank",
    "BC Bid", "NL Hydro", "NS Procurement", "Nunavut Tenders",
    "BC Ferries", "LNG Canada", "MERX (NL)",
    # New scrapers (2026-05)
    "PCS Scotland", "NBON", "GNWT", "SEAO Quebec",
    "eTenders Ireland", "Sell2Wales",
    # Multilateral development banks (added 2026-05 after Kyla feedback)
    "ADB", "AfDB",
    # UN Global Marketplace (added 2026-05 after AJAX endpoint reverse-engineered)
    "UNGM",
    # Norwegian public procurement (added 2026-05; needs DOFFIN_API_KEY env var)
    "Doffin",
}


def merge_with_existing(scraped):
    """Merge scraped records with manual entries already in rfps.json."""
    existing = load_existing()

    status_overrides = {}
    notes_overrides = {}
    for r in existing.get("rfps", []):
        if r.get("source") not in SCRAPER_SOURCES:
            continue
        if r.get("status") and r["status"] != "open":
            status_overrides[r["id"]] = r["status"]
        if r.get("notes"):
            notes_overrides[r["id"]] = r["notes"]

    for r in scraped:
        if r["id"] in status_overrides:
            r["status"] = status_overrides[r["id"]]
        if r["id"] in notes_overrides and not r.get("notes"):
            r["notes"] = notes_overrides[r["id"]]

    manual = [
        r for r in existing.get("rfps", [])
        if r.get("source") not in SCRAPER_SOURCES
    ]

    return {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "notes": (
            "Auto-generated by Edgewise_rfp_scrape.py. Scraped sources are refreshed each "
            "run; manual entries (source not in SCRAPER_SOURCES) are preserved. "
            "Status values 'watching', 'bidding', 'submitted', 'won', 'lost', "
            "'closed' and any notes are preserved across runs by stable id."
        ),
        "rfps": manual + scraped,
        "portals": existing.get("portals", []),
    }


# ====================================================================
# Main entry point
# ====================================================================

SCRAPERS = [
    scrape_canadabuys,         # Federal Canada (CSV) - highest value
    scrape_find_a_tender,      # UK above-threshold (OCDS JSON)
    scrape_contracts_finder,   # UK below-threshold (OCDS JSON)
    scrape_ted,                # EU above-threshold (TED JSON API)
    scrape_samgov,             # US federal (SAM.gov JSON API)
    scrape_pcs_scotland,       # Crown Estate Scotland, NatureScot, Marine Scotland (RSS)
    scrape_nbon,               # New Brunswick - NB Power, Bay of Fundy (HTML)
    scrape_gnwt,               # NWT - Inuvialuit, Beaufort Sea (HTML via OpenNWT)
    scrape_seao_qc,            # Quebec - Hydro-Québec, MELCCFP (open-data JSON)
    scrape_etenders_ie,        # Ireland - Marine Institute, MARA, NPWS (OCDS feed)
    scrape_sell2wales,         # Wales - NRW, Welsh Govt Marine (RSS)
    scrape_adb,                # Asian Development Bank - Asia-Pacific (HTML)
    scrape_afdb,               # African Development Bank - Africa (HTML)
    scrape_ungm,               # UN Global Marketplace - UN system (POST + HTML fragments)
    scrape_doffin,             # Norway - sub-threshold (REST API; needs DOFFIN_API_KEY)
    scrape_sprep,              # Pacific - SPREP (Playwright headless Chromium)
    scrape_worldbank,          # Global (JSON API)
    scrape_imo,                # Maritime (HTML)
    scrape_caribbean_db,       # Caribbean (HTML)
    scrape_bc_bid,             # BC public sector (HTML)
    scrape_nl_hydro,           # NL Hydro (bidsandtenders)
    scrape_ns_procurement,     # Nova Scotia (HTML)
    scrape_nunavut,            # Nunavut - nunavuttenders.ca (HTML table)
    scrape_bc_ferries,         # BC Ferries (HTML)
    scrape_lng_canada,         # LNG Canada (HTML)
    scrape_merx_nl,            # MERX NL government (HTML)
]


def main():
    log("=" * 70)
    log(f"RFP scrape starting - {len(SCRAPERS)} sources")
    log("=" * 70)

    raw = []
    for fn in SCRAPERS:
        try:
            raw.extend(fn())
        except Exception as e:
            log(f"{fn.__name__}: unhandled error - {e}")

    log(f"Total raw records: {len(raw)}")

    filtered = []
    for rec in raw:
        ok, reason = passes_filter(rec)
        if ok:
            rec["why_fits"] = reason
            if reason and ":" in reason:
                rec["tags"] = list(set(
                    (rec.get("tags") or []) + [reason.split(":", 1)[1].strip().strip('"')]
                ))
            rec.pop("category_code", None)
            filtered.append(rec)

    log(f"Passed filter (marine keywords / CPV codes): {len(filtered)}")

    deduped = deduplicate(filtered)
    log(f"After dedup: {len(deduped)}")

    fresh = prune_old(deduped)
    log(f"After pruning ({MAX_DAYS_OLD}d retention): {len(fresh)}")

    out = merge_with_existing(fresh)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    manual_count = len(out["rfps"]) - len(fresh)
    log(f"Wrote {OUTPUT_FILE}: {len(out['rfps'])} total RFPs "
        f"({manual_count} manual, {len(fresh)} scraped)")
    log("Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"FATAL: {e}")
        sys.exit(1)
