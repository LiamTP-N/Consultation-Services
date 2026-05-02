# Dr. Liam T. Pearson-Noseworthy - Personal Professional Website

**Live site:** [liamtp-n.github.io/Consultation-Services/](https://liamtp-n.github.io/Consultation-Services/)  
**Hosting:** GitHub Pages (static only - no server-side code)  
**Deployment:** GitHub Desktop  
**Stack:** Vanilla HTML/CSS/JS · Tailwind CSS via CDN · Firebase/Firestore · Google Apps Script

---

## Repository structure

```
/
├── index.html              Homepage
├── portfolio.html          Research & project portfolio
├── cv.html                 Academic CV (with print stylesheet)
├── services.html           Consultancy services
├── live-research.html      Active research studies feed
├── jobs.html               Automated job board
├── app.html                ROM-based Exercise (RBE) web app
├── waitlist.html           Redirects to app.html
├── 404.html                Custom 404 page
├── includes.js             Shared nav & footer (injected into all public pages)
├── search-index.json       Client-side site search index (Ctrl+K)
├── sitemap.xml             XML sitemap for search engines
├── robots.txt              Search engine crawl rules
├── manifest.json           PWA manifest
├── sw.js                   Service worker
├── SECURITY.md             Security disclosure policy
├── scrape.py               Daily job scraper script
├── scrape.yml              GitHub Actions workflow for the scraper
│
│   -- Private / personal tools (never in nav, sitemap, or public references) --
├── fitness.html            Boxing timer + gym session tracker (Liam & Ash)
├── crypto.html             Personal cryptocurrency dashboard
├── crypto-widget.html      Minimal crypto widget variant
└── route.html              Driving route comparator (Tyne Tunnel)
```

---

## Public pages

### `index.html` - Homepage
The main landing page. Introduces Liam's professional identity, headline services, and links out to portfolio, CV, and contact. Uses the shared nav/footer pattern via `includes.js`.

### `portfolio.html` - Portfolio
Showcases research projects, publications, and applied work. Organised by topic area. Linked from the main nav.

### `cv.html` - Academic CV
Full academic CV including employment history, qualifications, publications, and editorial roles. Includes a print stylesheet so it renders cleanly when printed or saved as PDF.

### `services.html` - Services
Consultancy services page describing performance and health consulting (athletes, older adults, sport teams, individuals) alongside academic and data services (pipeline engineering, machine learning in R/Python, systematic review support, ad hoc consultation). Uses the shared nav/footer pattern via `includes.js`.

### `live-research.html` - Live Research
Dynamically fetches active research studies from a Google Apps Script web app endpoint. Studies are sorted with Liam's own work surfaced first (secret sort). Includes a disclaimer banner noting that listings are for information only. The Google Apps Script deployment URL is stored in the page's JS.

### `jobs.html` - Jobs Board
An automatically updated board of academic and industry roles relevant to exercise science, kinesiology, physiology, biomechanics, and related disciplines across the UK and Canada. Updated daily at 07:00 UTC by a GitHub Actions workflow running `scrape.py`.

**Filters available:**
- Country: All / UK / Canada
- Role type: All / Academia / Research / Technician / Industry
- Discipline: Sport Science & Kinesiology, Biomechanics, Physiology, Nutrition, S&C, Wearables, Health
- Source dropdown + free-text search

**Sources scraped:** Indeed (UK & Canada), LinkedIn (UK & Canada), Jobs.ac.uk, THEunijobs Canada RSS, HigherEdJobs RSS, University Affairs HTML, Bluesky job posts

**Deduplication:** client-side on title + organisation + source; server-side LinkedIn URL normalisation stripping tracking parameters before ID hashing. Maximum age: 30 days. UK/Canada country badges shown on table rows. Bluesky jobs appear under All but not under country-specific filters.

### `app.html` - ROM-based Exercise (RBE) app
A pose-estimation fitness web app using MediaPipe (loaded from CDN) for real-time joint angle detection via the device camera. Exercise data persists to Firebase Firestore (project: `rom-tracker-app`). Has its own self-contained nav - does not use `includes.js`. Always refer to this app as "ROM-based exercise / RBE" (not the older "ROM-based training / RBT").

### `waitlist.html` - Waitlist
Redirects visitors to `app.html`. Previously hosted a waitlist form; now serves as a forwarding page.

### `404.html` - 404 page
Custom not-found page. Uses the shared `includes.js` nav/footer pattern.

---

## Shared infrastructure

### `includes.js` - Nav & footer
Injected into every public page via:
```html
<nav id="main-nav"></nav>
<footer id="main-footer"></footer>
<script src="includes.js" defer></script>
```
Each page sets `<meta name="current-page" content="[page-id]">` to highlight the active nav link.

`includes.js` also provides:
- Twitter/X card meta tags (derived from existing OG tags)
- Scroll-aware nav (transparent at top, solid on scroll)
- Mobile hamburger menu
- Back-to-top button
- Client-side site search modal (Ctrl+K / Cmd+K), reading from `search-index.json`
- Fade-in animation for `.animate-fade-in` elements

**Contact:** the footer provides a `mailto:` link to `LiamTPearson@gmail.com` and a "Get in Touch" anchor button that scrolls to the contact section. There is no inline contact form.

**Nav links (in order):** Home · Portfolio · CV · Services · LIVE Research · Jobs · Get in Touch

---

## Private personal tools

These files are excluded from the sitemap, nav, and all public-facing references. They carry `noindex` meta tags or equivalent and are explicitly disallowed in `robots.txt`.

### `fitness.html` - Boxing timer & gym tracker
A two-user session tracking app for Liam and Ash's boxing and gym sessions.

**Features:**
- Solo mode (green theme) and With Wife / Partner mode (purple theme)
- 1 or 2 block/bout session structure
- BLE heart rate monitors via Web Bluetooth (Polar straps - separate monitors for Liam and Ash)
- Surprise rounds with rare double-surprise mechanic
- Progressive rest periods
- Session summary with HR analytics, HR zone breakdown, calorie estimation
- PNG export of session summary (html2canvas, lazy-loaded)
- Voice callouts (Web Speech API)
- Wall-clock-based phase timing (prevents time corruption when app is backgrounded on iOS)

**Biometric data (hardcoded - must never be altered):**
- Liam: DOB 05/04/1991, weight 100 kg, male
- Ash: DOB 02/04/1987, weight 70 kg, female
- HRmax uses Tanaka formula: 208 - (0.7 × age)

**Calorie estimation:** Keytel et al. (2005) sex-specific formula, clamped 0-20 kcal/min

**HR zones (% HRmax):** Z1 <57% · Z2 57-63% · Z3 64-76% · Z4 77-95% · Z5 ≥95%

**Backend:**
- Firebase Firestore (project: `fitness-tracker-4cafa`, collection: `boxing-sessions`) stores completed session documents
- Google Apps Script webhook auto-posts session data to a Google Sheet after each session (single sheet, `person` column distinguishes Liam and Ash rows, shared `sessionId` links partner rows)

**No localStorage** - the app is stateless between sessions by design.

### `crypto.html` - Cryptocurrency dashboard
Tracks ZEC/XTZ exchange rate against a personal target value, plus ZEC, XTZ, and BTC spot prices. Multi-panel chart layout with 15m, 1h, 12h, 24h, and 7d timeframes. Default view: 24h. Data sourced from the Binance API. Built with Tailwind CSS and Chart.js. Gold Bitcoin favicon (base64 embedded).

### `crypto-widget.html` - Crypto widget
A minimal single-panel variant of the crypto dashboard intended for use as an embedded widget.

### `route.html` - Route Home comparator
A single-file driving route tool for comparing routes to/from home with and without the Tyne Tunnel, factoring in live fuel prices.

**Features:**
- Route calculation via OpenRouteService API (free tier, no card required)
- Live fuel prices from checkfuelprices.co.uk
- Tyne Tunnel detection via polyline bounding box
- Toll schedule hardcoded (`TT2_SCHEDULE`) with 10% TT2 Pre-Paid discount applied
- Google Maps "Drive it" deep links using 3 sampled waypoints (25/50/75% of polyline)
- Leaflet map with dark OSM tile theme
- Address geocoding via Postcodes.io

Carries `noindex` meta tag and is excluded from `sitemap.xml`.

---

## Automated job scraper

**Script:** `scrape.py`  
**Workflow:** `scrape.yml` (GitHub Actions, runs daily at 07:00 UTC)  
**Output:** `jobs.json` (committed to the repo, read by `jobs.html` at runtime)

The scraper pulls roles matching exercise science, kinesiology, physiology, biomechanics, S&C, wearables, nutrition, and health keywords from all configured sources, deduplicates them, prunes entries older than 30 days, and writes the result to `jobs.json`. Changes are committed automatically by the workflow.

---

## Boxing HR dashboard (Google Sheets)

Session data from `fitness.html` flows automatically to a connected Google Sheet via the Apps Script webhook. A companion Apps Script (`BoxingDashboard.gs`, stored separately) generates the following dashboard tabs inside that sheet:

| Tab | Contents |
|---|---|
| 📊 Summary | All-time key metrics for Liam and Ash side by side |
| 📈 Liam | Session history table, 6 trend charts, rolling 3-session averages |
| 📈 Ash | Same as Liam |
| ⚖️ Compare | Partner sessions side by side, %HRmax normalised comparison |
| 🫀 Zones | Z1-Z5 seconds per session and cumulative totals per athlete |
| 📖 Glossary | Full definitions of every metric with calculation methods and references |

Charts use static data ranges (not QUERY formulas) so series labels and legends render correctly. Axis scaling is computed from actual data values with 15% padding. Gridlines use `color: 'transparent'` to hide them without suppressing axis tick labels or numbers.

To refresh the dashboard after new sessions accumulate, open the sheet and run **🥊 Boxing Dashboard > Build / Refresh Dashboard** from the menu.

---

## Key technical rules

- **Static hosting only** - no server-side code, no build steps, no CLI/terminal workflows. All changes are committed via GitHub Desktop or the `github.dev` browser editor.
- **Tailwind CSS via CDN** - intentional; do not replace with a compiled stylesheet. JIT/arbitrary values depend on it.
- **`includes.js` pattern is mandatory** for all public pages. Never use inline nav/footer placeholders, fake `href="#"` links, or image placeholder divs.
- **Real image paths must always be preserved** - images live in `assets/images/` with their original filenames.
- **`fitness.html` and `boxing.html` are separate files** - `fitness.html` is the boxing timer + gym app. `boxing.html` is a private unrelated file. Never conflate them.
- **No localStorage in `fitness.html`** - static hosting, no persistence between sessions.
- **Biometric data in `fitness.html` must never be altered** in any rewrite.
