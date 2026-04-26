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

    https://liamtp-n.github.io/Consultation-Services/rfps.html

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
       UK Contracts Finder (JSON), World Bank (RSS).

  2. PUBLIC HTML LISTINGS (medium case)
       The portal shows its tenders on a public web page. No
       login required to see basic info (title, due date, link).
       We download the HTML and parse it with BeautifulSoup.
       Examples: SPREP, BC Bid public portal, Government of
       Nunavut RFTP, IMO open tenders, NL Hydro on bidsandtenders.
       Even most procurement portals that REQUIRE login to
       SUBMIT a bid will let you VIEW the basic tender info
       publicly. We grab whatever's public.

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
6. Test locally with `python rfp_scrape.py` before pushing.

TUNING WHAT GETS THROUGH THE FILTER
-----------------------------------
There are three lists you can edit at the top of this file:

  MARINE_KEYWORDS    Strings to look for in titles/descriptions.
                     If ANY match, the tender is kept. Add
                     keywords that would describe Edgewise work.

  CPV_CODES          Procurement category codes from your
                     CanadaBuys tracker (Wildlife studies,
                     Environmental management, etc.). Direct match
                     on the code field.

  EXCLUDE_KEYWORDS   Hard rejects. If ANY of these match the
                     title or description, the tender is dropped
                     even if it matched a keyword. Use this to
                     kill obvious irrelevants (catering, IT
                     support, cleaning supplies).

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
Configured in .github/workflows/rfp_scrape.yml to run daily at
10:30 UTC. That's:
  - 08:00 NDT (Newfoundland Daylight Time) Mar-Nov
  - 07:00 NST (Newfoundland Standard Time) Nov-Mar
GitHub Actions cron is fixed to UTC and does not handle DST.
Adjust the cron in the YAML if you'd rather a different time.

To run manually (locally on your laptop):
    python rfp_scrape.py

Dependencies (pip install ...):
    requests, beautifulsoup4, lxml

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
    Tighten MARINE_KEYWORDS (remove broad ones like "fisheries"
    or "biodiversity") and/or expand EXCLUDE_KEYWORDS.

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
# All standard library or trivial deps. Anything fancier is a flag
# that we should ask whether it's worth the install footprint.

import csv             # CanadaBuys CSV parsing
import hashlib         # Stable id hashing
import io              # In-memory CSV buffer
import json            # Output writing, OCDS API parsing
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

# Some portals (notably SPREP, IMO, parts of GoC) return 403 to the
# default python-requests UA. Send a normal Chrome UA to be polite.
# This is not deception - we identify as a desktop browser, which is
# what we are functionally (a one-shot HTTP client reading public
# pages). No login, no rate-limit-busting, no scraping behind auth.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
}


# --------------------------------------------------------------------
# Filter lists - EDIT THESE TO TUNE WHAT GETS THROUGH
# --------------------------------------------------------------------

# Marine / environmental consultancy keywords. At least one must match
# the title, description, or buyer name (case-insensitive substring).
# Adding a keyword here makes the filter MORE PERMISSIVE (more matches).
MARINE_KEYWORDS = [
    # ---- Edgewise core services ----
    "marine mammal", "mmo", "passive acoustic", "pam ",
    "seabird", "sea bird",

    # ---- Surveys and assessments ----
    "marine survey", "underwater survey", "benthic survey",
    "environmental impact", "eia", "environmental assessment",
    "oceanographic", "baseline study", "marine baseline",

    # ---- Sectors Edgewise targets ----
    "offshore wind", "marine renewable", "tidal energy", "wave energy",
    "subsea", "ocean energy",

    # ---- Broader environmental ----
    "fisheries", "marine conservation", "biodiversity",
    "marine ecology", "coastal monitoring", "marine monitoring",
    "acoustic monitoring", "bioacoustic",
    "wildlife monitoring", "wildlife survey",
    "habitat assessment", "habitat survey",

    # ---- Region focus (catches geography-tagged tenders) ----
    "atlantic canada", "arctic", "nunavut", "newfoundland",
    "north sea", "celtic sea", "labrador",
]

# CanadaBuys procurement category codes Edgewise specifically tracks.
# Pulled from your tracker spreadsheet (Procurement Sites Tracker > Canada Buys).
# These are UNSPSC codes used by federal Canadian procurement to classify
# tender opportunities. A tender tagged with one of these codes gets
# kept regardless of keyword match.
#
# 70101602 = Wildlife studies
# 70100000 = Forestry, fisheries, wildlife management services
# 81171500 = Information management technology
# 77101500 = Environmental management
CPV_CODES = [
    "70101602",
    "70100000",
    "81171500",
    "77101500",
]

# Hard rejects. If ANY of these match the title or description, the
# tender is dropped even if it matched a keyword. Use this to kill
# noise. Adding a keyword here makes the filter MORE STRICT.
EXCLUDE_KEYWORDS = [
    "janitorial", "cleaning service", "catering", "food service",
    "stationery", "office supplies", "printer toner",
    "uniform", "laundry",
    "pest control", "snow removal", "landscaping",
    "it support", "software licence", "software license",
    "vehicle rental", "fuel supply",
    "translation service", "interpreter",
    "medical supplies", "pharmaceutical",
]


# --------------------------------------------------------------------
# Generic helpers used by every scraper
# --------------------------------------------------------------------

def log(msg):
    """Print a timestamped line. Visible in GitHub Actions run logs."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def make_id(*parts):
    """Stable 16-char md5 hash. Used so the same tender re-scraped
    tomorrow gets the same id, which lets us preserve user-edited
    status fields across runs."""
    raw = "|".join(str(p or "") for p in parts).lower().strip()
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def truncate(text, n=MAX_FIELD_LEN):
    """Strip whitespace and cap length. Returns empty string for None."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", str(text)).strip()
    if len(text) <= n:
        return text
    return text[: n - 1].rstrip() + "\u2026"   # unicode ellipsis


def parse_iso_date(s):
    """Accept any ISO-ish string, return YYYY-MM-DD or empty.
    Handles '2026-05-11', '2026-05-11T23:59:59Z', '2026-05-11T...',
    and dies gracefully on garbage."""
    if not s:
        return ""
    try:
        s = re.sub(r"[Tt].*$", "", str(s).strip())
        return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return ""


def parse_uk_date(s):
    """Parse '11 May 2026' or '11/05/2026'. Falls back to ISO."""
    if not s:
        return ""
    s = s.strip()
    for fmt in ("%d %B %Y", "%d %b %Y", "%d/%m/%Y", "%d-%m-%Y"):
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
    """Return matched CPV code (str) or None. Direct substring."""
    if not text:
        return None
    t = str(text)
    for code in CPV_CODES:
        if code in t:
            return code
    return None


def is_excluded(text):
    """True if any exclude keyword matches. Used to reject noise."""
    if not text:
        return False
    t = text.lower()
    return any(kw in t for kw in EXCLUDE_KEYWORDS)


def passes_filter(rec):
    """The single decision point: should this record be kept?
    Returns (bool, reason_string). reason_string is shown in why_fits."""
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
        return True, f"keyword: {kw}"
    code = matches_cpv(rec.get("reference", "") + " " + rec.get("category_code", ""))
    if code:
        return True, f"CPV code: {code}"
    return False, None


def build_record(**kwargs):
    """Construct a record with all fields defaulted. Use this to create
    new records inside scrape_xxx() functions so we never miss a field."""
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
        # category_code is internal-only; passes_filter uses it then we strip it.
        "category_code": kwargs.get("category_code", ""),
    }


def safe_get(url, **kwargs):
    """Wrapper around requests.get that respects HEADERS and HTTP_TIMEOUT
    and doesn't raise on bad responses - returns None instead. Keeps
    one bad source from crashing the whole run."""
    try:
        kwargs.setdefault("headers", HEADERS)
        kwargs.setdefault("timeout", HTTP_TIMEOUT)
        r = requests.get(url, **kwargs)
        r.raise_for_status()
        return r
    except requests.RequestException as e:
        log(f"  HTTP error on {url}: {e}")
        return None


# ====================================================================
# SCRAPERS - one function per source
# ====================================================================
# Every scraper follows the same contract:
#   - Returns a list of records built via build_record()
#   - Logs progress via log()
#   - Catches its own errors so it doesn't crash the run
#   - Has its source URL as a constant at the top
#
# When you add a new scraper, copy the structure of the simplest one
# (scrape_imo or scrape_caribbean_db) and adapt.
# ====================================================================


# --------------------------------------------------------------------
# 1. CanadaBuys - federal Canadian government tenders
# --------------------------------------------------------------------
# Type: OPEN-DATA FEED (CSV)
# Refresh: PSPC updates the CSV every 2 hours, 06:15-22:15 ET.
# Login required: No.
# Coverage: All federal departments and Crown corporations.
#
# This is the highest-value single source for Edgewise. It includes
# DFO, NRCan, ECCC, DND, and contains tenders that aren't published
# anywhere else.

CANADABUYS_CSV = (
    "https://canadabuys.canada.ca/sites/default/files/opendata/"
    "open-bid-notices-canadabuys.csv"
)


def scrape_canadabuys():
    log("CanadaBuys: fetching open tender notices CSV")
    out = []
    r = safe_get(CANADABUYS_CSV)
    if not r:
        return out

    # CSV uses combined English/French columns post-March-2026.
    text = r.content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    count = 0
    for row in reader:
        # Field names in the new schema. Use .get() for resilience
        # because PSPC has changed the schema before and may again.
        title = (row.get("title-titre-eng") or row.get("title-titre") or "")
        desc = (row.get("tenderDescription-descriptionAppelOffres-eng")
                or row.get("noticeDescription-descriptionAvis-eng") or "")
        buyer = (row.get("contractingEntityName-nomEntiteContractante-eng")
                 or row.get("buyerName") or "")
        ref = (row.get("referenceNumber-numeroReference")
               or row.get("solicitationNumber-numeroSollicitation") or "")
        url = (row.get("noticeURL-URLavis-eng")
               or row.get("tenderNoticeURL-URLavisAppelOffres-eng") or "")
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
# Refresh: Real-time as new notices are published.
# Login required: No.
# Coverage: All UK central government and public sector procurement
#           above the threshold (Procurement Act 2023).

FIND_A_TENDER_API = "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages"


def scrape_find_a_tender():
    log("Find a Tender (UK): fetching OCDS releases (last 7d)")
    return _ocds_scrape(
        FIND_A_TENDER_API, source_name="Find a Tender (UK)",
        url_template="https://www.find-tender.service.gov.uk/Notice/{id}",
    )


# --------------------------------------------------------------------
# 3. UK Contracts Finder - UK below-threshold contracts
# --------------------------------------------------------------------
# Type: OPEN-DATA FEED (OCDS JSON API)
# Refresh: Real-time.
# Login required: No.

CONTRACTS_FINDER_API = (
    "https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search"
)


def scrape_contracts_finder():
    log("Contracts Finder (UK): fetching OCDS releases (last 7d)")
    return _ocds_scrape(
        CONTRACTS_FINDER_API, source_name="Contracts Finder (UK)",
        url_template="https://www.contractsfinder.service.gov.uk/Notice/{id}",
    )


def _ocds_scrape(api_url, source_name, url_template):
    """Shared OCDS parser used by both UK feeds. The two services
    publish identical OCDS shapes - the only differences are the URL
    of the human-facing notice page and how many parameters they
    accept."""
    out = []
    since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00")
    params = {"updatedFrom": since, "limit": 100, "stages": "tender"}
    cursor = None
    pages = 0

    try:
        while pages < 10:    # Hard cap so a buggy API can't loop forever.
            if cursor:
                params["cursor"] = cursor
            r = safe_get(api_url, params=params)
            if not r:
                break
            pkg = r.json()
            for rel in pkg.get("releases", []):
                rec = _ft_release_to_record(rel, source_name, url_template)
                if rec:
                    out.append(rec)
            # Walk the next-cursor pagination.
            nxt = (pkg.get("links", {}) or {}).get("next")
            if not nxt:
                break
            m = re.search(r"cursor=([^&]+)", nxt)
            if not m:
                break
            cursor = m.group(1)
            pages += 1
            time.sleep(0.5)   # polite delay
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

    # Buyer can be in `parties[].roles=[buyer]` OR `buyer.name`.
    buyer = ""
    for p in (rel.get("parties") or []):
        if "buyer" in (p.get("roles") or []):
            buyer = p.get("name", "")
            break
    if not buyer:
        buyer = (rel.get("buyer") or {}).get("name", "")

    closing = (tender.get("tenderPeriod") or {}).get("endDate", "")

    # Budget formatting if value is provided.
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
# 4. SPREP - Pacific environmental tenders
# --------------------------------------------------------------------
# Type: PUBLIC HTML LISTINGS
# Login required: No.
# Coverage: Environmental tenders in Pacific Island countries.
#           Includes the Palau seabird tender from April 2026.

SPREP_TENDERS_URL = "https://www.sprep.org/tenders"


def scrape_sprep():
    log("SPREP: scraping tenders page")
    out = []
    r = safe_get(SPREP_TENDERS_URL)
    if not r:
        return out

    soup = BeautifulSoup(r.content, "lxml")
    seen_urls = set()
    # SPREP renders tenders as a list of links pointing to either
    # /sites/default/files/documents/tenders/ PDFs or /tender/<slug>
    # nodes. We pick up either by URL pattern.
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/tender" not in href.lower() and "RFT_" not in href:
            continue
        text = a.get_text(strip=True)
        if not text or len(text) < 10:
            continue
        url = urljoin(SPREP_TENDERS_URL, href)
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Extract a closing date from the parent block, if present.
        parent_text = a.parent.get_text(" ", strip=True) if a.parent else ""
        m = re.search(r"clos\w*[^\d]+(\d{1,2}\s+\w+\s+\d{4})", parent_text, re.I)
        due = parse_uk_date(m.group(1)) if m else ""

        # Extract a reference number (RFT 2026/PBS/001 style).
        ref_match = re.search(
            r"RFT[_\s/-]*(\d{4}[/_-][A-Z0-9]+[/_-]\d+)",
            text + " " + parent_text, re.I,
        )
        ref = ref_match.group(0) if ref_match else ""

        out.append(build_record(
            project=text, entity="SPREP (Pacific Regional Environment Programme)",
            region="Pacific", due_date=due, reference=ref,
            source="SPREP", url=url, summary=parent_text,
            tags=["Pacific", "SPREP"],
        ))

    log(f"SPREP: {len(out)} tenders pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 5. World Bank - Procurement Notices RSS
# --------------------------------------------------------------------
# Type: OPEN-DATA FEED (RSS XML)
# Login required: No.
# Coverage: Global. Most relevant for Pacific/Caribbean/African projects
#           that touch marine environmental work.

WORLDBANK_RSS = (
    "https://projects.worldbank.org/en/projects-operations/procurement/notices.rss"
)


def scrape_worldbank():
    log("World Bank: fetching procurement RSS")
    out = []
    r = safe_get(WORLDBANK_RSS)
    if not r:
        return out

    soup = BeautifulSoup(r.content, "lxml-xml")
    for item in soup.find_all("item"):
        title = (item.title.text if item.title else "").strip()
        link = (item.link.text if item.link else "").strip()
        desc = (item.description.text if item.description else "").strip()
        pub = (item.pubDate.text if item.pubDate else "").strip()
        if not title:
            continue

        # Country usually appears as a prefix: "Senegal: Project XYZ"
        region = "International"
        m = re.match(r"^([A-Z][A-Za-z\s]+):", title)
        if m:
            region = m.group(1).strip()

        out.append(build_record(
            project=title, entity="World Bank", region=region,
            source="World Bank", url=link, summary=desc,
            notes=f"Published: {pub}" if pub else "",
            tags=["World Bank"],
        ))

    log(f"World Bank: {len(out)} notices pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 6. International Maritime Organisation (IMO)
# --------------------------------------------------------------------
# Type: PUBLIC HTML LISTINGS
# Login required: No.
# Coverage: Maritime/shipping tenders. Highly relevant for marine acoustic
#           and underwater work.

IMO_TENDERS_URL = "https://www.imo.org/en/About/Procurement/Pages/Open-Tenders.aspx"


def scrape_imo():
    log("IMO: scraping open tenders page")
    out = []
    r = safe_get(IMO_TENDERS_URL)
    if not r:
        return out

    soup = BeautifulSoup(r.content, "lxml")
    seen = set()
    # IMO lists tenders in tables with links; structure is fragile.
    # We collect all anchor tags whose text mentions "tender", "RFP",
    # "consultancy", or "services" and dedupe.
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
# 7. Caribbean Development Bank
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
# 8. BC Bid - British Columbia public sector procurement
# --------------------------------------------------------------------
# Type: PUBLIC HTML LISTINGS (browse-without-login)
# Login required: No (to view; yes to bid).
# Coverage: BC Hydro, BC Ferries, all BC ministries and Crown corps.
#           This single source covers BC Hydro and many other tracker
#           portals that delegate posting to BC Bid.
#
# Note: BC Bid is a SaaS (Ivalua). The browse URL is paginated. We
# pull the first page only - sufficient since the filter narrows
# results dramatically anyway.

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
# 9. NL Hydro - bidsandtenders.ca platform
# --------------------------------------------------------------------
# Type: PUBLIC HTML LISTINGS (bidsandtenders.ca platform)
# Login required: No (to view); yes to bid.

NL_HYDRO_URL = "https://nlhydro.bidsandtenders.ca/Module/Tenders/en"


def scrape_nl_hydro():
    return _scrape_bidsandtenders(
        NL_HYDRO_URL, "NL Hydro",
        "Newfoundland and Labrador Hydro", "Canada (NL)",
    )


# --------------------------------------------------------------------
# 10. Government of Yukon - bidsandtenders.ca platform
# --------------------------------------------------------------------

YUKON_BIDS_URL = "https://yukon.bidsandtenders.ca/Module/Tenders/en"


def scrape_yukon():
    return _scrape_bidsandtenders(
        YUKON_BIDS_URL, "Yukon",
        "Government of Yukon", "Canada (YT)",
    )


def _scrape_bidsandtenders(url, source_name, entity, region):
    """Generic bidsandtenders.ca scraper. The platform serves all
    its clients (NL Hydro, Yukon, hundreds of municipalities) on
    the same template, so this works for any of them."""
    log(f"{source_name}: scraping {url}")
    out = []
    r = safe_get(url)
    if not r:
        return out

    soup = BeautifulSoup(r.content, "lxml")
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "Tender/Detail" not in href and "/Module/Tenders" not in href:
            continue
        text = a.get_text(strip=True)
        if not text or len(text) < 10:
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
# 11. Government of Nova Scotia - Procurement Portal
# --------------------------------------------------------------------
# Type: PUBLIC HTML LISTINGS

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
# 12. Government of Nunavut - RFTP
# --------------------------------------------------------------------
# Type: PUBLIC HTML LISTINGS
# Note: Nunavut tenders are gold for Edgewise (Arctic focus).

NUNAVUT_URL = "https://www.gov.nu.ca/finance/information/government-nunavut-rftp"


def scrape_nunavut():
    log("Nunavut RFTP: scraping public notices")
    out = []
    r = safe_get(NUNAVUT_URL)
    if not r:
        return out

    soup = BeautifulSoup(r.content, "lxml")
    seen = set()
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        if not text or len(text) < 10:
            continue
        if not re.search(r"\b(RFT|RFP|RFQ|tender|proposal)\b",
                         text + " " + href, re.I):
            continue
        full = urljoin(NUNAVUT_URL, href)
        if full in seen:
            continue
        seen.add(full)
        out.append(build_record(
            project=text, entity="Government of Nunavut",
            region="Canada (NU)", source="Nunavut RFTP",
            url=full, tags=["Nunavut", "Arctic", "Canada"],
        ))

    log(f"Nunavut RFTP: {len(out)} entries pulled (pre-filter)")
    return out


# --------------------------------------------------------------------
# 13. BC Ferries - Procurement
# --------------------------------------------------------------------
# Type: PUBLIC HTML LISTINGS (some opportunities posted on BC Bid,
# some on their own page)

BC_FERRIES_URL = "https://www.bcferries.com/about/procurement"


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
# 14. LNG Canada - Contracting & Procurement
# --------------------------------------------------------------------
# Type: PUBLIC HTML LISTINGS
# Note: Marine environmental work around the LNG terminal in Kitimat.

LNG_CANADA_URL = "https://www.lngcanada.ca/our-business/contracting-procurement/"


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
# 15. MERX - Government of NL solicitations
# --------------------------------------------------------------------
# Type: PUBLIC HTML LISTINGS (basic info before paywall)
# Login required: Yes to download bid documents; No to see titles
# and headline info on the listing page.

MERX_NL_URL = "https://www.merx.com/govnl/solicitations/open-bids?pageNumber=1"


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
        if "/solicitations/" not in href and "/solicitation-detail/" not in href:
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
# string to this set as well, otherwise its entries won't get refreshed.
SCRAPER_SOURCES = {
    "CanadaBuys", "Find a Tender (UK)", "Contracts Finder (UK)",
    "SPREP", "World Bank", "IMO", "Caribbean Development Bank",
    "BC Bid", "NL Hydro", "Yukon", "NS Procurement", "Nunavut RFTP",
    "BC Ferries", "LNG Canada", "MERX (NL)",
}


def merge_with_existing(scraped):
    """Merge scraped records with manual entries already in rfps.json.

    Behaviour:
      - Scraped entries (source in SCRAPER_SOURCES) are replaced
        wholesale each run, EXCEPT for status overrides and notes
        the user has added (matched by stable id).
      - Manual entries (source NOT in SCRAPER_SOURCES) are kept
        whole - this is how Gemini-found entries or hand-added
        tenders survive between scrapes.
      - The portals array is preserved untouched.
    """
    existing = load_existing()

    # Capture user-edited fields from existing scraped entries.
    status_overrides = {}
    notes_overrides = {}
    for r in existing.get("rfps", []):
        if r.get("source") not in SCRAPER_SOURCES:
            continue
        if r.get("status") and r["status"] != "open":
            status_overrides[r["id"]] = r["status"]
        if r.get("notes"):
            notes_overrides[r["id"]] = r["notes"]

    # Apply overrides to fresh scrape.
    for r in scraped:
        if r["id"] in status_overrides:
            r["status"] = status_overrides[r["id"]]
        if r["id"] in notes_overrides and not r.get("notes"):
            r["notes"] = notes_overrides[r["id"]]

    # Keep manual entries.
    manual = [
        r for r in existing.get("rfps", [])
        if r.get("source") not in SCRAPER_SOURCES
    ]

    return {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "notes": (
            "Auto-generated by rfp_scrape.py. Scraped sources are refreshed each "
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

# List of all active scrapers. To disable one temporarily, comment out
# its line. To add a new scraper, add the function reference here AND
# add its source string to SCRAPER_SOURCES above.
SCRAPERS = [
    scrape_canadabuys,         # Federal Canada (CSV) - highest value
    scrape_find_a_tender,      # UK above-threshold (JSON API)
    scrape_contracts_finder,   # UK below-threshold (JSON API)
    scrape_sprep,              # Pacific (HTML)
    scrape_worldbank,          # Global (RSS)
    scrape_imo,                # Maritime (HTML)
    scrape_caribbean_db,       # Caribbean (HTML)
    scrape_bc_bid,             # BC public sector (HTML)
    scrape_nl_hydro,           # NL Hydro (b&t platform)
    scrape_yukon,              # Yukon (b&t platform)
    scrape_ns_procurement,     # Nova Scotia (HTML)
    scrape_nunavut,            # Nunavut Arctic (HTML)
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
            # One source failing must NOT abort the whole run.
            log(f"{fn.__name__}: unhandled error - {e}")

    log(f"Total raw records: {len(raw)}")

    # Apply marine/CPV filter.
    filtered = []
    for rec in raw:
        ok, reason = passes_filter(rec)
        if ok:
            rec["why_fits"] = reason
            if reason and ":" in reason:
                rec["tags"] = list(set(
                    (rec.get("tags") or []) + [reason.split(":", 1)[1].strip()]
                ))
            rec.pop("category_code", None)   # internal-only field
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
