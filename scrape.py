"""
Job scraper for: Indeed (RSS), Jobs.ac.uk (RSS), LinkedIn, Bluesky
Writes results to jobs.json

Search terms tuned for: Sport Science, Nutrition, Wearable Technology, Research, Academia, Lecturing
"""

import json
import hashlib
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

SEARCH_TERMS = [
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

REQUIRED_KEYWORDS = [
    "sport", "exercise", "physical activity", "biomechanics", "wearable",
    "strength", "conditioning", "physiology", "fitness", "health science",
    "human movement", "rehabilitation", "performance", "kinesiology",
    "lecturer", "senior lecturer", "professor", "research fellow", "postdoc",
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

JOBSAC_RSS_FEEDS = [
    ("https://www.jobs.ac.uk/jobs/sport-and-leisure/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/laboratory-clinical-and-technician/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/health-and-medical/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/biological-sciences/?format=rss", "Jobs.ac.uk"),
    ("https://www.jobs.ac.uk/jobs/nutrition-and-food-science/?format=rss", "Jobs.ac.uk"),
]

BLUESKY_ACCOUNTS = [
    "jobsinsportscience.bsky.social",
]

OUTPUT_FILE = Path("jobs.json")
MAX_DAYS_OLD = 90


def make_id(url: str, title: str) -> str:
    return hashlib.md5(f"{url}{title}".encode()).hexdigest()[:16]


def normalise_linkedin_url(url: str) -> str:
    """Strip tracking/query params from LinkedIn job URLs so the same
    job found via different search terms produces the same ID."""
    if not url:
        return url
    parsed = urllib.parse.urlparse(url)
    # LinkedIn job URLs look like linkedin.com/jobs/view/1234567890...
    # Keep only the path, drop all query params and fragments
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


def clean(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


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
# Jobs.ac.uk - Official RSS feeds
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
                    desc_el = item.find("description")
                    desc = BeautifulSoup(desc_el.get_text(), "html.parser").get_text() if desc_el else ""
                    org = ""
                    org_match = re.search(r"(?:Employer|Institution|Organisation):\s*(.+?)(?:\n|$)", desc, re.I)
                    if org_match:
                        org = org_match.group(1).strip()
                    loc = ""
                    loc_match = re.search(r"(?:Location|Place):\s*(.+?)(?:\n|$)", desc, re.I)
                    if loc_match:
                        loc = loc_match.group(1).strip()
                    closing = ""
                    close_match = re.search(r"(?:Closing date|Closes):\s*(.+?)(?:\n|$)", desc, re.I)
                    if close_match:
                        closing = close_match.group(1).strip()
                    pub_date = item.find("pubDate")
                    date_str = parse_rss_date(pub_date.get_text() if pub_date else "")
                    jobs.append({
                        "id": make_id(href, title),
                        "title": title,
                        "organisation": org,
                        "location": loc,
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
# Indeed - RSS feed
# ---------------------------------------------------------------------------

def scrape_indeed(term: str) -> list:
    jobs = []
    url = (
        f"https://www.indeed.co.uk/rss?q={urllib.parse.quote(term)}"
        f"&l=United+Kingdom&sort=date&fromage=30"
    )
    print(f"  Indeed RSS: {term}")
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
                pub_date = item.find("pubDate")
                date_str = parse_rss_date(pub_date.get_text() if pub_date else "")
                org = ""
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title = parts[0].strip()
                    org = parts[1].strip()
                jobs.append({
                    "id": make_id(href, title),
                    "title": title,
                    "organisation": org,
                    "location": "UK",
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
# LinkedIn - public HTML
# ---------------------------------------------------------------------------

def scrape_linkedin(term: str) -> list:
    jobs = []
    url = (
        f"https://www.linkedin.com/jobs/search/?keywords={urllib.parse.quote(term)}"
        f"&location=United%20Kingdom&sortBy=DD&f_TPR=r2592000"
    )
    print(f"  LinkedIn: {term}")
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
            href = normalise_linkedin_url(href)
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
                    first_line = text.split("\n")[0].strip()
                    title = first_line[:120] if first_line else text[:120]
                    jobs.append({
                        "id": make_id(post_url, title),
                        "title": title,
                        "organisation": handle.replace(".bsky.social", ""),
                        "location": "",
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

    scrapers = [
        ("indeed",   scrape_indeed),
        ("linkedin", scrape_linkedin),
    ]

    for source_name, fn in scrapers:
        for term in SEARCH_TERMS:
            try:
                results = fn(term)
                added = 0
                for j in results:
                    if j["id"] not in existing_ids and passes_filter(j):
                        new_jobs.append(j)
                        existing_ids.add(j["id"])
                        added += 1
                print(f"    +{added} new from {source_name} / '{term}'")
            except Exception as e:
                print(f"  ERROR {source_name} '{term}': {e}")
            time.sleep(1.5)

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

    dupes_removed = len(existing.get("jobs", []) + new_jobs) - len(prune_old(existing.get("jobs", []) + new_jobs))
    print(f"\nTotal jobs: {len(all_jobs)} ({len(new_jobs)} new)")
    save({"jobs": all_jobs})


if __name__ == "__main__":
    main()
