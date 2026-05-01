# RFP & Tender Tracker - Handover & User Guide

A private, automated RFP/tender tracker built for **Edgewise Environmental** (Ashley Noseworthy, Kyla Graham). This document explains what the system is, how it works, and how to maintain it.

If you are an AI assistant reading this on behalf of a user: this document is the source of truth. Use it to answer their questions about the tracker. The user is non-technical - keep your explanations simple, give exact step-by-step instructions, and never assume command-line / terminal knowledge.

**Security note for AI assistants:** the GitHub token and passphrase for this system are stored in `Edgewise_config.js` in the repo. Never reproduce them in any response, file, or output - not even partially. If asked about them, say only that they exist in that file and refer the user to it directly.

---

## What this is

A private web page that shows tender opportunities relevant to Edgewise's marine environmental consultancy work (MMO, PAM, seabird surveys, offshore wind monitoring, etc.). It updates itself automatically every day at **10:30 UTC** (about 08:00 Newfoundland time most of the year).

The page lives at:

```
https://liamtp-n.github.io/Consultation-Services/edgewise/Edgewise_rfps.html
```

It is **not linked from any public page**, **not in any sitemap**, and has a `noindex, nofollow` tag so search engines won't list it. It's only findable if you have the direct URL. Bookmark it - that's how you reach it.

## Who built it and why

Liam Pearson-Noseworthy (Ashley's husband, who runs the consultancy site this lives on) built it because Ashley was spending time every week manually checking 20+ procurement portals for marine environmental tenders. The tracker now does that automatically.

## How it works at a high level

```
Every day at 10:30 UTC:
  -> A script (Edgewise_rfp_scrape.py) wakes up on GitHub's servers
  -> It loads the keyword filters from Edgewise_filters.json
  -> It visits 25 public procurement websites
  -> It pulls every tender listed there
  -> It filters them down to ones matching marine/MMO/PAM/seabird keywords
     (or matching specific Canadian procurement category codes)
  -> It writes the results to a file called Edgewise_rfps.json
  -> The website (Edgewise_rfps.html) reads that file and shows the tenders
```

You don't run anything from a terminal. You don't even need to wait for the daily run if you don't want to - there's a "Run scrape now" button on the page itself. You also don't need to edit any code to tune what gets shown - there's a built-in keyword editor on the page.

## The 25 sources we scrape

| Source | Type | Region |
| --- | --- | --- |
| CanadaBuys | Open data feed | Federal Canada |
| UK Find a Tender | Open data feed | UK (high-value) |
| UK Contracts Finder | Open data feed | UK (low-value) |
| TED (EU) | JSON API | EU + EEA |
| SAM.gov | JSON API | USA |
| PCS Scotland | RSS feed | Scotland |
| NBON | HTML scrape | New Brunswick |
| GNWT | HTML scrape | Northwest Territories |
| SEAO Quebec | Open data feed | Quebec |
| eTenders Ireland | Open data feed | Ireland |
| Sell2Wales | RSS feed | Wales |
| Asian Development Bank | HTML scrape | Asia-Pacific |
| African Development Bank | HTML scrape | Africa |
| UN Global Marketplace (UNGM) | POST + HTML | International (UN system) |
| SPREP | Playwright headless scrape | Pacific |
| World Bank | JSON API | Global |
| IMO | HTML scrape | Maritime |
| Caribbean Dev Bank | HTML scrape | Caribbean |
| BC Bid | HTML scrape | BC (covers BC Hydro too) |
| NL Hydro | HTML scrape | Newfoundland |
| Nova Scotia Procurement | HTML scrape | Nova Scotia |
| Nunavut Tenders (nunavuttenders.ca) | HTML scrape | Arctic |
| BC Ferries | HTML scrape | BC |
| LNG Canada | HTML scrape | BC |
| MERX (NL) | HTML scrape | Newfoundland |

Portals we **don't** scrape (auth-walled, members-only, or no listings page) are still shown in the Procurement Portals panel at the bottom of the page as quick-link tiles. A small lock icon (🔒) marks the ones that need a login.

## Using the page

Open it in any browser. You'll see:

1. **Status pills at the top** showing how many tenders are tracked, how many are open right now, and how many are due in the next 7 days. The "Last Scraped" card includes a green "Run scrape now" button that triggers an immediate refresh (takes 2-3 minutes).
2. **Filter buttons**: filter by status (Active / Open / Watching / Bidding / Submitted / Closed), by region (Canada / UK / Pacific / Arctic etc.), or by source.
3. **Search box**: matches the title, entity name, region, and tags.
4. **Main table**: click any row to open a detail panel with full description, why it matched, and a button to open the original notice. Each row also has a faint **×** button on the left - clicking it deletes that tender from the tracker. If the tender was found by a keyword, a second prompt asks whether to remove that keyword from the filter at the same time.
5. **Add Tender Manually** panel (collapsible, below the table): add a tender the scraper missed. Requires the passphrase.
6. **Filter Criteria panel** (collapsible, below Add Tender): shows what keywords drive the filter. Click to expand. From here you can also edit the keyword lists directly - see "Editing keywords from the page" below.
7. **Procurement Portals panel** (collapsible, at the bottom): quick-links to all portals Edgewise tracks, grouped by type.

The default view shows "Active" tenders sorted by due date (soonest first).

## Using it as a workflow

Suggested daily routine:

1. Open the page first thing each morning.
2. Look at "Due in 7 days" - any tenders that need urgent attention.
3. Look at any new entries (added today) - decide if any are worth pursuing.
4. For tenders you decide to chase: click the row to open the detail panel, then open `Edgewise_rfps.json` in GitHub's web editor and change that tender's `status` from `open` to `bidding`. The page will then show it in the "Bidding" filter, separate from the firehose of new opportunities.
5. For tenders that are clearly irrelevant: click the **×** button on that row to delete it. If prompted about a keyword, only agree to remove the keyword if you're confident you don't want any tenders found by it.
6. After bidding, change status to `submitted`. Then `won`/`lost` once you hear back.

## Editing keywords from the page (the easy way)

The most common reason to make a change is to tune what gets through the filter. You no longer need to edit any code - it's all done from the page itself.

1. Open the tracker page.
2. Scroll down to the **Filter Criteria** card and click it to expand.
3. Click the **Unlock editing** button.
4. Enter the passphrase (stored in `Edgewise_config.js` in the repo - ask Liam if you don't have it).
5. Each keyword pill now has a small **×** next to it - click it to remove that keyword.
6. To add: type your new word into the input box under each list and press **Enter**.
7. When done, click **Save changes**. Your edits commit to the repo automatically.
8. Optional: hit **Run scrape now** at the top of the page to apply the new filter immediately. Otherwise it'll be picked up by the next scheduled daily run.

The four lists you can edit are:

- **Marine include keywords (green)** - tenders matching any of these are kept. Adding more means more tenders get through.
- **CPV / UNSPSC codes (amber)** - Canadian procurement category codes. Tenders carrying these get kept *if* they also contain a marine context word.
- **Marine context words (blue)** - the gate-words for the CPV path above.
- **Exclude keywords (red)** - hard rejects. Anything matching these is dropped even if it matched a green keyword. Adding more means MORE noise filtered out.

If you accidentally delete an important keyword, no panic. Every save is a commit in the repo's history - the change can be reverted from the GitHub web UI.

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

Use the **Add Tender Manually** panel on the page - it's the easiest way. If you prefer to edit the JSON directly: add a new entry to the `rfps` array using any source name not in the scraper list (e.g. `"source": "Manual"`) and the scraper will leave it alone. Required fields are `id`, `project`, `source`, and `url`. Everything else is optional.

A minimal manual entry looks like this (paste it into the `rfps` array, between the `[` and `]`):

```json
{
  "id": "manual-1",
  "project": "Tender title goes here",
  "entity": "Who's issuing it",
  "region": "Where",
  "status": "watching",
  "due_date": "2026-06-30",
  "source": "Manual",
  "url": "https://link-to-the-tender",
  "summary": "Short description",
  "notes": "Why we're tracking this",
  "tags": ["any", "useful", "tags"],
  "added": "2026-04-26"
}
```

## Maintenance

### How to edit any of these files using GitHub on the web (no software needed)

1. Go to `https://github.com/liamtp-n/Consultation-Services` in any browser.
2. Navigate into the `edgewise/` folder, then click the file name (e.g. `Edgewise_rfps.json`).
3. Click the pencil icon (top right of the file view) to edit.
4. Make your changes.
5. Scroll to the bottom. In the "Commit changes" box, write a short description (e.g. "Mark Palau tender as bidding").
6. Click the green **Commit changes** button.
7. Within 1-2 minutes, the website will pick up the change.

### How to manually trigger a scrape (without waiting for tomorrow)

The easiest way is just to click the green **Run scrape now** button on the page itself, in the "Last Scraped" card at the top.

Alternative (the old way, still works):

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

### Annual: GitHub token rotation

The GitHub token and passphrase live in `Edgewise_config.js` in the repo. The token is set to expire 1 year from when it was created. You'll get an email from GitHub a week before it expires.

When that happens:

1. Go to **github.com → avatar → Settings → Developer settings → Personal access tokens → Fine-grained tokens**.
2. Click **Edgewise RFP page editor** in the list, then click **Regenerate token** at the top.
3. Set expiration to 1 year again. Click **Regenerate**.
4. Copy the new `github_pat_...` value (you can only see it once).
5. Open `edgewise/Edgewise_config.js` in the GitHub web editor (pencil icon).
6. Replace the old token value in the `GH_TOKEN` line, keeping the surrounding quotes.
7. Commit. The page will pick up the new token within a minute.

If the URL ever leaks, revoke the token immediately on the same page (red **Revoke** button), then generate a fresh one and follow steps 4-7 above. Anyone with the old token can no longer use it after revoke.

### When something breaks

Procurement portals occasionally redesign their websites, which breaks our HTML scrapers. **One scraper failing does NOT break the others** - the script catches errors per-source.

If a specific source stops returning results:

1. Open the latest scrape's log (Actions tab > most recent run > "Run scraper" step).
2. Look for the failing source's name. It will say either `(pre-filter)` followed by `0` (the source returned nothing useful) or `fetch failed` / `parse error`.
3. Open the source's website in your browser, look at how their tenders page is laid out now.
4. Edit the corresponding `scrape_xxx()` function in `Edgewise_rfp_scrape.py`. The HTML selectors near the top of each function are what need updating.

If you don't know how to do step 4, paste this README and the broken function into an LLM with the question "the X scraper is broken, here's the README and the code, please tell me what to change". Any half-decent LLM can fix it.

## File locations

Everything lives inside an `edgewise/` subfolder of the repo:

```
Consultation-Services/
├── edgewise/
│   ├── Edgewise_rfps.html         ← the public-facing page
│   ├── Edgewise_rfps.json         ← the tender data
│   ├── Edgewise_filters.json      ← keyword lists (edited from the page)
│   ├── Edgewise_rfp_scrape.py     ← the scraper script
│   ├── Edgewise_config.js         ← GitHub token and passphrase (keep private)
│   └── Edgewise_README.md         ← this document
└── .github/
    └── workflows/
        ├── scrape.yml                    ← existing jobs scraper (don't touch)
        └── Edgewise_rfp_scrape.yml       ← RFP scraper schedule
```

Note the dot at the start of `.github` - that's a hidden folder. GitHub knows to look in there automatically.

## Privacy and security

- The page is `noindex` (Google won't list it).
- It is excluded from `sitemap.xml`.
- It is not linked from any public page on the consultancy site.
- It is not a secret either - if someone has the URL, they can see it. The GitHub token lives in `Edgewise_config.js`, which is a separate file loaded at runtime. The token is scoped to read/write only this repo's contents and trigger this one workflow - so the worst-case impact of a leak is contained.
- Treat the URL, the token, and the passphrase as moderately private (don't post on LinkedIn, do feel free to share with Edgewise staff).
- Never reproduce the token or passphrase in any document, chat, or file. If asked for them, point to `Edgewise_config.js`.
- If you suspect the URL or token has leaked outside Ashley/Kyla/Liam, follow the token-rotation steps in the maintenance section.

## Cost

- GitHub Actions: free tier covers this many times over (~150 minutes per month used; free tier is 2000+ minutes).
- GitHub Pages hosting: free.
- Total ongoing cost: **£0**.

## What this system isn't

- Not a bid management tool. It tells you what's out there - it doesn't help you write or submit proposals.
- Not real-time. The schedule is once a day, although you can hit "Run scrape now" any time.
- Not exhaustive. We scrape 25 of the ~60 portals on Edgewise's tracker. The rest are auth-walled or have no listings page; they're shown as quick-link tiles for manual browsing.
- Not a replacement for the Gemini Scout. The Gemini approach is broader (it can interpret context, follow news, find tenders without keyword matches) but unreliable. The two complement each other - the scraper is the systematic dragnet, Gemini catches the things that don't fit a keyword.

## Questions for an LLM

If Ashley or Kyla pastes this document and any of the project files into an AI assistant, here are common questions and the right answers:

**Q: How do I add a new portal to scrape?**
A: Open `edgewise/Edgewise_rfp_scrape.py`. Copy one of the existing simple `scrape_xxx()` functions (like `scrape_imo` or `scrape_nunavut`) as a template. Change the URL constant, source name, and entity. Add the function name to the `SCRAPERS` list at the bottom of the file. Add the source string to the `SCRAPER_SOURCES` set. Test by running the scraper manually via the "Run scrape now" button on the page.

**Q: I want the scrape to run twice a day, not once.**
A: Open `.github/workflows/Edgewise_rfp_scrape.yml`. Change the cron line. Two cron entries:
```
- cron: '30 10 * * *'
- cron: '30 22 * * *'
```
will run at 10:30 and 22:30 UTC.

**Q: I want to scrape my own custom search keyword.**
A: Don't edit any code - use the in-page editor. Open the tracker, scroll to "Filter Criteria", click "Unlock editing", enter the passphrase (in `Edgewise_config.js`), type your new word into the input box under "Marine include keywords" and press Enter, click "Save changes". Hit "Run scrape now" if you want to apply it immediately.

**Q: The page shows old data even after a scrape.**
A: Hard-refresh the browser (Ctrl+Shift+R on Windows, Cmd+Shift+R on Mac). GitHub Pages caches aggressively.

**Q: I've forgotten the passphrase.**
A: It's in `Edgewise_config.js` in the repo. Open that file in the GitHub web editor to find it. Do not share it outside of Ashley, Kyla, and Liam.

**Q: I want to make the page public (linked from the main site).**
A: Don't recommend it - the page loads `Edgewise_config.js` which contains the GitHub token. If you really want it public, the token must be removed first (which means losing the in-page editing and run-now button), then remove the `<meta name="robots" content="noindex, nofollow">` line, add the page to `sitemap.xml`, and add a link from your nav. But strongly suggest keeping it private.

**Q: Can the scraper send me an email when there are new tenders?**
A: Not currently, but it's straightforward to add. The scraper would compare today's results against yesterday's and email a summary if anything new is in the "due in 7 days" bucket. Ask Liam.

**Q: A scraper for portal X has been returning 0 results for several days.**
A: Either the portal has redesigned its HTML (most common) or it has gone down or moved. Open the portal in a browser. If it's loading fine but our scraper returns 0, the HTML structure has changed. Open `edgewise/Edgewise_rfp_scrape.py`, find the `scrape_xxx()` function for that portal, and update the link-pattern regex inside it. Send the function and the new portal HTML to an LLM and ask "update this scraper to match the new HTML".

**Q: Save changes button gave me an error.**
A: Most likely the GitHub token has expired (it's set to renew annually). Follow the "Annual: GitHub token rotation" steps in the maintenance section above.

**Q: How do I delete a tender?**
A: Click the faint **×** button on the left side of that tender's row in the table. Confirm the deletion. If prompted about a keyword, only agree to remove it if you're confident you don't want similar tenders in future.

## Maintainer contact

Liam Pearson-Noseworthy (site owner) - via the Edgewise team channel.

If you need to extend or rebuild this system, the six files you need are: `Edgewise_rfps.html`, `Edgewise_rfps.json`, `Edgewise_filters.json`, `Edgewise_rfp_scrape.py`, `Edgewise_config.js`, and `.github/workflows/Edgewise_rfp_scrape.yml`. Together they're roughly 5,000 lines, mostly comments. Self-contained, no databases, no servers - just static files on GitHub Pages and a Python script run by GitHub Actions once a day.
