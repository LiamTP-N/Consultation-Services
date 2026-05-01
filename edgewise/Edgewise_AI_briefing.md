# Edgewise RFP Tracker - AI Briefing Document

> **What this document is:** a complete, self-contained briefing on the Edgewise Environmental RFP / tender tracker system. It exists so that Kyla Graham (Senior Marine Biologist / Consulting Lead at Edgewise) can paste it into an AI assistant (ChatGPT, Claude, Gemini, etc.) and then ask questions about how the system works, why certain tenders did or didn't show up, what would happen if she changed a keyword, and so on.
>
> **Intended audience:** the AI assistant Kyla is talking to. Not Kyla directly. Kyla isn't expected to read this top-to-bottom. She'll paste it in and start asking questions.
>
> **What this document is not:** code. There's no Python or JavaScript here. Anything code-level is described in plain English so the AI has enough context to explain things back to Kyla without trying to make her edit anything.

---

## INSTRUCTIONS FOR THE AI ASSISTANT

You are helping Kyla Graham understand a tender-tracking system that her colleague Liam Pearson-Noseworthy built for Edgewise Environmental Ltd. Kyla is a senior marine biologist and consulting lead - she is the **user** of the system, not the maintainer. Liam is the maintainer.

Follow these rules in every response:

1. **Keep explanations non-technical.** Kyla is technically capable but doesn't write code, doesn't use the command line, and edits files via GitHub's web interface only when she has to. If a question requires explaining something code-level, describe what the code does in plain English. Never paste code at her.

2. **Frame answers in terms of action, not implementation.** Instead of "you'd need to modify the regex on line 482 of the scraper", say "this would be a small change Liam can make - it'd take him about five minutes." When the answer is "ask Liam," say so plainly.

3. **Be concrete.** If she asks "why didn't this tender appear?" walk through the actual filter logic step by step against the actual tender, naming which rule fired or didn't, and what the practical fix would be (add this green keyword / add this red keyword / accept that the source isn't being scraped / etc.).

4. **Never reproduce the GitHub token or passphrase.** They live in a file called `Edgewise_config.js`. If she asks where they are, say "in `Edgewise_config.js` in the repo - open it via GitHub's web editor." Don't speculate at the values.

5. **Help her formulate sharper feedback to Liam.** A big part of why this document exists is so Kyla can pre-validate her thinking before emailing him. If a question reveals the underlying issue is unambiguous (e.g. "we're missing US tenders because we don't scrape any US portals beyond SAM.gov, and SAM.gov needs a paid API key for full coverage"), say so, and frame it as "the question to ask Liam is X" rather than just answering the surface question.

6. **Use British English** (matches the system's house style). Hyphens, not em dashes.

7. **If you don't know, say so.** This document is comprehensive but not exhaustive. If Kyla asks something this brief doesn't cover, the right answer is "I'd ask Liam directly - this isn't something the briefing covers."

---

## 1. WHAT THE SYSTEM DOES, IN ONE PARAGRAPH

Every morning at 10:30 UTC (around 8 a.m. Newfoundland time), a Python script wakes up on GitHub's servers, visits 24 public procurement websites, downloads every tender notice they're publishing, filters that mass of tenders down to the ones that look genuinely relevant to Edgewise's marine environmental consultancy work (MMO, PAM, seabird surveys, offshore wind monitoring, oil spill response, marine mammal research, etc.), and writes the survivors to a JSON file. A web page reads that JSON file and shows the tenders in a sortable, filterable table at a private URL. Kyla and Ashley visit the page, see what's new, and decide what to chase. Total cost: zero. Total user effort: bookmark the page.

---

## 2. WHO IS WHO

- **Ashley Noseworthy** - President and CEO of Edgewise Environmental. Liam's wife. Edgewise is hers; she sets the strategic direction.
- **Kyla Graham** - Senior Marine Biologist and Consulting Lead at Edgewise. She is the day-to-day user of the tracker. She knows marine science deeply but doesn't code.
- **Liam Pearson-Noseworthy** - Ashley's husband. Built the tracker as a favour. He's the only maintainer. When something breaks or needs extending, Kyla emails him.
- **You (the AI)** - Kyla's sounding board. Your job is to help her understand what's happening so her conversations with Liam are sharper and more useful.

---

## 3. THE PUBLIC URL

The tracker lives at:

```
https://liamtp-n.github.io/Consultation-Services/edgewise/Edgewise_rfps.html
```

It is **private by convention, not by login.** Anyone with the link can see it, but: it's not indexed by Google, it's not linked from any public site, and it has a `noindex, nofollow` tag in the HTML. The URL should be treated as semi-confidential. Don't post it on LinkedIn, do feel free to share with Edgewise staff.

A small piece of the page (editing keywords, deleting tenders, manually adding tenders, triggering an immediate scrape) is gated behind a passphrase, which is just a soft lock to prevent accidental clicks. The passphrase is stored in `Edgewise_config.js` along with a GitHub access token. Neither of those values should ever be reproduced in conversation - if Kyla needs them she opens that file in GitHub's web editor.

---

## 4. THE SIX FILES THAT MAKE UP THE SYSTEM

Everything lives in a GitHub repository called `Consultation-Services`, inside an `edgewise/` subfolder. The six files are:

| File | What it is |
| --- | --- |
| `Edgewise_rfps.html` | The web page Kyla looks at. Loads the JSON, renders the table, handles all interactivity (filtering, sorting, search, the keyword editor, the manual-add panel, the delete buttons, the run-scrape button). |
| `Edgewise_rfps.json` | The data. Two arrays inside it: `rfps` (tenders found, scraped or manual) and `portals` (the static list of quick-link tiles at the bottom of the page). |
| `Edgewise_filters.json` | The four keyword lists that drive what gets kept and what gets dropped during scraping. Edited via the in-page keyword editor (or directly via GitHub). |
| `Edgewise_rfp_scrape.py` | The Python script that runs daily on GitHub Actions. Pulls every source, filters them, writes the JSON. ~2,200 lines, mostly comments. |
| `Edgewise_config.js` | Holds the GitHub access token and the passphrase. Loaded by the HTML page at runtime. **Sensitive. Never reproduce its contents.** |
| `Edgewise_README.md` | Plain-English handover document for the system. Kyla has access to it; this AI briefing is a more user-focused version. |

There's also a workflow file at `.github/workflows/Edgewise_rfp_scrape.yml` which tells GitHub *when* to run the scraper (10:30 UTC daily) and *what command to run* (the Python script). Kyla shouldn't need to touch this.

---

## 5. HOW THE FILTER ACTUALLY DECIDES WHAT TO KEEP

This is the most important section to understand. Almost every "why didn't tender X appear?" question comes down to filter logic.

For each tender pulled from a source portal, the filter checks three rules **in order**:

### Rule 1 - HARD REJECT (run first, wins everything else)

If the tender's title, summary, entity name or tags contain **any** keyword from the EXCLUDE list, the tender is dropped immediately. No appeal. This is the "clearly not for us" filter.

There are currently around **207 exclude keywords**. Examples: `janitorial`, `office furniture`, `paving`, `kitchen construction`, `roofing`, `hazmat`, `IT support`, `software licence`, `prison`, `helicopter`, `electric vehicle supply`, `aerial photography`, `building materials`. The full list is in section 12.

**Important quirk:** the exclude list is a substring match. If the exclude list contains `training`, then ANY tender mentioning training (even a perfectly relevant marine mammal observer training tender) would be killed. So the exclude list is hand-curated to avoid words that overlap with legitimate marine work.

### Rule 2 - GREEN KEYWORD MATCH

If the tender survives the exclude filter and contains **any** keyword from the MARINE_KEYWORDS (green) list anywhere in its title, summary, entity name or tags, it is kept.

There are currently around **188 green keywords.** They cover: marine fauna observation (`marine mammal`, `MMO`, `seabird observer`, `PSO`), acoustics (`PAM`, `passive acoustic`, `underwater noise`, `hydroacoustic`), surveys (`marine geophysical`, `benthic survey`, `vessel-based survey`), environmental assessments (`EIA`, `EEM`, `environmental baseline`), Edgewise's target sectors (`offshore wind`, `tidal energy`, `decommissioning`, `metocean`), specific service lines (`oil spill`, `oiled wildlife`, `marine spatial planning`, `MPA`), and some geography-specific terms (`Grand Banks`, `Hibernia`, `ScotWind`, `Beaufort Sea`, `Inuvialuit`).

**Critical quirk: short acronyms have padded spaces.** The list contains `" mmo "` (with spaces) rather than `"mmo"`, because otherwise it would match the `mmo` inside words like `accommodation`. This is also why some keywords look strange. They're meant to.

### Rule 3 - CPV / UNSPSC CODE WITH MARINE CONTEXT

This is the trickiest rule. If the tender survives the exclude filter, doesn't match any green keyword directly, but **does** carry a tracked procurement category code (Canadian UNSPSC or EU CPV), AND ALSO contains at least one MARINE_CONTEXT word, it is kept.

The reason for this rule: some tenders are tagged with very specific category codes (e.g. CPV 71351923 = "bathymetric surveying services") that strongly imply marine relevance even if the title is generic. But we don't want to keep every tender with an environmental code, so we gate it: the tender also has to mention `marine`, `ocean`, `coastal`, `offshore`, `vessel`, `whale`, `harbour` or similar.

There are currently **39 tracked codes** and **81 marine context words.**

### Rule 4 (implicit) - DROP

If a tender doesn't trigger any of the three rules above, it's dropped.

### What this means in practice

- Adding more **green** keywords lets MORE tenders through. If we're missing things, this is what to widen.
- Adding more **red** (exclude) keywords filters MORE noise out. If we're getting irrelevant rubbish, this is what to widen.
- Adding **CPV codes** only matters for sources that actually tag tenders with these codes (mostly Canadian and European; barely the US, never the bilateral aid sources).
- Adding **marine context words** only matters if there's also a relevant CPV code; on its own it does nothing.

---

## 6. THE 24 SOURCES (AND WHY EACH IS THERE)

The scraper visits 25 sources, all currently active. SPREP (which used to block automated scrapers) is now reached via a headless browser, and Nunavut is now reached via the `nunavuttenders.ca` mirror which doesn't have Cloudflare in front of it.

### Auto-scraped (25 active)

| Source | Type | Region | Why it's there |
| --- | --- | --- | --- |
| **CanadaBuys** | Open data CSV | Federal Canada | Catches every federal Canadian tender. Highest single-source yield. |
| **UK Find a Tender** | OCDS JSON API | UK above-threshold | UK contracts >~£139k. Catches Crown Estate, Defra, Cefas, MMO, JNCC. |
| **UK Contracts Finder** | OCDS JSON API | UK below-threshold | UK contracts under that threshold. Smaller-value but often more relevant for boutique consultancy. |
| **TED (EU)** | JSON API | EU + EEA | The EU's official journal for procurement. Catches Irish, Norwegian, Dutch, German, Belgian offshore wind and marine tenders. |
| **SAM.gov** | JSON API | USA | US federal procurement. BOEM, NOAA, USACE, NSF post here. Currently uses the free DEMO_KEY which limits us to ~30 requests/hour - usable but coarse. |
| **PCS Scotland** | RSS feeds | Scotland | Crown Estate Scotland posts ALL its tenders here. NatureScot, Marine Scotland. ScotWind work. |
| **NBON** | HTML scrape | New Brunswick | NB Power, DNRED Fisheries, Bay of Fundy, Saint John Harbour. |
| **GNWT** | HTML scrape | Northwest Territories | Inuvialuit Settlement Region, Beaufort Sea, NWT Power Corp. |
| **SEAO Quebec** | Open-data JSON | Quebec | Hydro-Québec, MELCCFP, Gulf of St. Lawrence municipalities. French-language. |
| **eTenders Ireland** | OCDS JSON | Ireland | Marine Institute Ireland, MARA (the new offshore wind regulator), NPWS, Inland Fisheries Ireland. |
| **Sell2Wales** | RSS feeds | Wales | NRW, Welsh Government Marine Directorate. Celtic Sea floating wind. |
| **Asian Development Bank** | HTML scrape | Asia-Pacific | Pacific island marine work, fisheries projects, coastal climate adaptation. |
| **African Development Bank** | HTML scrape | Africa | West/East African coastal climate-adaptation studies. |
| **UN Global Marketplace (UNGM)** | POST + HTML | International (UN system) | 54 UN bodies post here: UNDP, UNEP, UNOPS, FAO, WFP, WHO, UNICEF, UNHCR, IMO, IAEA, UNFCCC, etc. The page is JavaScript-rendered, but the AJAX search endpoint is reachable directly, so we POST to it and parse the HTML fragments it returns. |
| **World Bank** | JSON API | Global | Multilateral, mostly developing-country marine work. |
| **IMO** | HTML scrape | Maritime | International Maritime Organisation's own tenders. |
| **Caribbean Development Bank** | HTML scrape | Caribbean | Caribbean coastal/marine work. |
| **BC Bid** | HTML scrape | BC | British Columbia public sector, including BC Hydro, all on this one platform. |
| **NL Hydro** | HTML scrape | Newfoundland | Provincial utility, Labrador Sea-adjacent. |
| **Nova Scotia Procurement** | HTML scrape | Nova Scotia | Provincial portal. Bay of Fundy work appears here. |
| **BC Ferries** | HTML scrape | BC | Marine vessel operator. |
| **LNG Canada** | HTML scrape | BC | Kitimat LNG terminal, marine environmental work around it. |
| **MERX (NL)** | HTML scrape | Newfoundland | Newfoundland provincial tenders. |
| **SPREP** | Playwright (headless Chromium) | Pacific | Pacific Regional Environment Programme. The site actively blocked plain HTTP scrapers, so this one runs a real headless browser to render the page first, then parses it. Low volume (~2-5 marine-relevant per year) but directly on-priority for Pacific seabird/marine work. |
| **Nunavut Tenders** | HTML scrape | Arctic | Government of Nunavut tenders via `nunavuttenders.ca`. The official portal at gov.nu.ca is Cloudflare-protected, but this mirror serves the same data without bot protection. Captures GN environmental services, wildlife surveys, marine infrastructure, Arctic logistics. |

### Why "we don't crawl the wider internet"

The scraper does NOT do general web search. It only visits the 25 specific portals above. If a tender is published exclusively on `developmentaid.org` or `tenders.net` or some other aggregator that isn't in our list, the scraper will not find it. This is deliberate:

1. General tender aggregators are full of duplicates, scams, paywalls and out-of-date listings. Filtering them reliably is hard.
2. Scraping them at scale would make us look like a bot and get us blocked.
3. The portals we DO scrape are, between them, the actual original publishers - so most legitimate tenders appear in our list eventually anyway, just via the original portal rather than the aggregator.

The Gemini scout that Kyla also runs is the right complement here: it's broader (LLM-driven, can read context, can find things outside our keyword list) but unreliable (hallucinates, misses details, can't be trusted to be exhaustive). The two systems together cover more ground than either alone.

DevelopmentAid and Tenders.net are still listed in the portal directory at the bottom of the page as quick-link tiles, so Kyla can manually check them with one click whenever she wants.

---

## 7. HOW THE PAGE WORKS, FEATURE BY FEATURE

When Kyla opens the URL, she sees:

### Top stats card (4 tiles)

- **Total Tracked** - count of all tenders currently in the JSON.
- **Open Now** - count of tenders with status `open`, `watching`, `bidding` or `submitted`.
- **Due in 7 Days** - count of open tenders whose closing date is within a week.
- **Last Scraped** - timestamp of the most recent successful scrape, plus a green "Run scrape now" button that triggers an immediate refresh (takes 2-3 minutes).

### Filter rows

- **Status row:** Active / Open / Watching / Bidding / Submitted / Closed-Lost-Won / All.
- **Region row:** All / Canada / USA / UK / EU / Pacific / Arctic / Caribbean / Asia / Africa.
- **Source dropdown:** every source name that appears in the data, dynamically populated.
- **Search box:** matches title, entity, region, summary and tags.

### Main results table

Five columns: Project (with a small region badge and a faint X delete button on the left), Entity, Source, Status, Due date. Sortable by clicking column headers. Clicking a row opens a detail panel with the full description, why-this-fits explanation, notes, tags, and a button to open the original tender notice.

### Per-row delete

The faint X on the left side of every row deletes that tender from the tracker. If the tender was found via a green keyword, a second prompt asks whether to ALSO remove that keyword from the filter (so similar tenders won't appear in future). This is the fastest way to teach the filter what's noise.

### Add tender manually (collapsible panel)

For tenders the scraper missed (e.g. spotted somewhere we don't currently cover, or pointed out by a colleague). Requires the passphrase. Fields: project title, entity, region, link, due date, reference, source, status, summary, notes. Saves directly to the JSON. The scraper preserves manually-added entries across runs (it only refreshes things it scraped itself).

### Filter Criteria panel (collapsible)

Shows all four keyword lists, colour-coded by purpose. Each keyword displays as a coloured pill. After unlocking with the passphrase, every pill gets a clickable X for removal, and each list gets an input box where new keywords can be added by typing and pressing Enter. Save commits the changes; "Run scrape now" applies them immediately, otherwise they take effect on the next daily run.

### Procurement Portals panel (collapsible)

Quick-link tiles for ALL the portals Edgewise tracks, including the auth-walled ones the scraper can't reach (SAP Ariba, Equinor, Ørsted, ABCMI, etc.) and the manual-check ones (DevelopmentAid, Tenders.net). Grouped into four sections: auto-scraped, bot-protected, no-listings-page, login-required. A 🚫 icon means the site blocks automation; a 🔒 means it needs a login.

---

## 8. THE STATUS LIFECYCLE OF A TENDER

When a tender is first scraped, its status is `open`. From there, Kyla can change it to track her progress:

| Status | Meaning |
| --- | --- |
| `open` | Default. Just appeared, no decision yet. |
| `watching` | Interesting, no action yet. Want it to stay visible. |
| `bidding` | We're working on a proposal for it. |
| `submitted` | Proposal sent, waiting for outcome. |
| `won` | We got it. |
| `lost` | We didn't get it. |
| `closed` | Withdrawn by buyer, or otherwise no longer relevant. |

To change a status, Kyla either edits the JSON directly via GitHub's web editor (find the tender by its title, change the `status` value, commit), or future versions of the page will likely add an in-page status dropdown. The scraper preserves manual status changes across runs - if she sets a tender to `bidding` today, tomorrow's scrape doesn't reset it to `open`.

Tenders with a closing date more than 90 days in the past are automatically pruned from the JSON. This is the "archive window" - effectively, anything closed within the last three months is still visible under the Closed/Lost/Won filter.

---

## 9. WHY A TENDER MIGHT NOT APPEAR (DIAGNOSTIC CHECKLIST)

When Kyla notices a tender she expected to see, this is the order in which to walk through possibilities:

1. **Is the tender on a portal we scrape at all?** Check the source. If it's only on, say, the DevelopmentAid aggregator and nowhere else, we won't see it. (DevelopmentAid usually mirrors stuff from primary portals, so the same tender often appears via a primary portal a day or two later.)
2. **Was it published more than the lookback window allows?** UK Find a Tender, UK Contracts Finder, TED, and SAM.gov scrapers each look at the last 14 days of postings. Older tenders won't be picked up, even if still open for bidding. (CanadaBuys is different - it provides a "currently open" snapshot regardless of publication date.)
3. **Did an EXCLUDE keyword kill it?** Read the title and summary. Cross-reference against the exclude list (section 12). If a word like `training` or `consulting` matched, that's the killer.
4. **Did NO green keyword match?** This is the most common cause for relevant-but-missed tenders. The fix is to add a new green keyword that captures the missing terminology.
5. **Did it match via the CPV-with-context rule, but lack a marine context word?** Less common. Indicates the tender used a tracked code but described itself in language that doesn't mention any marine/coastal/vessel terminology. Adding to the marine_context_words list helps.
6. **Did the scraper for that source fail that day?** Less common. Visible in the GitHub Actions logs. Liam can check.

The standard recipe for a "why didn't this appear?" question to Liam is:

> Here's a tender link: [URL]. It closes [date], it's about [subject]. I'd expect this to appear because [reason]. Could you check whether the [source] scraper saw it, and if so, why it was filtered out?

---

## 10. WHY THE GENERAL US REGION FEELS EMPTY

A separate diagnostic worth flagging because it comes up:

- The only US source we currently scrape is SAM.gov.
- SAM.gov is being scraped successfully but uses a free `DEMO_KEY` which has rate limits.
- Most US federal procurement is buried under non-marine NAICS codes that don't immediately match our marine green keywords without help.
- BOEM, NOAA Fisheries and USACE all post on SAM.gov, but their tender titles often use bureaucratic shorthand (`OCS-A 0540`, `Atlantic OCS lease environmental`, etc.) that the green keyword list isn't tuned for yet.

So "the US filter is empty" is usually NOT a bug - it's the system correctly reporting that nothing US-side passed the marine filter that day. The fix isn't a code change; it's adding US-specific terminology (`BOEM`, `NMFS`, `OCS-A`, `incidental harassment authorization`, `IHA`, `MMPA`, `BiOp`) to the green keyword list. Several of these are already in there, but it's worth a deliberate review pass once Edgewise actually registers as a SAM.gov supplier and Ashley/Kyla decide US work is on the table.

---

## 11. THE PORTAL DIRECTORY (NON-SCRAPED PORTALS)

Beyond the 24 scraped sources, the page lists ~40 other portals that Edgewise tracks but that the scraper cannot reach. These are shown as quick-link tiles at the bottom of the page. Examples:

- **SAP Ariba** - terms of use forbid automation. Login: `ashley@edgewiseenvironmental.com`.
- **Equinor / Ørsted / RWE / Vattenfall / SSE Renewables** - oil & gas and offshore wind operator portals. Most require Achilles FPAL/JQS pre-qualification.
- **Achilles FPAL/JQS** - the oil and gas industry's pre-qualification gateway. Edgewise registering here would unlock visibility to most North Sea and Atlantic Canada operators.
- **C-NLOPB** - Canada-Newfoundland and Labrador Offshore Petroleum Board. Regulatory body; flags upcoming work but isn't a tender portal itself.
- **IAAC** (Impact Assessment Agency of Canada) - registry of federal impact assessments. Read-only signal source.
- **EnergyNL, ABCMI, NLOWE, Marine Renewables Canada, EnergiCoast** - industry associations, members-only.
- **DevelopmentAid, Tenders.net** - aggregators; manual check only.

Each tile in the portal directory has hover-text notes explaining what it covers and why we're not scraping it.

---

## 12. THE FULL CURRENT FILTER LISTS

Pasting these in so the AI can answer specific keyword questions without guessing.

### Marine include keywords (green) - ~188 entries

```
marine mammal, mmo, mmso, marine mammal observer, seabird, sea bird, sbo,
seabird observer, protected species observer, pso, marine fauna, marine wildlife,
passive acoustic, pam, pam operator, pam-, acoustic monitoring, acoustic mitigation,
bioacoustic, underwater noise, underwater radiated noise, urn, anthropogenic noise,
noise mitigation, noise impact, noise modelling, noise modeling,
sound source verification, ssv, sound source characterisation, sound source characterization,
hydroacoustic, hydroacoustics, seismic survey, marine geophysical, marine geotechnical,
marine survey, underwater survey, subsea cable, marine baseline, marine monitoring,
environmental effects monitoring, eem, marine ecology, marine conservation,
environmental baseline, benthic survey, benthic habitat,
vessel-based survey, vessel based survey,
offshore wind, marine renewable, tidal energy, wave energy, subsea, ocean energy,
blue economy, offshore oil, offshore gas, offshore environmental, decommissioning,
metocean, site characterisation, site characterization,
abandoned vessel, abandoned boat, vessel assessment,
oil spill, spill response, emergency environmental response,
bird handling, oiled wildlife, marine ornithology, marine ornithologist,
marine spatial planning, marine protected area, mpa,
species at risk, sara, right whale, north atlantic right whale, narw,
incidental take, marine licence, marine license,
habitats regulations assessment, hra, crown estate, boem, noaa fisheries,
aquaculture environmental, mariculture, dredging, capital dredging,
joint nature conservation, jncc, cefas, eia,
grand banks, flemish pass, flemish cap, jeanne d'arc basin, orphan basin,
labrador sea, hibernia field, hebron field, white rose, terra nova field,
bay du nord, c-nlopb, scotwind, intog, celtic sea floating wind,
floating offshore wind, flow, crown estate leasing, wind energy area,
ecological clerk of works, ecow, marine mammal mitigation, soft start monitoring,
exclusion zone monitoring, jncc guidelines, jncc-approved,
cetacean survey, cetacean monitoring, pinniped survey,
harbour porpoise, harbor porpoise, minke whale, humpback whale,
static acoustic monitoring, digital aerial survey,
line transect survey, distance sampling,
incidental harassment authorization, iha, marine mammal protection act,
baci study, before-after-control-impact, benthic grab, drop-down video,
seabed habitat survey, habitat mapping, biotope mapping,
epifauna survey, infauna survey, marine licence application,
development consent order, scoping report,
preliminary environmental information, peir, appropriate assessment,
offshore substation, geophysical survey, geotechnical survey, uxo survey,
sub-bottom profiler, multibeam survey, side-scan sonar,
oil spill response, shoreline cleanup, scat,
derelict vessel, wreck assessment, ice observer,
inuit impact benefit, iiba, nunavut impact review, nirb,
inuvialuit, nunatsiavut, beaufort sea, davis strait, baffin bay,
hudson bay, hudson strait, lancaster sound, tallurutiup imanga,
oecm, nmca monitoring, fisheries observer, at-sea observer,
stranding response, marine mammal stranding,
norwegian continental shelf, barents sea, boem pso
```

### Procurement category codes (CPV / UNSPSC) - 39 entries

Canadian UNSPSC codes:
```
70101602 (wildlife studies), 70101601 (animal preservation),
70101604 (habitat conservation), 70100000 (forestry/fisheries/wildlife mgmt),
77101500 (environmental management),
70141600 (wildlife protection), 70141700 (wildlife management),
70171600 (oceanography), 70171700 (marine biology),
70171800 (aquatic environmental impact), 70171900 (habitat assessment),
77101600 (env advisory), 77101700 (env planning), 77102000 (env monitoring),
81141600 (acoustical engineering), 81161800 (aquatic ecology)
```

EU CPV codes:
```
90711000 (EIA), 90712000 (env planning), 90713000 (env consultancy),
90720000 (env protection), 73111000 (research lab), 73210000 (research consultancy),
71351000 (geological/geophysical/prospecting), 71351900 (geological survey),
71351923 (bathymetric survey), 71351924 (hydrographic survey),
90711100 (risk/hazard), 90711200 (env standards), 90711400 (EIA services),
90712400 (nature resource conservation), 90714000 (env auditing),
90715000 (pollution investigation), 90721000 (env protection services),
71313400 (env engineering), 71313440 (EIA for construction),
71313450 (env monitoring non-construction),
92534000 (wildlife preservation services), 98363000 (diving services),
76400000 (positioning for oil and gas)
```

### Marine context words - ~81 entries

```
marine, ocean, oceanic, vessel, vessels, subsea, underwater, offshore,
whale, dolphin, porpoise, cetacean, pinniped, seal, walrus,
narwhal, beluga, bowhead, seabird, sea bird, fish,
coastal, estuarine, intertidal, nearshore, inshore, foreshore, shoreline,
harbour, harbor, port, wharf, jetty, bay, inlet, fjord,
shipping, maritime, hydrographic, bathymetric, acoustic,
spill, oil spill, water sampling, water column,
benthic, pelagic, reef, shelf, continental shelf,
tidal, tide, tidewater, dredge, dredging, aquaculture, mariculture,
arctic, subarctic, sub-arctic, ice, sea ice, pack ice, icebreaker, polar,
newfoundland, labrador, grand banks, north sea, irish sea, celtic sea,
hebrides, moray firth, dogger bank, beaufort, inuvialuit, baffin,
gulf of st. lawrence, bay of fundy, norway, norwegian
```

### Exclude keywords (red) - ~207 entries

Categorised for readability but stored as one flat list:

**Generic facilities:** janitorial, cleaning service, catering, food service, stationery, office supplies, printer toner, uniform, laundry, office furniture, pest control, snow removal, landscaping, lawn maintenance, silviculture, grass cutting, vehicle rental, fuel supply, translation service, interpreter, medical supplies, pharmaceutical.

**IT and digital:** IT support, software licence, software license, legal software, legal solution, case management software, software solution, im/it, im/ it, data centre, cloud service, saas, cyber.

**Construction:** accommodation, accommodations, barracks, housing, bridge replacement, culvert, paving, paving program, chimney replacement, library cooling, cooling tower, roof replacement, roofing, kitchen construction, electrical upgrade, lighting upgrade, plumbing, building materials, domestic appliance, modular bridge, panel bridge.

**Defence/military:** heavy equipment replacement, heavy support equipment, armoured, armored, shipbuilding, shipyard, ground vehicle, uncrewed ground, unmanned ground, military training, role playing, role-playing, parachute instructor, parachutist, signal generator, agile signal, helicopter, polar helicopter, aviation fuel, explosive ordnance, explosive threat, intelligence enterprise, command and control, c4isr, defence intelligence.

**Environmental work that's NOT us:** contaminated site, remediation construction, hazmat, hazardous material, tank assessment, petroleum storage tank, asbestos, topographic lidar, aerial photography, hazardous waste.

**Correctional/health:** correctional service, penitentiary, institution, inmate, offender, healing lodge, detention, rcmp, prison, dental, psychiatric, psychiatry, psychological, physiotherapy, physician service, primary care, dermatology, medical radiation, urinalysis, mental health, exit interview, pre-employment, ribbon, boots-ankle, ankle boot, boot, footwear.

**Furniture/facilities:** furniture for, furniture fixtures, mobile shelving, shelving, alarm system, security management system, perimeter intrusion, perimeter security, elevator, elevating device, hvac, boiler replacement, boiler heating.

**Equipment/tools:** fluke insulation, fluke multimeter, multimeter, insulation meter, cables and wires, wire and cable, backhoe, skid steer, tractor loader, fertilizer, fertiliser, static mixer, electric vehicle supply, evse, buses-electric, electric bus, automated liquid handler, aptamer.

**Misc:** mowing, grounds maintenance, building construction services, airport terminal, terminal renovation, exhibition fit-out, exhibition fit out, teaching & learning, teaching and learning, early years, pre-school, preschool, education provision, early years education, refugee, refugee resettlement, museum, art gallery, cultural heritage, professional audit, task professional services, solutions professional services, tsps, media monitoring, printing service, change management consultant, indigenous artist, indigenous business capacity, sustained action crew, fire suppression, ats replacement, system support, tractor, vessel recycling, proservices method of supply, method of supply, audit and support services, pass rfsa, pass refresh, tspsh, tssb, industry day, loi - industry, article 23, land claims agreement, independent review of.

(For the live list, the page itself is always authoritative.)

---

## 13. THINGS THE TRACKER DOES NOT DO

This is worth being explicit about, because Kyla occasionally asks for things the system isn't designed for.

- **It does not crawl the open web.** Only the 24 configured portals.
- **It does not write proposals.** It tells Kyla what's out there, not how to bid for it.
- **It does not send email alerts** for new tenders. Could be added; isn't there yet.
- **It does not score or rank tenders by likely fit.** Everything that passes the filter is shown equally.
- **It does not access auth-walled portals,** even ones where Edgewise has credentials. SAP Ariba's terms of use forbid automation entirely. Smaller portals (member associations, supplier portals) could in principle be reached with credentials but the legal/ToS situation is murky and the risk-reward isn't worth it.
- **It does not track day-by-day historical state.** A tender is either in the JSON or it isn't. The 90-day post-close retention is the "archive window."
- **It does not deduplicate the same tender appearing on two different portals.** If a UK tender posts on both Find a Tender and TED, it'll appear twice with two different source labels. (Same `id` hash would deduplicate; different platforms generate different reference numbers, so the hashes differ.)

---

## 14. HOW TO MAKE THE TRACKER BETTER (FROM KYLA'S SIDE)

Six things Kyla can do that materially improve the tracker:

1. **Tell Liam about every relevant tender she finds via other means** (email tip-offs, the Gemini scout, manual portal browsing). Each one is a free training data point. If it should have appeared in the tracker but didn't, Liam can diagnose why and tune the filter.

2. **Use the per-row delete button on irrelevant tenders.** When the prompt asks "remove the keyword that brought this in?", say yes if the keyword is genuinely producing noise. This actively trains the filter.

3. **Add green keywords for terminology she knows but the filter doesn't.** Sub-fields evolve - new acronyms appear, regulators rebrand. The keyword editor is one click away.

4. **Add red keywords when she sees the same kind of irrelevant tender appearing repeatedly.** A single instance is fine; a pattern is worth excluding.

5. **Send Liam links to tenders she's currently bidding on.** This lets him sanity-check that the tracker is picking them up, and use them as positive examples when tuning.

6. **Tell Liam when a portal's results stop showing up entirely** - that usually means the source has redesigned its website and the scraper for that one source has broken. Easy fix, but Liam needs to know.

---

## 15. EXAMPLE QUESTIONS KYLA MIGHT ASK YOU

Examples of useful prompts she could give the AI assistant after pasting this document. The AI doesn't need to wait for these specific questions; they're illustrative of the kind of help that's valuable:

- *"Here's a tender link [URL]. It should have appeared in the tracker but didn't. Walk me through why."*
- *"I keep seeing tenders for [X] in the tracker that aren't relevant. What red keyword should I add, and is there any risk it'll filter out something legitimate?"*
- *"Should I add the keyword [X] to the green list? Will it cause noise?"*
- *"What's the difference between CPV codes and UNSPSC codes, and why does it matter for the tracker?"*
- *"The Cefas Sri Lanka tender appeared after Liam widened the lookback window from 7 to 14 days. Are there other tenders we might have been missing for the same reason? How would I check?"*
- *"I want to start tracking tenders in [region we don't cover]. What would Liam need to do to add a portal for that?"*
- *"Translate this email I'm about to send Liam into something more specific and useful: [paste email]."*
- *"I'm about to bid on this tender: [URL]. Will the tracker still show it next week if I change its status to `bidding`, or will the scraper overwrite my changes?"* (Answer: it'll preserve the status change.)
- *"Why is the US region empty when I select it?"*
- *"The Gemini scout flagged these five tenders. Cross-reference them against the tracker logic and tell me which ones the keyword filter would have caught and which ones it would have missed - and for the misses, what keyword would have helped."*

The last one is particularly valuable - it's exactly the kind of training-data exercise Liam will want her to do.

---

## 16. WHAT TO TELL LIAM, AND WHEN

Quick reference for "I've noticed something - is this an email-Liam moment or a fix-it-myself moment?":

| Situation | Fix it herself | Email Liam |
| --- | --- | --- |
| A keyword needs adding/removing | ✅ via the in-page editor | only if she's unsure of the impact |
| A specific tender needs deleting | ✅ via the X button | no |
| A specific tender needs adding manually | ✅ via the manual-add panel | no |
| The tracker is showing zero results everywhere | no | ✅ (probably the scraper broke) |
| One specific source has stopped returning anything | no | ✅ (that source's scraper probably broke after a redesign) |
| She wants to add a NEW source that isn't in the 24 | no | ✅ |
| She wants email alerts | no | ✅ |
| She wants to change the daily run time | no | ✅ |
| The "Run scrape now" button gives an error | no | ✅ (probably the GitHub access token has expired) |
| The "Save changes" button gives an error in the keyword editor | no | ✅ (same reason) |
| She wants to change a tender's status from `open` to `bidding` etc. | ✅ (via GitHub web editor) | no, but she could ask for an in-page status dropdown if the GitHub edit feels clunky |
| She forgot the passphrase | ✅ (it's in `Edgewise_config.js`) | only if she can't open that file |

---

## 17. CLOSING NOTE TO THE AI

The single most useful thing you can do for Kyla is help her ask Liam **better questions.** A question like *"the tracker isn't working"* is useless; a question like *"the Cefas Sri Lanka tender was published on [date] but didn't appear - was the OCDS lookback window the issue, and if so, can we extend it permanently or just for high-priority portals?"* is gold.

When she asks you something, ask yourself: "what would the ideal email to Liam about this look like?" and steer her there.

If she asks something this document doesn't cover, say so honestly - "the briefing doesn't get into that level of detail; you'd need to ask Liam directly" is a perfectly fine answer. Do not invent details about how the system works.

End of briefing.
