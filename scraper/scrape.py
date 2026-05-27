"""
================================================================
SCRAPE.PY - automated job scraper for the jobs board
================================================================

Purpose
-------
Pulls fresh job postings from multiple UK and Canadian sources,
filters them against a category-tagged keyword dictionary tuned
for Dr Liam T. Pearson-Noseworthy's broadened applicability
(applied health and exercise science, plus data science, health
tech, FE/HE teaching, research management, and research
technician roles), dedupes across sources, and writes the result
to jobs.json for the static site (jobs.html) to render client-side.

Sources
-------
UK:
  - Jobs.ac.uk    (RSS, academic-focused)
  - Bluesky       (@jobsinsportscience.bsky.social feed)

Canada:
  - THEunijobs Canada     (RSS)
  - HigherEdJobs          (RSS)
  - University Affairs    (HTML)

Note: Indeed and LinkedIn HTML scrapers have been removed in
Phase 1 - they were producing low signal and high noise. They
can be reintroduced in Phase 2 if needed.

Filtering and categorisation
----------------------------
Each candidate job passes through passes_filter():
  - CATEGORY_KEYWORDS: dict of category -> keyword list. A job is
    tagged with every category whose keywords match anywhere in
    title/organisation/type. A job with zero matched categories
    is rejected.
  - EXCLUDE_KEYWORDS: any match rejects the job outright. Slimmed
    in Phase 1 to keep medical-clinical roles out but allow
    software/data/health-tech roles in.

Output jobs now include a "categories": [str] field consumed by
the frontend category filter.

Categories (Phase 1)
--------------------
  academic_sport      Sport/exercise/biomech academic posts
  academic_adjacent   Kinesiology, rehab science, gerontology,
                      public health, human movement, motor control
  technician          Lab/research technician, lab manager,
                      research software engineer
  data_science        Data scientist, ML engineer, applied
                      analytics, research software engineer
  health_tech         Digital health, medical device, mHealth,
                      wearable/sensor, NHS digital, clinical
                      software
  fe_he_teaching      Lecturer, tutor, curriculum, IQA/EQA,
                      programme leader, assessor (any subject)
  research_mgmt       Research manager/coordinator, grants
                      officer, ethics, research operations
  industry_applied    S&C coach, performance analyst, sport
                      scientist, consulting biomechanist

Dedup strategy
--------------
Two layers:
  1. make_id(url, title) -> stable 16-char hash, used to merge
     the same posting scraped repeatedly across daily runs.
  2. deduplicate() runs at the end on (title, organisation, source)
     tuples to kill cross-term duplicates within a single run.

Output: jobs.json
-----------------
Shape:
  {
    "last_updated": "2026-05-27T07:00:00Z",
    "jobs": [
      {
        "id":            str,
        "title":         str,
        "organisation":  str,
        "location":      str,
        "type":          str,
        "url":           str,
        "source":        str,
        "date_posted":   str,
        "description":   str,
        "country":       str,
        "categories":    [str]
      },
      ...
    ]
  }

Retention
---------
MAX_DAYS_OLD = 30. prune_old() drops anything older than that on
each run to stop jobs.json growing unbounded. Jobs without a
parseable date_posted are kept (erring on the side of visibility).
"""

import json
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
# CATEGORY-TAGGED KEYWORDS
# ---------------------------------------------------------------------------
# Each category lists the keywords that, when matched in title/org/type,
# tag the job with that category. A job needs at least one category to pass.
# Keywords are matched as case-insensitive substrings, so multi-word phrases
# only fire if the full phrase appears in order. Keep single-word keywords
# (e.g. "lecturer") generic enough to catch variants but specific enough not
# to false-positive on unrelated postings.

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
    # Doctoral + postdoc + fellow roles tagged separately so the frontend
    # can surface them via the "research" facet without forcing them into
    # academic_sport vs academic_adjacent.
    "research_postdoc": [
        "research fellow", "postdoc", "postdoctoral",
        "research associate", "phd studentship", "doctoral researcher",
        "doctoral candidate", "studentship",
    ],
}

# Phase 1 exclude list: slimmed to remove software/data/business analyst
# excludes (those were killing the broadening). Kept clinical-medical
# excludes since Liam doesn't qualify for those.
EXCLUDE_KEYWORDS = [
    # Clinical-medical roles Liam can't credibly apply to
    "clinical fellow", "junior fellow", "medical fellow", "surgical fellow",
    "haematology", "oncology", "cardiology", "anaesthetic", "radiographer",
    "pharmacist", "nurse", "nursing", "midwife",
    "physiotherapist", "occupational therapist",
    "urology", "gynaecology", "neurosurgery", "ophthalmology",
    "pathology", "dentist", "dental", "veterinary",
    "psychiatrist", "psychologist clinical",
    "speech and language", "speech therapist", "speech-language",
    # Non-academic finance roles
    "investment analyst", "financial analyst", "actuarial",
    # Sales/marketing/HR roles that sometimes match "performance"
    "sales executive", "marketing executive", "hr business partner",
    "recruitment consultant",
    # Niche spam terms previously seen in feeds
    "tiktok", "anti-fraud",
]

# Jobs.ac.uk RSS feeds (UK)
# Broadened in Phase 1 to include managerial/research-ops and IT/data feeds.
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

OUTPUT_FILE = Path("scraper/jobs.json")
MAX_DAYS_OLD = 30
MAX_FIELD_LEN = 500


def make_id(url: str, title: str) -> str:
    return hashlib.md5(f"{url}{title}".encode()).hexdigest()[:16]


def clean(text: str) -> str:
    """Sanitise a text field pulled from an external source."""
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
    """Only accept http/https URLs."""
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
    """Return the list of categories matched by this job's text. Order
    follows CATEGORY_KEYWORDS dict insertion order so the frontend can
    sort consistently."""
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


def passes_filter(job: dict) -> bool:
    """A job passes if (a) no exclude keyword matches and (b) at least
    one category keyword matches. Categories are stamped on the job
    in place so the caller doesn't need to re-run categorise()."""
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
    """Existing jobs in jobs.json from before the category migration
    won't have a 'categories' field. Backfill it on load so they
    surface correctly on the frontend without waiting for a fresh
    scrape to displace them."""
    for j in jobs:
        if "categories" not in j or not j["categories"]:
            cats = categorise(j)
            j["categories"] = cats if cats else ["academic_sport"]  # legacy default
    return jobs


def deduplicate(jobs: list) -> list:
    """Remove duplicates based on normalised title + organisation + source.
    Keeps the first occurrence. When merging duplicates, union the
    categories lists so we don't lose any tags."""
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
            # union categories onto the kept copy
            existing_cats = set(seen[key].get("categories", []))
            new_cats = set(j.get("categories", []))
            seen[key]["categories"] = sorted(existing_cats | new_cats)
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
# University Affairs - HTML scrape (Canada)
# ---------------------------------------------------------------------------

def scrape_university_affairs() -> list:
    jobs = []
    url = "https://www.universityaffairs.ca/career-centre/job-board/"
    print(f"  University Affairs HTML scrape...")
    r = get(url)
    if not r:
        return jobs
    try:
        soup = BeautifulSoup(r.text, "html.parser")
        listings = soup.select("article.job, li.job-listing, div.job-item, .views-row")
        if not listings:
            listings = soup.select("h2 a, h3 a, .job-title a")
        for item in listings[:40]:
            try:
                title_el = item.select_one("h2, h3, .job-title, a") if hasattr(item, 'select_one') else item
                if not title_el:
                    continue
                title = clean(title_el.get_text())
                if not title or len(title) < 5:
                    continue
                link_el = item.select_one("a") if hasattr(item, 'select_one') else item
                href = ""
                if link_el and link_el.get("href"):
                    href = link_el["href"]
                    if href.startswith("/"):
                        href = "https://www.universityaffairs.ca" + href
                href = clean_url(href)
                org_el = item.select_one(".institution, .employer, .university, .org")
                org = clean(org_el.get_text()) if org_el else ""
                jobs.append({
                    "id": make_id(href or title, title),
                    "title": title,
                    "organisation": org,
                    "location": "Canada",
                    "country": "Canada",
                    "source": "University Affairs",
                    "url": href,
                    "date_posted": datetime.date.today().isoformat(),
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
    print("=== JobScan scraper starting (Phase 1: category-tagged) ===")
    existing = load_existing()
    # Backfill categories on existing jobs so post-migration runs don't drop
    # them from the frontend until they age out naturally.
    existing["jobs"] = backfill_categories(existing.get("jobs", []))
    existing_ids = {j["id"] for j in existing["jobs"]}
    new_jobs = []

    print("  Running Jobs.ac.uk RSS scraper...")
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

    print("  Running Bluesky scraper...")
    try:
        bsky_results = scrape_bluesky()
        added = 0
        for j in bsky_results:
            if j["id"] not in existing_ids:
                # Bluesky posts bypass the category filter but still get
                # categorised so the frontend can place them sensibly.
                cats = categorise(j)
                j["categories"] = cats if cats else ["industry_applied"]
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
