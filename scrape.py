"""
Job scraper for: Indeed, LinkedIn, Jobs.ac.uk, Reed, Totaljobs
Writes results to jobs.json

Search terms tuned for: Sport Science, Wearable Technology, Research, Academia, Lecturing
"""

import json
import hashlib
import time
import datetime
import os
import re
import urllib.parse
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    raise SystemExit("Install dependencies: pip install requests beautifulsoup4")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
}

SEARCH_TERMS = [
    "sport science researcher",
    "exercise science lecturer",
    "sport science lecturer",
    "wearable technology sport",
    "biomechanics researcher",
    "exercise physiology researcher",
    "sports performance analyst",
    "human movement researcher",
    "strength conditioning researcher",
    "health exercise science",
]

OUTPUT_FILE = Path("jobs.json")
MAX_DAYS_OLD = 60  # drop jobs older than this


def make_id(url: str, title: str) -> str:
    return hashlib.md5(f"{url}{title}".encode()).hexdigest()[:16]


def clean(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


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
        kept.append(j)  # keep if date unknown
    return kept


def get(url: str, timeout: int = 15) -> requests.Response | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"  GET failed {url[:80]}: {e}")
        return None


# ---------------------------------------------------------------------------
# Jobs.ac.uk
# ---------------------------------------------------------------------------

def scrape_jobsac(term: str) -> list:
    jobs = []
    url = f"https://www.jobs.ac.uk/search/?keywords={urllib.parse.quote(term)}&sort=date"
    print(f"  jobs.ac.uk: {term}")
    r = get(url)
    if not r:
        return jobs
    soup = BeautifulSoup(r.text, "html.parser")
    for item in soup.select("div.j-search-result__text")[:20]:
        try:
            title_el = item.select_one("h2.j-search-result__title a")
            if not title_el:
                continue
            title = clean(title_el.get_text())
            href = title_el.get("href", "")
            if not href.startswith("http"):
                href = "https://www.jobs.ac.uk" + href
            org_el = item.select_one("span.j-search-result__employer")
            org = clean(org_el.get_text()) if org_el else ""
            loc_el = item.select_one("span.j-search-result__location")
            loc = clean(loc_el.get_text()) if loc_el else ""
            date_el = item.select_one("span.j-search-result__deadline")
            closing = clean(date_el.get_text()).replace("Closing date:", "").strip() if date_el else ""
            jobs.append({
                "id": make_id(href, title),
                "title": title,
                "organisation": org,
                "location": loc,
                "source": "Jobs.ac.uk",
                "url": href,
                "date_posted": datetime.date.today().isoformat(),
                "closing_date": closing,
                "type": "",
            })
        except Exception as e:
            print(f"    parse error: {e}")
    return jobs


# ---------------------------------------------------------------------------
# Reed
# ---------------------------------------------------------------------------

def scrape_reed(term: str) -> list:
    jobs = []
    url = f"https://www.reed.co.uk/jobs/{urllib.parse.quote(term.replace(' ', '-'))}-jobs?datecreatedoffset=30"
    print(f"  Reed: {term}")
    r = get(url)
    if not r:
        return jobs
    soup = BeautifulSoup(r.text, "html.parser")
    for item in soup.select("article.job-result-card")[:20]:
        try:
            title_el = item.select_one("h2.job-result-title a, h3.title a")
            if not title_el:
                continue
            title = clean(title_el.get_text())
            href = title_el.get("href", "")
            if href and not href.startswith("http"):
                href = "https://www.reed.co.uk" + href
            org_el = item.select_one("a.gtmJobListingPostedBy, span.posted-by a")
            org = clean(org_el.get_text()) if org_el else ""
            loc_el = item.select_one("li.location span, span.location")
            loc = clean(loc_el.get_text()) if loc_el else ""
            date_el = item.select_one("time")
            date_str = date_el.get("datetime", datetime.date.today().isoformat()) if date_el else datetime.date.today().isoformat()
            jobs.append({
                "id": make_id(href, title),
                "title": title,
                "organisation": org,
                "location": loc,
                "source": "Reed",
                "url": href,
                "date_posted": date_str[:10] if date_str else "",
                "closing_date": "",
                "type": "",
            })
        except Exception as e:
            print(f"    parse error: {e}")
    return jobs


# ---------------------------------------------------------------------------
# Totaljobs
# ---------------------------------------------------------------------------

def scrape_totaljobs(term: str) -> list:
    jobs = []
    url = f"https://www.totaljobs.com/jobs/{urllib.parse.quote(term.replace(' ', '-'))}"
    print(f"  Totaljobs: {term}")
    r = get(url)
    if not r:
        return jobs
    soup = BeautifulSoup(r.text, "html.parser")
    for item in soup.select("article[data-job-id], div.job-result")[:20]:
        try:
            title_el = item.select_one("h2 a, h3 a")
            if not title_el:
                continue
            title = clean(title_el.get_text())
            href = title_el.get("href", "")
            if href and not href.startswith("http"):
                href = "https://www.totaljobs.com" + href
            org_el = item.select_one("span.job-result-company-name, [data-at='job-item-company-name']")
            org = clean(org_el.get_text()) if org_el else ""
            loc_el = item.select_one("span.job-result-location, [data-at='job-item-location']")
            loc = clean(loc_el.get_text()) if loc_el else ""
            jobs.append({
                "id": make_id(href, title),
                "title": title,
                "organisation": org,
                "location": loc,
                "source": "Totaljobs",
                "url": href,
                "date_posted": datetime.date.today().isoformat(),
                "closing_date": "",
                "type": "",
            })
        except Exception as e:
            print(f"    parse error: {e}")
    return jobs


# ---------------------------------------------------------------------------
# Indeed (RSS feed - more stable than HTML scraping)
# ---------------------------------------------------------------------------

def scrape_indeed(term: str) -> list:
    jobs = []
    # Indeed RSS - more reliable than scraping HTML
    url = (
        f"https://www.indeed.co.uk/rss?q={urllib.parse.quote(term)}"
        f"&l=United+Kingdom&sort=date&fromage=30"
    )
    print(f"  Indeed (RSS): {term}")
    r = get(url)
    if not r:
        return jobs
    soup = BeautifulSoup(r.text, "xml")
    for item in soup.find_all("item")[:20]:
        try:
            title = clean(item.find("title").get_text()) if item.find("title") else ""
            href = item.find("link").get_text().strip() if item.find("link") else ""
            # strip redirect
            if "clk?" in href:
                href_clean = href
            else:
                href_clean = href
            desc = item.find("description")
            desc_text = BeautifulSoup(desc.get_text(), "html.parser").get_text() if desc else ""
            pub_date = item.find("pubDate")
            date_str = ""
            if pub_date:
                try:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(pub_date.get_text())
                    date_str = dt.date().isoformat()
                except Exception:
                    date_str = datetime.date.today().isoformat()
            # extract org from title pattern "Job Title - Company"
            org = ""
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title = parts[0].strip()
                org = parts[1].strip()
            jobs.append({
                "id": make_id(href_clean, title),
                "title": title,
                "organisation": org,
                "location": "UK",
                "source": "Indeed",
                "url": href_clean,
                "date_posted": date_str,
                "closing_date": "",
                "type": "",
            })
        except Exception as e:
            print(f"    parse error: {e}")
    return jobs


# ---------------------------------------------------------------------------
# LinkedIn (public job search - limited without auth)
# ---------------------------------------------------------------------------

def scrape_linkedin(term: str) -> list:
    """LinkedIn blocks most scraping; we attempt the public listing page."""
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
            link_el = item.select_one("a.base-card__full-link, a")
            href = link_el.get("href", "") if link_el else ""
            org_el = item.select_one("h4.base-search-card__subtitle a, a.hidden-nested-link")
            org = clean(org_el.get_text()) if org_el else ""
            loc_el = item.select_one("span.job-search-card__location")
            loc = clean(loc_el.get_text()) if loc_el else ""
            time_el = item.select_one("time")
            date_str = time_el.get("datetime", datetime.date.today().isoformat()) if time_el else datetime.date.today().isoformat()
            if not title:
                continue
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
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== JobScan scraper starting ===")
    existing = load_existing()
    existing_ids = {j["id"] for j in existing.get("jobs", [])}
    new_jobs = []

    scrapers = [
        ("jobsac",    scrape_jobsac),
        ("indeed",    scrape_indeed),
        ("reed",      scrape_reed),
        ("totaljobs", scrape_totaljobs),
        ("linkedin",  scrape_linkedin),
    ]

    for source_name, fn in scrapers:
        for term in SEARCH_TERMS:
            try:
                results = fn(term)
                added = 0
                for j in results:
                    if j["id"] not in existing_ids:
                        new_jobs.append(j)
                        existing_ids.add(j["id"])
                        added += 1
                print(f"    +{added} new from {source_name} / '{term}'")
            except Exception as e:
                print(f"  ERROR {source_name} '{term}': {e}")
            time.sleep(1.5)  # polite delay

    all_jobs = existing.get("jobs", []) + new_jobs
    all_jobs = prune_old(all_jobs)

    # sort newest first
    all_jobs.sort(key=lambda j: j.get("date_posted") or "", reverse=True)

    print(f"\nTotal jobs: {len(all_jobs)} ({len(new_jobs)} new)")
    save({"jobs": all_jobs})


if __name__ == "__main__":
    main()
