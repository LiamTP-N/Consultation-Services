"""
================================================================
SCRAPE.PY - automated job scraper for the jobs board (Phase 2)
================================================================

Purpose
-------
Pulls fresh job postings from multiple UK and Canadian sources,
tags each with applicable categories from a CV-anchored dictionary,
computes a per-job fit score weighted to Liam's profile, dedupes
across sources, and writes the result to jobs.json for the static
site (jobs.html) to render client-side.

Sources (Phase 2)
-----------------
UK:
  - Jobs.ac.uk RSS (12 feeds: sport, lab/tech, health/medical,
    biology, nutrition, computer science, library/info services,
    professional/managerial, research related, PhDs, engineering,
    mathematics/statistics)
  - Adzuna API UK (opt-in, set ADZUNA_APP_ID + ADZUNA_APP_KEY env vars)
  - Bluesky (@jobsinsportscience.bsky.social feed)

Canada:
  - THEunijobs Canada RSS
  - HigherEdJobs RSS (2 category feeds)
  - University Affairs HTML scrape (proper URL: /search-jobs/)
  - Adzuna API Canada (opt-in, same env vars as UK)

Adzuna integration
------------------
Adzuna offers a free-tier REST API covering UK + Canada with 
generous rate limits. Activate by setting two GitLab CI variables:
  ADZUNA_APP_ID, ADZUNA_APP_KEY (register at developer.adzuna.com)
Without them the Adzuna step is silently skipped.

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
# CATEGORY-TAGGED KEYWORDS (Phase 2)
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS = {
    "academic_sport": [
        "sport science", "sports science", "exercise science",
        "exercise physiology", "sport and exercise", "sports and exercise",
        "biomechanics", "biomechanist", "strength and conditioning",
        "sport psychology", "sports psychology", "sport coaching",
        "sport nutrition", "sports nutrition",
    ],
    "academic_adjacent": [
        "kinesiology", "human kinetics", "human movement", "movement science",
        "motor control", "motor learning", "skill acquisition",
        "rehabilitation science", "rehabilitation research", "physical therapy research",
        "gerontology", "ageing research", "aging research", "healthy ageing", "healthy aging",
        "public health", "population health", "epidemiology",
        "physical activity", "physical education",
        "musculoskeletal research", "neuromuscular",
    ],
    "technician": [
        "lab technician", "laboratory technician", "research technician",
        "senior technician", "technical specialist", "technical officer",
        "lab manager", "laboratory manager", "facility manager",
        "research software engineer", "rse",
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
        "wearable", "wearables", "inertial sensor", "imu",
        "clinical software", "clinical informatics", "nhs digital",
        "health informatics", "digital therapeutic",
        "computer vision health", "pose estimation",
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
    "academic_adjacent": 18,
    "research_postdoc":  15,
    "technician":        20,  # current role; transferable anywhere
    "data_science":      22,  # 2.2M-record ML pipeline + Python/R
    "health_tech":       22,  # RBE app, MediaPipe, NHS pathway
    "fe_he_teaching":    15,
    "research_mgmt":     12,
    "industry_applied":  10,
}

# Cap to keep fit_score visually clean (0-100 scale)
FIT_SCORE_CAP = 100

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

# Jobs.ac.uk RSS feeds (UK) - Phase 2: expanded to 12 feeds
JOBSAC_RSS_FEEDS = [
    ("https://www.jobs.ac.uk/jobs/sport-and-leisure/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/laboratory-clinical-and-technician/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/health-and-medical/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/biological-sciences/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/nutrition-and-food-science/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/computer-sciences/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/information-and-library-services/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/professional-or-managerial/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/research-related/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/phd/?format=rss", "Jobs.ac.uk"),
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

# Adzuna API: country code, country label, query list
# Queries chosen to span Liam's CV categories without burning quota
ADZUNA_QUERIES = [
    "sport science",
    "biomechanics",
    "research software engineer",
    "data scientist health",
    "digital health",
    "kinesiology",
    "lecturer exercise",
    "research technician",
]

OUTPUT_FILE = Path("scraper/jobs.json")
MAX_DAYS_OLD = 30
MAX_FIELD_LEN = 500


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
    matched = []
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
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
    text = (
        f"{job.get('title', '')} "
        f"{job.get('organisation', '')} "
        f"{job.get('type', '')} "
        f"{job.get('description', '')}"
    ).lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw in text:
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
                    continue
            except Exception:
                pass
        kept.append(j)
    return kept


def backfill_categories(jobs: list) -> list:
    """Backfill categories AND fit_score on legacy entries."""
    for j in jobs:
        if "categories" not in j or not j["categories"]:
            cats = categorise(j)
            j["categories"] = cats if cats else ["academic_sport"]
        if "fit_score" not in j:
            j["fit_score"] = compute_fit_score(j["categories"])
    return jobs


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
                    href = link.get_text().strip() if link else ""
                    if not href and link:
                        href = link.next_sibling
                    href = clean_url(href)
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
                    href = link.get_text().strip() if link else ""
                    if not href and link:
                        href = link.next_sibling
                    href = clean_url(href)
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
    """Phase 2 fix: the previous URL (/career-centre/job-board/) no longer
    exists. The live jobs page is /search-jobs/. Parse the listing markup
    which is a flat sequence of H2 anchors followed by university + date."""
    jobs = []
    url = "https://www.universityaffairs.ca/search-jobs/"
    print(f"  University Affairs HTML scrape...")
    r = get(url)
    if not r:
        return jobs
    try:
        soup = BeautifulSoup(r.text, "html.parser")
        # Each job is an <h2> with <a> link inside, followed by university name
        # and a "Posting date YYYY-MM-DD" string somewhere nearby.
        for h2 in soup.find_all("h2")[:80]:
            try:
                a = h2.find("a")
                if not a or not a.get("href"):
                    continue
                href = a["href"]
                if "job_id=" not in href:
                    continue  # not a job link
                if href.startswith("/"):
                    href = "https://universityaffairs.ca" + href
                href = clean_url(href)
                title = clean(a.get_text())
                if not title or len(title) < 5:
                    continue
                # Walk forward to find org + posting date
                org = ""
                date_str = datetime.date.today().isoformat()
                sibling = h2.next_sibling
                walked = 0
                while sibling is not None and walked < 6:
                    text = ""
                    if hasattr(sibling, "get_text"):
                        text = sibling.get_text(" ", strip=True)
                    elif isinstance(sibling, str):
                        text = sibling.strip()
                    if text:
                        # University name typically the first non-empty
                        # non-"Location"/"Posting" line
                        if not org and "Location" not in text and "Posting" not in text:
                            org = clean(text[:200])
                        m = re.search(r"Posting date\s*(\d{4}-\d{2}-\d{2})", text)
                        if m:
                            date_str = m.group(1)
                            break
                    sibling = sibling.next_sibling
                    walked += 1
                jobs.append({
                    "id": make_id(href or title, title),
                    "title": title,
                    "organisation": org,
                    "location": "Canada",
                    "country": "Canada",
                    "source": "University Affairs",
                    "url": href,
                    "date_posted": date_str,
                    "closing_date": "",
                    "type": "",
                    "description": "",
                })
            except Exception as e:
                print(f"    item parse error: {e}")
        print(f"    found {len(jobs)} listings from University Affairs")
    except Exception as e:
        print(f"  ERROR University Affairs: {e}")
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
    jobs = []
    print(f"  Adzuna {country_label} ({country_code}): {len(ADZUNA_QUERIES)} queries")
    for query in ADZUNA_QUERIES:
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
    print("=== JobScan scraper starting (Phase 2: fit-score + Adzuna + UA fix) ===")
    existing = load_existing()
    existing["jobs"] = backfill_categories(existing.get("jobs", []))
    existing_ids = {j["id"] for j in existing["jobs"]}
    new_jobs = []

    print("  Running Jobs.ac.uk RSS scraper (12 feeds)...")
    try:
        results = scrape_jobsac_rss()
        added = 0
        for j in results:
            if j["id"] not in existing_ids and passes_filter(j):
                new_jobs.append(j)
                existing_ids.add(j["id"])
                added += 1
        print(f"    +{added} new from Jobs.ac.uk RSS")
    except Exception as e:
        print(f"  ERROR jobs.ac.uk RSS: {e}")

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

    print("  Running University Affairs scraper...")
    try:
        results = scrape_university_affairs()
        added = 0
        for j in results:
            if j["id"] not in existing_ids and passes_filter(j):
                new_jobs.append(j)
                existing_ids.add(j["id"])
                added += 1
        print(f"    +{added} new from University Affairs")
    except Exception as e:
        print(f"  ERROR University Affairs: {e}")

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
