# RFP & Tender Tracker - Handover & User Guide

A private, automated RFP/tender tracker built for **Edgewise Environmental** (Ashley Noseworthy, Kyla Graham). This document explains what the system is, how it works, and how to maintain it.

If you are an AI assistant reading this on behalf of a user: this document is the source of truth. Use it to answer their questions about the tracker. The user is non-technical - keep your explanations simple, give exact step-by-step instructions, and never assume command-line / terminal knowledge.

---

## What this is

A private web page that shows tender opportunities relevant to Edgewise's marine environmental consultancy work (MMO, PAM, seabird surveys, offshore wind monitoring, etc.). It updates itself automatically every day at **10:30 UTC** (about 08:00 Newfoundland time most of the year).

The page lives at:

```
https://liamtp-n.github.io/Consultation-Services/edgewise/Edgewise_Edgewise_rfps.html
```

It is **not linked from any public page**, **not in any sitemap**, and has a `noindex, nofollow` tag so search engines won't list it. It's only findable if you have the direct URL. Bookmark it - that's how you reach it.

## Who built it and why

Liam Pearson-Noseworthy (Ashley's husband, who runs the consultancy site this lives on) built it because Ashley was spending time every week manually checking 20+ procurement portals for marine environmental tenders. The tracker now does that automatically.

## How it works at a high level

```
Every day at 10:30 UTC:
  -> A script (Edgewise_rfp_scrape.py) wakes up on GitHub's servers
  -> It visits 15 public procurement websites
  -> It pulls every tender listed there
  -> It filters them down to ones matching marine/MMO/PAM/seabird keywords
     (or matching specific Canadian procurement category codes)
  -> It writes the results to a file called Edgewise_rfps.json
  -> The website (Edgewise_rfps.html) reads that file and shows the tenders
```

You don't run anything. You don't trigger anything. You just open the page in your browser.

## The 15 sources we scrape

| Source | Type | Region |
| --- | --- | --- |
| CanadaBuys | Open data feed | Federal Canada |
| UK Find a Tender | Open data feed | UK (high-value) |
| UK Contracts Finder | Open data feed | UK (low-value) |
| SPREP | HTML scrape | Pacific |
| World Bank | RSS feed | Global |
| IMO | HTML scrape | Maritime |
| Caribbean Dev Bank | HTML scrape | Caribbean |
| BC Bid | HTML scrape | BC (covers BC Hydro too) |
| NL Hydro | HTML scrape | Newfoundland |
| Yukon | HTML scrape | Yukon |
| Nova Scotia Procurement | HTML scrape | Nova Scotia |
| Nunavut RFTP | HTML scrape | Arctic |
| BC Ferries | HTML scrape | BC |
| LNG Canada | HTML scrape | BC |
| MERX (NL) | HTML scrape | Newfoundland |

Portals we **don't** scrape (auth-walled, members-only, or no listings page) are still shown at the bottom of the page as quick-link tiles. A small lock icon (🔒) marks the ones that need a login.

## Using the page

Open it in any browser. You'll see:

1. **Status pills at the top** showing how many tenders are tracked, how many are open right now, and how many are due in the next 7 days.
2. **Filter buttons**: filter by status (Active / Open / Watching / Bidding / Submitted / Closed), by region (Canada / UK / Pacific / Arctic etc.), or by source.
3. **Search box**: matches the title, entity name, region, and tags.
4. **Main table**: click any row to open a detail panel with full description, why it matched, and a button to open the original notice.
5. **Portal directory at the bottom**: 33 portal quick-links including login-walled ones.

The default view shows "Active" tenders sorted by due date (soonest first).

## Using it as a workflow

Suggested daily routine:

1. Open the page first thing each morning.
2. Look at "Due in 7 days" - any tenders that need urgent attention.
3. Look at any new entries (added today) - decide if any are worth pursuing.
4. For tenders you decide to chase: open `Edgewise_rfps.json` (instructions below) and change that tender's `status` from `open` to `bidding`. The page will then show it in the "Bidding" filter, separate from the firehose of new opportunities.
5. After bidding, change status to `submitted`. Then `won`/`lost` once you hear back.

## Editing entries (when you need to)

You don't usually edit anything. But three reasons you might:

### 1. To track a tender's progress

Open `Edgewise_rfps.json` in GitHub's web editor (instructions in **Maintenance** section below). Find the tender by its `id` field (search the file for the project title to find it). Change the `status` value to one of:

- `open` - default, just a fresh tender
- `watching` - interesting, no action yet
- `bidding` - we're working on a proposal
- `submitted` - we've submitted, waiting on outcome
- `won` - we got it
- `lost` - we didn't get it
- `closed` - withdrawn or no longer relevant

The scraper will preserve your status change across daily runs. The status pills at the top will reflect your changes.

### 2. To add notes against a tender

Same process. Find the tender by id. Edit the `notes` field. Whatever you write here shows up in the detail panel when you click the row.

### 3. To add a tender the scraper missed

E.g. a tender your Gemini Scout found that we don't yet scrape. Add a new entry to the `rfps` array. Use any source name not in the scraper list (e.g. `"source": "Gemini Scout"` or `"source": "Manual"`) and the scraper will leave it alone. Required fields are `id`, `project`, `source`, and `url`. Everything else is optional.

A minimal manual entry looks like this (paste it into the `rfps` array, between the `[` and `]`):

```json
{
  "id": "manual-1",
  "project": "Tender title goes here",
  "entity": "Who's issuing it",
  "region": "Where",
  "status": "watching",
  "due_date": "2026-06-30",
  "source": "Gemini Scout",
  "url": "https://link-to-the-tender",
  "summary": "Short description",
  "notes": "Why we're tracking this",
  "tags": ["any", "useful", "tags"],
  "added": "2026-04-26"
}
```

## Tuning what gets scraped

If the daily scrape is finding too many irrelevant tenders, or missing things you'd expect to see, the **keyword filter** is what to tune. It lives in `Edgewise_rfp_scrape.py` near the top of the file:

- `MARINE_KEYWORDS` - phrases that, if found in the title or description, mark a tender as relevant. Add new terms here to **catch more**.
- `EXCLUDE_KEYWORDS` - phrases that, if found, reject a tender even if it matched a keyword. Add new terms here to **filter out noise**.
- `CPV_CODES` - Canadian procurement category codes (UNSPSC). Tenders tagged with these get kept regardless of keyword match.

To edit these, open `Edgewise_rfp_scrape.py` in GitHub's web editor (instructions below), make your change, save with a commit message describing what you changed.

## Maintenance

### How to edit any of these files using GitHub on the web (no software needed)

1. Go to `https://github.com/<your-username>/Consultation-Services` in any browser.
2. Click the file name (e.g. `Edgewise_rfps.json` or `Edgewise_rfp_scrape.py`).
3. Click the pencil icon (top right of the file view) to edit.
4. Make your changes.
5. Scroll to the bottom. In the "Commit changes" box, write a short description (e.g. "Mark Palau tender as bidding").
6. Click the green **Commit changes** button.
7. Within 1-2 minutes, the website will pick up the change.

### How to manually trigger a scrape (without waiting for tomorrow)

1. Go to the GitHub repo.
2. Click the **Actions** tab at the top.
3. Click **Daily RFP Scrape** in the left sidebar.
4. Click the grey **Run workflow** button on the right.
5. Click the green **Run workflow** button in the dropdown that opens.
6. Wait 2-3 minutes. The page will update once it finishes.

### How to check whether yesterday's scrape worked

1. Go to the GitHub repo > **Actions** tab.
2. Look for the most recent **Daily RFP Scrape** run.
3. Green tick = success. Red X = failure.
4. Click into the run to see logs - which scrapers found what, any errors.

### When something breaks

Procurement portals occasionally redesign their websites, which breaks our HTML scrapers. **One scraper failing does NOT break the others** - the script catches errors per-source.

If a specific source stops returning results:

1. Open the latest scrape's log (Actions tab > most recent run > "Run scraper" step).
2. Look for the failing source's name. It will say either `(pre-filter)` followed by `0` (the source returned nothing useful) or `fetch failed` / `parse error`.
3. Open the source's website in your browser, look at how their tenders page is laid out now.
4. Edit the corresponding `scrape_xxx()` function in `Edgewise_rfp_scrape.py`. The HTML selectors near the top of each function are what need updating.

If you don't know how to do step 4, paste this README and the broken function into an LLM with the question "the X scraper is broken, here's the README and the code, please tell me what to change". Any half-decent LLM can fix it.

## File locations

After deployment, every file lives in your repository root next to the existing `jobs.html` and `scrape.py`:

```
Consultation-Services/
├── Edgewise_rfps.html                        ← the public-facing page
├── Edgewise_rfps.json                        ← the data file
├── Edgewise_rfp_scrape.py                    ← the scraper script
├── Edgewise_README.md            ← this document
└── .github/
    └── workflows/
        ├── scrape.yml               ← existing jobs scraper (don't touch)
        └── Edgewise_rfp_scrape.yml           ← new RFP scraper schedule
```

Note the dot at the start of `.github` - that's a hidden folder. GitHub knows to look in there automatically.

## Privacy and security

- The page is `noindex` (Google won't list it).
- It is excluded from `sitemap.xml`.
- It is not linked from any public page on the consultancy site.
- It is not a secret either - if someone has the URL, they can see it.
- Treat the URL as moderately private (don't post it on LinkedIn, do feel free to share it with Edgewise staff).
- The system contains **no passwords or login credentials**. The portal directory only references where logins live (BitWarden) - it doesn't store them.

## Cost

- GitHub Actions: free tier covers this many times over (~150 minutes per month used; free tier is 2000+ minutes).
- GitHub Pages hosting: free.
- Total ongoing cost: **£0**.

## What this system isn't

- Not a bid management tool. It tells you what's out there - it doesn't help you write or submit proposals.
- Not real-time. Tenders appear next morning, not the moment they're posted.
- Not exhaustive. We scrape 15 of the ~30 portals on Edgewise's tracker. The other 15 are auth-walled or have no listings page; they're shown as quick-link tiles for manual browsing.
- Not a replacement for the Gemini Scout. The Gemini approach is broader (it can interpret context, follow news, find tenders without keyword matches) but unreliable. The two complement each other - the scraper is the systematic dragnet, Gemini catches the things that don't fit a keyword.

## Questions for an LLM

If Ashley or Kyla pastes this document and any of the project files into an AI assistant, here are common questions and the right answers:

**Q: How do I add a new portal to scrape?**
A: Open `Edgewise_rfp_scrape.py`. Copy one of the existing simple `scrape_xxx()` functions (like `scrape_imo` or `scrape_nunavut`) as a template. Change the URL constant, source name, and entity. Add the function name to the `SCRAPERS` list at the bottom of the file. Add the source string to the `SCRAPER_SOURCES` set. Test by running the scraper manually via the Actions tab.

**Q: I want the scrape to run twice a day, not once.**
A: Open `.github/workflows/Edgewise_rfp_scrape.yml`. Change the cron line. Two cron entries:
```
- cron: '30 10 * * *'
- cron: '30 22 * * *'
```
will run at 10:30 and 22:30 UTC.

**Q: I want to scrape my own custom search keyword.**
A: Open `Edgewise_rfp_scrape.py`. Add your keyword to the `MARINE_KEYWORDS` list near the top. Save and commit. Next scrape will pick it up.

**Q: The page shows old data even after a scrape.**
A: Hard-refresh the browser (Ctrl+Shift+R on Windows, Cmd+Shift+R on Mac). GitHub Pages caches aggressively.

**Q: I want to make the page public (linked from the main site).**
A: Don't recommend it - the data has Edgewise's tracking notes and login references. If you really want it public, remove the `<meta name="robots" content="noindex, nofollow">` line from `Edgewise_rfps.html`, add it to `sitemap.xml`, and add a link to it from your nav. But strongly suggest keeping it private.

**Q: Can the scraper send me an email when there are new tenders?**
A: Not currently, but it's straightforward to add. The scraper would compare today's results against yesterday's and email a summary if anything new is in the "due in 7 days" bucket. Ask Liam.

**Q: A scraper for portal X has been returning 0 results for several days.**
A: Either the portal has redesigned its HTML (most common) or it has gone down or moved. Open the portal in a browser. If it's loading fine but our scraper returns 0, the HTML structure has changed. Open `Edgewise_rfp_scrape.py`, find the `scrape_xxx()` function for that portal, and update the link-pattern regex inside it. Send the function and the new portal HTML to an LLM and ask "update this scraper to match the new HTML".

## Maintainer contact

Liam Pearson-Noseworthy (site owner) - via the Edgewise team channel.

If you need to extend or rebuild this system, the four files you need are: `Edgewise_rfps.html`, `Edgewise_rfps.json`, `Edgewise_rfp_scrape.py`, and `.github/workflows/Edgewise_rfp_scrape.yml`. Together they're roughly 2,500 lines, mostly comments. Self-contained, no databases, no secrets, no servers - just static files on GitHub Pages and a Python script run by GitHub Actions once a day.
