# Dr. Liam T. Pearson-Noseworthy - Personal Professional Website

**Live site:** [liamtp-n.github.io/Consultation-Services/](https://liamtp-n.github.io/Consultation-Services/)
**Hosting:** GitHub Pages (static only - no server-side code)
**Stack:** Vanilla HTML/CSS/JS · Tailwind CSS via CDN · Firebase/Firestore · Google Apps Script

A personal professional website covering consultancy services, academic CV/portfolio, an automated job board for exercise science roles across the UK and Canada, a live research studies feed, and a pose-estimation fitness web app (ROM-based Exercise).

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
└── scrape.yml              GitHub Actions workflow for the scraper
```

---

## Public pages

### `index.html` - Homepage
The main landing page. Introduces professional identity, headline services, and links out to portfolio, CV, and contact. Uses the shared nav/footer pattern via `includes.js`.

### `portfolio.html` - Portfolio
Showcases research projects, publications, and applied work. Organised by topic area.

### `cv.html` - Academic CV
Full academic CV including employment history, qualifications, publications, and editorial roles. Includes a print stylesheet so it renders cleanly when printed or saved as PDF.

### `services.html` - Services
Consultancy services page describing performance and health consulting (athletes, older adults, sport teams, individuals) alongside academic and data services (pipeline engineering, machine learning in R/Python, systematic review support, ad hoc consultation).

### `live-research.html` - Live Research
Dynamically fetches active research studies from a Google Apps Script web app endpoint. Studies are sorted with the site owner's work surfaced first. Includes a disclaimer banner noting that listings are for information only.

### `jobs.html` - Jobs Board
An automatically updated board of academic and industry roles relevant to exercise science, kinesiology, physiology, biomechanics, and related disciplines across the UK and Canada. Updated daily at 07:00 UTC by a GitHub Actions workflow running `scrape.py`.

**Filters available:**
- Country: All / UK / Canada
- Role type: All / Academia / Research / Technician / Industry
- Discipline: Sport Science & Kinesiology, Biomechanics, Physiology, Nutrition, S&C, Wearables, Health
- Source dropdown + free-text search

**Sources scraped:** Indeed (UK & Canada), LinkedIn (UK & Canada), Jobs.ac.uk, THEunijobs Canada RSS, HigherEdJobs RSS, University Affairs HTML, Bluesky job posts.

**Deduplication:** client-side on title + organisation + source; server-side LinkedIn URL normalisation stripping tracking parameters before ID hashing. Maximum age: 30 days. UK/Canada country badges shown on table rows.

### `app.html` - ROM-based Exercise (RBE) app
A pose-estimation fitness web app using MediaPipe (loaded from CDN) for real-time joint angle detection via the device camera. Exercise data persists to Firebase Firestore. Has its own self-contained nav - does not use `includes.js`.

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

**Nav links (in order):** Home · Portfolio · CV · Services · LIVE Research · Jobs · Get in Touch

---

## Automated job scraper

**Script:** `scrape.py`
**Workflow:** `scrape.yml` (GitHub Actions, runs daily at 07:00 UTC)
**Output:** `jobs.json` (committed to the repo, read by `jobs.html` at runtime)

The scraper pulls roles matching exercise science, kinesiology, physiology, biomechanics, S&C, wearables, nutrition, and health keywords from all configured sources, deduplicates them, prunes entries older than 30 days, and writes the result to `jobs.json`. Changes are committed automatically by the workflow.

---

## Key technical rules

- **Static hosting only** - no server-side code, no build steps. All changes are committed via GitHub Desktop or the `github.dev` browser editor.
- **Tailwind CSS via CDN** - intentional; do not replace with a compiled stylesheet. JIT/arbitrary values depend on it.
- **`includes.js` pattern is mandatory** for all public pages. Never use inline nav/footer placeholders, fake `href="#"` links, or image placeholder divs.
- **Real image paths must always be preserved** - images live in `assets/images/` with their original filenames.

---

## Security

See [`SECURITY.md`](SECURITY.md) for the security disclosure policy.

---

## Contact

Email: see the website footer.

---

## Licence

All rights reserved. Code and content are personal/professional work; please contact for permissions before reuse.
