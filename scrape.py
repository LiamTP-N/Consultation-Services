"""
================================================================
SCRAPE.PY - automated job scraper for the consultancy jobs board
================================================================

Purpose
-------
Pulls fresh job postings from multiple UK and Canadian sources,
filters them against a keyword list tuned for applied health and
exercise science, dedupes across sources, and writes the result
to jobs.json for the static site (jobs.html) to render client-side.

Sources
-------
UK:
  - Indeed UK     (RSS per search term)
  - Jobs.ac.uk    (RSS, academic-focused)
  - LinkedIn UK   (HTML scrape per search term)
  - Bluesky       (@jobsinsportscience.bsky.social feed)

Canada:
  - Indeed Canada         (RSS)
  - LinkedIn Canada       (HTML)
  - THEunijobs Canada     (RSS)
  - HigherEdJobs          (RSS)
  - University Affairs    (HTML)

Search terms live in SEARCH_TERMS_UK / SEARCH_TERMS_CA near the
top of the file - edit there to tune what's pulled.

Filtering
---------
Each candidate job passes through passes_filter():
  - REQUIRED_KEYWORDS: at least one must match title/org/type
  - EXCLUDE_KEYWORDS:  any match rejects the job
This is coarse by design - the jobs.html frontend can refilter
interactively.

Dedup strategy
--------------
Two layers:
  1. make_id(url, title) -> stable 16-char hash, used to merge
     the same posting scraped repeatedly across daily runs.
  2. deduplicate() runs at the end on (title, organisation, source)
     tuples to kill cross-term duplicates within a single run
     (e.g. the same Indeed job surfaced by two search terms).
LinkedIn URLs are normalised first (query string stripped) so
tracking params don't defeat the URL-based id.

Output: jobs.json
-----------------
Shape:
  {
    "last_updated": "2026-04-24T07:00:00Z",  # ISO-8601 UTC
    "jobs": [
      {
        "id":            "<16-char md5>",
        "title":         str,
        "organisation":  str,
        "location":      str,
        "type":          str,     # full-time/part-time/etc where available
        "url":           str,
        "source":        str,     # "Indeed UK", "Jobs.ac.uk", etc.
        "date_posted":   str,     # ISO-8601, may be empty
        "description":   str,     # truncated to MAX_FIELD_LEN
        "country":       str      # "UK" or "Canada"
      },
      ...
    ]
  }

Retention
---------
MAX_DAYS_OLD = 30. prune_old() drops anything older than that on
each run to stop jobs.json growing unbounded. Jobs without a
parseable date_posted are kept (erring on the side of visibility).

Scheduling
----------
Run daily at 07:00 UTC by .github/workflows/scrape.yml on a
GitHub Actions ubuntu-latest runner. The workflow commits the
updated jobs.json back to main with retry-on-conflict (up to 5
attempts with rebase), so the static site updates without a
redeploy.

Run manually:
    python scrape.py

Or trigger the workflow via the Actions tab (workflow_dispatch).

Dependencies
------------
requests, beautifulsoup4, lxml. Installed by the workflow via
pip; for local runs: pip install requests beautifulsoup4 lxml

Notes
-----
- HEADERS sets a desktop-Chrome UA and en-GB accept-language.
  LinkedIn in particular blocks default python-requests UA.
- Each scraper function is self-contained and returns a list[dict]
  in the unified shape above, so sources can be added or removed
  by editing main() without touching anything else.
- All timestamps stored UTC with "Z" suffix for consistency.
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

# UK-focused search terms (used for Indeed UK and LinkedIn UK)
SEARCH_TERMS_UK = [
    "sport science lecturer",
    "exercise science lecturer",
    "sport exercise science researcher",
    "biomechanics researcher",
    "exercise physiology researcher",
    "wearable technology sport research",
    "strength conditioning researcher",
    "sport science senior lecturer",
    "physical activity health researcher",
    "laboratory technician sport science",
    "sport nutrition lecturer",
    "exercise nutrition researcher",
    "health nutrition lecturer",
    "nutrition science researcher",
]

# Canada-focused search terms (kinesiology terminology used in Canadian HE)
SEARCH_TERMS_CA = [
    "kinesiology lecturer",
    "kinesiology professor",
    "assistant professor kinesiology",
    "associate professor kinesiology",
    "sport science professor",
    "exercise science professor",
    "human kinetics professor",
    "exercise physiology professor",
    "biomechanics professor",
    "sport nutrition professor",
    "physical education professor",
    "health sciences sport professor",
    "laboratory technician kinesiology",
    "research fellow exercise science",
]

REQUIRED_KEYWORDS = [
    "sport", "exercise", "physical activity", "biomechanics", "wearable",
    "strength", "conditioning", "physiology", "fitness", "health science",
    "human movement", "rehabilitation", "performance", "kinesiology",
    "human kinetics", "physical education",
    "lecturer", "senior lecturer", "professor", "assistant professor",
    "associate professor", "research fellow", "postdoc", "postdoctoral",
    "lab technician", "laboratory", "data scientist", "python", "machine learning",
    "resistance training", "older adult", "ageing", "aging", "musculoskeletal",
    "nutrition", "dietetics", "diet",
]

EXCLUDE_KEYWORDS = [
    "clinical fellow", "junior fellow", "medical fellow", "surgical fellow",
    "haematology", "oncology", "cardiology", "anaesthetic", "radiographer",
    "pharmacist", "nurse", "physiotherapist", "occupational therapist",
    "business analyst", "investment analyst", "financial analyst",
    "software engineer", "front-end", "back-end", "devops",
    "tiktok", "ecommerce", "anti-fraud",
    "urology", "gynaecology", "neurosurgery", "ophthalmology",
    "pathology", "dentist", "dental", "veterinary",
]

# Jobs.ac.uk RSS feeds (UK only)
JOBSAC_RSS_FEEDS = [
    ("https://www.jobs.ac.uk/jobs/sport-and-leisure/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/laboratory-clinical-and-technician/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/health-and-medical/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/biological-sciences/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/nutrition-and-food-science/?format=rss", "Jobs.ac.uk"),
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

OUTPUT_FILE = Path("jobs.json")
MAX_DAYS_OLD = 30

# Max characters we'll keep for any single field - prevents runaway payloads
# and keeps jobs.json a sensible size.
MAX_FIELD_LEN = 500


def make_id(url: str, title: str) -> str:
    return hashlib.md5(f"{url}{title}".encode()).hexdigest()[:16]


def normalise_linkedin_url(url: str) -> str:
    """Strip tracking/query params from LinkedIn job URLs so the same
    job found via different search terms produces the same ID."""
    if not url:
        return url
    parsed = urllib.parse.urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


def clean(text: str) -> str:
    """Sanitise a text field pulled from an external source.

    Steps:
      1. Strip any HTML tags (script/style tags and their contents removed).
      2. Decode HTML entities (&amp; -> &, &#39; -> ', etc).
      3. Collapse all whitespace to single spaces.
      4. Remove ASCII control characters (null bytes, backspaces etc.).
      5. Cap length at MAX_FIELD_LEN characters.
    """
    if not text:
        return ""
    # 1. Strip tags via BeautifulSoup (handles malformed HTML, drops script/style)
    try:
        soup = BeautifulSoup(str(text), "html.parser")
        for bad in soup(["script", "style"]):
            bad.decompose()
        stripped = soup.get_text(separator=" ")
    except Exception:
        stripped = str(text)
    # 2. Decode entities twice in case of double-encoded payloads
    stripped = html_module.unescape(html_module.unescape(stripped))
    # 3. Normalise whitespace
    stripped = re.sub(r"\s+", " ", stripped).strip()
    # 4. Drop control characters (keep tab/newline/cr already handled by step 3)
    stripped = "".join(ch for ch in stripped if ord(ch) >= 32 or ch in "\t")
    # 5. Cap length
    if len(stripped) > MAX_FIELD_LEN:
        stripped = stripped[:MAX_FIELD_LEN].rstrip() + "..."
    return stripped


def clean_url(url: str) -> str:
    """Only accept http/https URLs. Strip anything else (javascript:, data:,
    vbscript:, file:, etc.) so a poisoned listing cannot inject an active
    scheme into the front-end."""
    if not url:
        return ""
    url = str(url).strip()
    # Control character check - reject outright
    if any(ord(ch) < 32 for ch in url):
        return ""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme.lower() in ("http", "https") and parsed.netloc:
            # Rebuild a clean URL to normalise it
            return urllib.parse.urlunparse(parsed)
    except Exception:
        pass
    return ""


def passes_filter(job: dict) -> bool:
    text = f"{job.get('title', '')} {job.get('organisation', '')} {job.get('type', '')}".lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw in text:
            return False
    for kw in REQUIRED_KEYWORDS:
        if kw in text:
            return True
    return False


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


def deduplicate(jobs: list) -> list:
    """Remove duplicates based on normalised title + organisation + source.
    Keeps the first occurrence (which will be the earliest-scraped copy)."""
    seen = set()
    unique = []
    for j in jobs:
        key = (
            j.get("title", "").strip().lower(),
            j.get("organisation", "").strip().lower(),
            j.get("source", "").strip().lower(),
        )
        if key not in seen:
            seen.add(key)
            unique.append(j)
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
                    })
                except Exception as e:
                    print(f"    item parse error: {e}")
        except Exception as e:
            print(f"    feed parse error: {e}")
        time.sleep(1)
    return jobs


# ---------------------------------------------------------------------------
# Indeed - RSS feed (UK and Canada)
# ---------------------------------------------------------------------------

def scrape_indeed(term: str, country: str = "UK") -> list:
    jobs = []
    if country == "Canada":
        url = (
            f"https://ca.indeed.com/rss?q={urllib.parse.quote(term)}"
            f"&l=Canada&sort=date&fromage=30"
        )
    else:
        url = (
            f"https://www.indeed.co.uk/rss?q={urllib.parse.quote(term)}"
            f"&l=United+Kingdom&sort=date&fromage=30"
        )
    print(f"  Indeed RSS ({country}): {term}")
    r = get(url)
    if not r:
        return jobs
    try:
        soup = BeautifulSoup(r.text, "xml")
        for item in soup.find_all("item")[:20]:
            try:
                title = clean(item.find("title").get_text()) if item.find("title") else ""
                if not title:
                    continue
                href = item.find("link").get_text().strip() if item.find("link") else ""
                href = clean_url(href)
                pub_date = item.find("pubDate")
                date_str = parse_rss_date(pub_date.get_text() if pub_date else "")
                org = ""
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title = clean(parts[0])
                    org = clean(parts[1])
                jobs.append({
                    "id": make_id(href, title),
                    "title": title,
                    "organisation": org,
                    "location": country,
                    "country": country,
                    "source": "Indeed",
                    "url": href,
                    "date_posted": date_str,
                    "closing_date": "",
                    "type": "",
                })
            except Exception as e:
                print(f"    parse error: {e}")
    except Exception as e:
        print(f"  Indeed RSS parse error: {e}")
    return jobs


# ---------------------------------------------------------------------------
# LinkedIn - public HTML (UK and Canada)
# ---------------------------------------------------------------------------

def scrape_linkedin(term: str, country: str = "UK") -> list:
    jobs = []
    location = "Canada" if country == "Canada" else "United%20Kingdom"
    url = (
        f"https://www.linkedin.com/jobs/search/?keywords={urllib.parse.quote(term)}"
        f"&location={location}&sortBy=DD&f_TPR=r2592000"
    )
    print(f"  LinkedIn ({country}): {term}")
    r = get(url)
    if not r:
        return jobs
    soup = BeautifulSoup(r.text, "html.parser")
    for item in soup.select("div.base-card, li.jobs-search__results-list > li")[:20]:
        try:
            title_el = item.select_one("h3.base-search-card__title, span.sr-only")
            if not title_el:
                continue
            title = clean(title_el.get_text())
            if not title:
                continue
            link_el = item.select_one("a.base-card__full-link, a")
            href = link_el.get("href", "") if link_el else ""
            href = clean_url(normalise_linkedin_url(href))
            org_el = item.select_one("h4.base-search-card__subtitle a, a.hidden-nested-link")
            org = clean(org_el.get_text()) if org_el else ""
            loc_el = item.select_one("span.job-search-card__location")
            loc = clean(loc_el.get_text()) if loc_el else ""
            time_el = item.select_one("time")
            date_str = time_el.get("datetime", datetime.date.today().isoformat()) if time_el else datetime.date.today().isoformat()
            jobs.append({
                "id": make_id(href, title),
                "title": title,
                "organisation": org,
                "location": loc,
                "country": country,
                "source": "LinkedIn",
                "url": href,
                "date_posted": date_str[:10],
                "closing_date": "",
                "type": "",
            })
        except Exception as e:
            print(f"    parse error: {e}")
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
    """Scrape the University Affairs job board (Canada's primary academic job listing)."""
    jobs = []
    url = "https://www.universityaffairs.ca/career-centre/job-board/"
    print(f"  University Affairs HTML scrape...")
    r = get(url)
    if not r:
        return jobs
    try:
        soup = BeautifulSoup(r.text, "html.parser")
        # Job listings are typically in article or li elements with job data
        listings = soup.select("article.job, li.job-listing, div.job-item, .views-row")
        if not listings:
            # Fallback: look for any links with job-like href patterns
            listings = soup.select("h2 a, h3 a, .job-title a")
        for item in listings[:40]:
            try:
                # Try to find title
                title_el = item.select_one("h2, h3, .job-title, a") if hasattr(item, 'select_one') else item
                if not title_el:
                    continue
                title = clean(title_el.get_text())
                if not title or len(title) < 5:
                    continue
                # Find link
                link_el = item.select_one("a") if hasattr(item, 'select_one') else item
                href = ""
                if link_el and link_el.get("href"):
                    href = link_el["href"]
                    if href.startswith("/"):
                        href = "https://www.universityaffairs.ca" + href
                href = clean_url(href)
                # Find organisation
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
    print("=== JobScan scraper starting ===")
    existing = load_existing()
    existing_ids = {j["id"] for j in existing.get("jobs", [])}
    new_jobs = []

    # --- UK sources ---

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

    print("  Running UK scrapers (Indeed + LinkedIn)...")
    uk_scrapers = [
        ("indeed",   scrape_indeed),
        ("linkedin", scrape_linkedin),
    ]
    for source_name, fn in uk_scrapers:
        for term in SEARCH_TERMS_UK:
            try:
                results = fn(term, country="UK")
                added = 0
                for j in results:
                    if j["id"] not in existing_ids and passes_filter(j):
                        new_jobs.append(j)
                        existing_ids.add(j["id"])
                        added += 1
                print(f"    +{added} new from {source_name} UK / '{term}'")
            except Exception as e:
                print(f"  ERROR {source_name} UK '{term}': {e}")
            time.sleep(1.5)

    # --- Canadian sources ---

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

    print("  Running Canadian scrapers (Indeed CA + LinkedIn CA)...")
    ca_scrapers = [
        ("indeed",   scrape_indeed),
        ("linkedin", scrape_linkedin),
    ]
    for source_name, fn in ca_scrapers:
        for term in SEARCH_TERMS_CA:
            try:
                results = fn(term, country="Canada")
                added = 0
                for j in results:
                    if j["id"] not in existing_ids and passes_filter(j):
                        new_jobs.append(j)
                        existing_ids.add(j["id"])
                        added += 1
                print(f"    +{added} new from {source_name} CA / '{term}'")
            except Exception as e:
                print(f"  ERROR {source_name} CA '{term}': {e}")
            time.sleep(1.5)

    # --- Bluesky ---

    print("  Running Bluesky scraper...")
    try:
        bsky_results = scrape_bluesky()
        added = 0
        for j in bsky_results:
            if j["id"] not in existing_ids:
                new_jobs.append(j)
                existing_ids.add(j["id"])
                added += 1
        print(f"    +{added} new from Bluesky")
    except Exception as e:
        print(f"  ERROR bluesky: {e}")

    all_jobs = existing.get("jobs", []) + new_jobs
    all_jobs = prune_old(all_jobs)
    all_jobs = deduplicate(all_jobs)
    all_jobs.sort(key=lambda j: j.get("date_posted") or "", reverse=True)

    print(f"\nTotal jobs: {len(all_jobs)} ({len(new_jobs)} new)")
    save({"jobs": all_jobs})


if __name__ == "__main__":
    main()
