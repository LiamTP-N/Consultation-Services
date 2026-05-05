# Dr. Liam T. Pearson-Noseworthy - Personal Academic Website

**Live site:** [liamtp-n.github.io/Consultation-Services/](https://liamtp-n.github.io/Consultation-Services/)

Personal professional and academic website for Dr. Liam T. Pearson-Noseworthy, applied health and exercise scientist (Senior Laboratory Technician, Northumbria University; Reviewing Editor, Springer Nature). Serves as a portfolio, CV, services page, live research feed, and an automatically updated jobs board for exercise science and related disciplines.

---

## Stack

- Static HTML, CSS, and JavaScript - no framework, no build step
- Tailwind CSS via CDN
- Hosted on GitHub Pages
- Firebase / Firestore backs the ROM-based exercise (RBE) web app
- Google Apps Script powers the live research feed
- GitHub Actions runs the daily jobs scraper

---

## Public pages

### `index.html` - Home
Landing page introducing professional identity, headline services, and links to portfolio, CV, and contact.

### `portfolio.html` - Portfolio
Research projects, publications, and applied work, organised by topic area.

### `cv.html` - Academic CV
Full academic CV including employment history, qualifications, publications, and editorial roles. Includes a print stylesheet for clean PDF export.

### `services.html` - Services
Consultancy services across two strands: performance and health consulting (athletes, older adults, sports teams, individuals) and academic / data services (pipeline engineering, machine learning in R and Python, systematic review support, ad hoc consultation).

### `live-research.html` - Live Research
Dynamically fetches active research studies from a Google Apps Script web app endpoint. Includes a disclaimer banner noting that listings are for information only.

### `jobs.html` - Jobs Board
An automatically updated board of academic and industry roles relevant to exercise science, kinesiology, physiology, biomechanics, and related disciplines across the UK and Canada. Refreshed daily by a GitHub Actions workflow running `scrape.py`.

**Filters:** country, role type, discipline, source, and free-text search. Deduplication runs both client-side and server-side; entries older than 30 days are pruned.

### `app.html` - ROM-based Exercise (RBE) app
A pose-estimation fitness web app using MediaPipe (loaded from CDN) for real-time joint-angle detection via the device camera. Exercise data persists to Firebase Firestore. The app is self-contained and does not use the shared nav/footer.

### `waitlist.html` - Waitlist
Redirects visitors to `app.html`.

### `404.html` - Not-found page
Custom 404 page using the shared nav/footer pattern.

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

`includes.js` also provides scroll-aware nav behaviour, mobile hamburger menu, back-to-top button, fade-in animations, and a client-side site search modal (Ctrl+K / Cmd+K) reading from `search-index.json`.

### Other supporting files
- `sitemap.xml` - XML sitemap for search engines
- `robots.txt` - search engine crawl rules
- `manifest.json`, `sw.js` - PWA manifest and service worker
- `search-index.json` - data source for the in-page search modal
- `SECURITY.md` - security disclosure policy

---

## Job scraper

**Script:** `scrape.py` (Python, BeautifulSoup)
**Workflow:** `scrape.yml` (GitHub Actions)
**Output:** `jobs.json`, read by `jobs.html` at runtime

The scraper aggregates roles matching exercise science, kinesiology, physiology, biomechanics, S&C, wearables, nutrition, and health keywords; deduplicates them; prunes entries older than 30 days; and writes the result to `jobs.json`. Updates are committed automatically by the workflow.

---

## Contact

For research collaborations, consultancy enquiries, or any other matter, please use the contact link on the [live site](https://liamtp-n.github.io/Consultation-Services/).
