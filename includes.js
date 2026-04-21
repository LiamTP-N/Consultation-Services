/**
 * Shared navigation & footer for all pages.
 * Usage: <script src="includes.js" defer></script>
 *        <nav id="main-nav"></nav>           (place where nav should render)
 *        <footer id="main-footer"></footer>  (place where footer should render)
 *
 * Each page sets:  <meta name="current-page" content="index">  (or live-research, portfolio, cv, jobs, etc.)
 *
 * Also injects:
 *   - Twitter/X card meta tags (derived from existing OG tags)
 *   - Back-to-top button
 *   - Client-side site search modal
 */

(function () {
    const page = document.querySelector('meta[name="current-page"]')?.content || '';

    // ---------------------------------------------------------------
    // Twitter/X card meta injection (reads existing OG tags)
    // ---------------------------------------------------------------
    (function injectTwitterCards() {
        const mapping = [
            { twitter: 'twitter:card',        fallback: 'summary_large_image' },
            { twitter: 'twitter:title',       og: 'og:title' },
            { twitter: 'twitter:description', og: 'og:description' },
            { twitter: 'twitter:image',       og: 'og:image' },
        ];
        mapping.forEach(function (entry) {
            if (document.querySelector('meta[name="' + entry.twitter + '"]')) return; // already set
            var meta = document.createElement('meta');
            meta.setAttribute('name', entry.twitter);
            if (entry.og) {
                var ogTag = document.querySelector('meta[property="' + entry.og + '"]');
                meta.setAttribute('content', ogTag ? ogTag.content : '');
            } else {
                meta.setAttribute('content', entry.fallback);
            }
            document.head.appendChild(meta);
        });
    })();

    // ---------------------------------------------------------------
    // Shared CSS
    // ---------------------------------------------------------------
    const sharedCSS = document.createElement('style');
    sharedCSS.textContent = `
        html { scroll-behavior: smooth; }
        .animate-fade-in { animation: fadeIn 0.6s ease-out forwards; opacity: 0; }
        .animate-fade-in.loaded { opacity: 1; }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .glow-text { text-shadow: 0 0 8px rgba(34, 197, 94, 0.4); }

        /* Back-to-top button */
        #back-to-top {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            z-index: 40;
            width: 2.75rem;
            height: 2.75rem;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 9999px;
            background: rgba(30, 41, 59, 0.9);
            border: 1px solid rgba(71, 85, 105, 0.5);
            color: #94a3b8;
            cursor: pointer;
            opacity: 0;
            transform: translateY(1rem);
            transition: opacity 0.3s, transform 0.3s, background 0.2s, color 0.2s;
            pointer-events: none;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
        }
        #back-to-top.visible {
            opacity: 1;
            transform: translateY(0);
            pointer-events: auto;
        }
        #back-to-top:hover {
            background: rgba(37, 99, 235, 0.9);
            color: #fff;
            border-color: rgba(59, 130, 246, 0.5);
        }

        /* Search modal */
        #site-search-overlay {
            position: fixed;
            inset: 0;
            z-index: 100;
            background: rgba(2, 6, 23, 0.8);
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
            display: none;
            align-items: flex-start;
            justify-content: center;
            padding-top: 12vh;
        }
        #site-search-overlay.open { display: flex; }
        #site-search-box {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 1rem;
            width: 90%;
            max-width: 560px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            overflow: hidden;
            animation: searchSlideIn 0.2s ease-out;
        }
        @keyframes searchSlideIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        #site-search-input {
            width: 100%;
            padding: 1rem 1.25rem;
            background: transparent;
            border: none;
            outline: none;
            color: #f1f5f9;
            font-size: 1rem;
            border-bottom: 1px solid #334155;
        }
        #site-search-input::placeholder { color: #64748b; }
        #site-search-results {
            max-height: 50vh;
            overflow-y: auto;
            padding: 0.5rem;
        }
        #site-search-results:empty::after {
            content: 'Start typing to search...';
            display: block;
            padding: 1rem;
            color: #64748b;
            text-align: center;
            font-size: 0.875rem;
        }
        .search-result-item {
            display: block;
            padding: 0.75rem 1rem;
            border-radius: 0.5rem;
            text-decoration: none;
            transition: background 0.15s;
        }
        .search-result-item:hover, .search-result-item.active {
            background: rgba(51, 65, 85, 0.5);
        }
        .search-result-item .sr-title {
            color: #e2e8f0;
            font-weight: 600;
            font-size: 0.9375rem;
        }
        .search-result-item .sr-desc {
            color: #94a3b8;
            font-size: 0.8125rem;
            margin-top: 0.125rem;
            line-height: 1.4;
        }
        .search-hint {
            padding: 0.5rem 1rem 0.75rem;
            text-align: center;
            color: #475569;
            font-size: 0.75rem;
            border-top: 1px solid #334155;
        }
    `;
    document.head.appendChild(sharedCSS);

    // ---------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------
    function linkClass(id) {
        if (id === 'live-research') return 'text-green-500 font-bold animate-pulse glow-text';
        return page === id ? 'text-white' : 'hover:text-blue-400 transition-colors';
    }
    function mobileLinkClass(id) {
        if (id === 'live-research') return 'text-green-500 font-bold hover:bg-slate-800 py-2 rounded-lg transition-colors';
        return (page === id ? 'text-white' : 'text-slate-300 hover:text-white') + ' hover:bg-slate-800 py-2 rounded-lg transition-colors';
    }

    const links = [
        { id: 'index', label: 'Home', href: 'index.html' },
        { id: 'portfolio', label: 'Portfolio', href: 'portfolio.html' },
        { id: 'cv', label: 'CV', href: 'cv.html' },
        { id: 'live-research', label: 'LIVE Research', href: 'live-research.html' },
        { id: 'jobs', label: 'Jobs', href: 'jobs.html' },
    ];

    // ---------------------------------------------------------------
    // Navigation (no search icon)
    // ---------------------------------------------------------------
    const nav = document.getElementById('main-nav');
    if (nav) {
        nav.className = 'fixed w-full z-50 transition-all duration-300 bg-transparent py-4';
        nav.innerHTML = `
        <div class="max-w-7xl mx-auto px-4">
            <div class="flex justify-between items-center">
                <a href="index.html" class="font-bold text-xl tracking-tight text-slate-100 hover:text-blue-400 transition">
                    Dr. Liam T. Pearson-Noseworthy
                </a>
                <div class="hidden md:flex gap-6 text-sm font-medium text-slate-400 items-center">
                    ${links.map(l => `<a href="${l.href}" class="${linkClass(l.id)}">${l.label}</a>`).join('\n                    ')}
                    <a href="#contact" class="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">Get in Touch</a>
                </div>
                <div class="md:hidden flex items-center gap-3">
                    <button id="mobile-menu-btn" class="text-slate-300 hover:text-white focus:outline-none">
                        <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
                        </svg>
                    </button>
                </div>
            </div>
            <div id="mobile-menu" class="hidden md:hidden mt-4 pb-4 bg-slate-900/95 backdrop-blur-xl border-t border-slate-700 rounded-b-xl">
                <div class="flex flex-col space-y-4 pt-4 px-2 text-center">
                    ${links.map(l => `<a href="${l.href}" class="${mobileLinkClass(l.id)}">${l.label}</a>`).join('\n                    ')}
                    <a href="#contact" class="bg-blue-600 text-white py-3 rounded-lg font-bold mx-4 shadow-lg">Get in Touch</a>
                </div>
            </div>
        </div>`;

        // scroll behaviour (throttled to ~60fps)
        let scrollTick = false;
        const handleScroll = () => {
            if (window.scrollY > 50) {
                nav.classList.remove('bg-transparent', 'py-4');
                nav.classList.add('bg-slate-900/95', 'backdrop-blur-sm', 'shadow-md', 'py-3', 'border-b', 'border-slate-700');
            } else {
                nav.classList.add('bg-transparent', 'py-4');
                nav.classList.remove('bg-slate-900/95', 'backdrop-blur-sm', 'shadow-md', 'py-3', 'border-b', 'border-slate-700');
            }
        };
        window.addEventListener('scroll', () => {
            if (!scrollTick) {
                requestAnimationFrame(() => {
                    handleScroll();
                    scrollTick = false;
                });
                scrollTick = true;
            }
        });
        handleScroll();

        // mobile menu toggle
        const btn = document.getElementById('mobile-menu-btn');
        const menu = document.getElementById('mobile-menu');
        if (btn && menu) {
            btn.addEventListener('click', () => menu.classList.toggle('hidden'));
        }
    }

    // ---------------------------------------------------------------
    // Footer
    // ---------------------------------------------------------------
    const footer = document.getElementById('main-footer');
    if (footer) {
        const year = new Date().getFullYear();
        footer.className = 'py-8 px-4 bg-slate-800 text-white mt-auto border-t border-slate-700';
        footer.innerHTML = `
        <div id="contact" class="max-w-7xl mx-auto">
            <div class="text-center mb-8">
                <h2 class="text-xl font-bold mb-2">Ready to optimise your training or research?</h2>
                <p class="text-slate-400 text-sm">Get in touch to discuss how I can help.</p>
            </div>
            <div class="flex flex-col sm:flex-row gap-4 justify-center mb-8">
                <a href="mailto:LiamTPearson@gmail.com?subject=Website%20Query" class="flex items-center justify-center bg-blue-500 hover:bg-blue-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-all shadow-md hover:shadow-blue-500/20">
                    Email Me
                    <svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.8 5.2a2 2 0 002.4 0L21 8"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8V6a2 2 0 012-2h14a2 2 0 012 2v2"></path></svg>
                </a>
                <a href="https://www.linkedin.com/in/liamtp-n/" target="_blank" rel="noopener" class="flex items-center justify-center bg-slate-700 hover:bg-slate-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-all shadow-md border border-slate-600">
                    Connect on LinkedIn
                    <svg class="w-4 h-4 ml-2" fill="currentColor" viewBox="0 0 24 24"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.75s.784-1.75 1.75-1.75 1.75.79 1.75 1.75-.783 1.75-1.75 1.75zm13.5 12.268h-3v-5.604c0-3.368-4-3.535-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.766 7 2.062v7.173z"/></svg>
                </a>
                <a href="https://scholar.google.com/citations?user=vXjhLEsAAAAJ&hl=en&oi=ao" target="_blank" rel="noopener" class="flex items-center justify-center bg-slate-700 hover:bg-slate-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-all shadow-md border border-slate-600">
                    Google Scholar
                    <svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path></svg>
                </a>
            </div>
            <div class="pt-6 border-t border-slate-700/50">
                <div class="flex flex-col sm:flex-row justify-between items-center gap-4">
                    <div class="flex flex-wrap justify-center sm:justify-start gap-x-5 gap-y-1 text-xs text-slate-500">
                        ${links.map(l => `<a href="${l.href}" class="hover:text-slate-300 transition-colors">${l.label}</a>`).join('\n                        ')}
                    </div>
                    <div class="text-slate-500 text-xs">
                        &copy; ${year} Dr. Liam T. Pearson-Noseworthy. All rights reserved.
                    </div>
                </div>
            </div>
        </div>`;
    }

    // ---------------------------------------------------------------
    // Back-to-top button
    // ---------------------------------------------------------------
    (function initBackToTop() {
        var btt = document.createElement('button');
        btt.id = 'back-to-top';
        btt.setAttribute('aria-label', 'Back to top');
        btt.title = 'Back to top';
        btt.innerHTML = '<svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 15l7-7 7 7"/></svg>';
        document.body.appendChild(btt);

        function checkScroll() {
            if (window.scrollY > 300) {
                btt.classList.add('visible');
            } else {
                btt.classList.remove('visible');
            }
        }

        var bttTick = false;
        window.addEventListener('scroll', function () {
            if (!bttTick) {
                requestAnimationFrame(function () {
                    checkScroll();
                    bttTick = false;
                });
                bttTick = true;
            }
        });
        checkScroll();

        btt.addEventListener('click', function () {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    })();

    // ---------------------------------------------------------------
    // Site search (Ctrl/Cmd+K still works, just no visible button)
    // ---------------------------------------------------------------
    (function initSiteSearch() {
        // Build overlay
        var overlay = document.createElement('div');
        overlay.id = 'site-search-overlay';
        overlay.innerHTML = `
            <div id="site-search-box">
                <input type="text" id="site-search-input" placeholder="Search pages..." autocomplete="off" />
                <div id="site-search-results"></div>
                <div class="search-hint">Esc to close &middot; &uarr;&darr; to navigate &middot; Enter to open</div>
            </div>`;
        document.body.appendChild(overlay);

        var input = document.getElementById('site-search-input');
        var resultsDiv = document.getElementById('site-search-results');
        var searchIndex = null;
        var activeIdx = -1;

        function openSearch() {
            overlay.classList.add('open');
            input.value = '';
            resultsDiv.innerHTML = '';
            activeIdx = -1;
            setTimeout(function () { input.focus(); }, 50);
        }

        function closeSearch() {
            overlay.classList.remove('open');
            activeIdx = -1;
        }

        // Close on overlay click (not box)
        overlay.addEventListener('click', function (e) {
            if (e.target === overlay) closeSearch();
        });

        // Keyboard: Ctrl/Cmd+K to open, Esc to close
        document.addEventListener('keydown', function (e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                openSearch();
            }
            if (e.key === 'Escape' && overlay.classList.contains('open')) {
                closeSearch();
            }
        });

        // Load index on first open
        function ensureIndex(cb) {
            if (searchIndex) return cb();
            fetch('search-index.json')
                .then(function (r) { return r.json(); })
                .then(function (data) { searchIndex = data; cb(); })
                .catch(function () {
                    resultsDiv.innerHTML = '<p style="padding:1rem;color:#94a3b8;text-align:center;font-size:0.875rem;">Could not load search index.</p>';
                });
        }

        function doSearch(query) {
            if (!searchIndex) return;
            var q = query.toLowerCase().trim();
            if (!q) { resultsDiv.innerHTML = ''; activeIdx = -1; return; }

            var terms = q.split(/\s+/);
            var scored = searchIndex.map(function (item) {
                var haystack = (item.title + ' ' + item.description + ' ' + item.keywords).toLowerCase();
                var score = 0;
                terms.forEach(function (t) {
                    if (haystack.indexOf(t) !== -1) score++;
                    if (item.title.toLowerCase().indexOf(t) !== -1) score += 2; // title match bonus
                });
                return { item: item, score: score };
            }).filter(function (s) { return s.score > 0; });

            scored.sort(function (a, b) { return b.score - a.score; });

            if (scored.length === 0) {
                resultsDiv.innerHTML = '<p style="padding:1rem;color:#94a3b8;text-align:center;font-size:0.875rem;">No results found.</p>';
                activeIdx = -1;
                return;
            }

            resultsDiv.innerHTML = scored.map(function (s, i) {
                return '<a href="' + s.item.url + '" class="search-result-item" data-idx="' + i + '">' +
                    '<div class="sr-title">' + s.item.title + '</div>' +
                    '<div class="sr-desc">' + s.item.description + '</div>' +
                    '</a>';
            }).join('');
            activeIdx = -1;
        }

        function highlightResult(idx) {
            var items = resultsDiv.querySelectorAll('.search-result-item');
            items.forEach(function (el) { el.classList.remove('active'); });
            if (idx >= 0 && idx < items.length) {
                items[idx].classList.add('active');
                items[idx].scrollIntoView({ block: 'nearest' });
            }
        }

        input.addEventListener('input', function () {
            ensureIndex(function () { doSearch(input.value); });
        });

        input.addEventListener('keydown', function (e) {
            var items = resultsDiv.querySelectorAll('.search-result-item');
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                activeIdx = Math.min(activeIdx + 1, items.length - 1);
                highlightResult(activeIdx);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                activeIdx = Math.max(activeIdx - 1, 0);
                highlightResult(activeIdx);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (activeIdx >= 0 && items[activeIdx]) {
                    window.location.href = items[activeIdx].href;
                } else if (items.length > 0) {
                    window.location.href = items[0].href;
                }
            }
        });
    })();

    // ---------------------------------------------------------------
    // Fade-in animation
    // ---------------------------------------------------------------
    document.querySelectorAll('.animate-fade-in').forEach((el, i) => {
        setTimeout(() => el.classList.add('loaded'), 50 * (i + 1));
    });
})();
