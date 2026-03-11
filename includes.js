/**
 * Shared navigation & footer for all pages.
 * Usage: <script src="includes.js" defer></script>
 *        <nav id="main-nav"></nav>           (place where nav should render)
 *        <footer id="main-footer"></footer>  (place where footer should render)
 *
 * Each page sets:  <meta name="current-page" content="index">  (or services, live-research, portfolio, cv, jobs, etc.)
 */

(function () {
    const page = document.querySelector('meta[name="current-page"]')?.content || '';

    // --- helpers ---
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
        { id: 'services', label: 'Services', href: 'services.html' },
        { id: 'live-research', label: 'LIVE Research', href: 'live-research.html' },
        { id: 'jobs', label: 'Jobs', href: 'jobs.html' },
    ];

    // --- build nav ---
    const nav = document.getElementById('main-nav');
    if (nav) {
        nav.className = 'fixed w-full z-50 transition-all duration-300 bg-transparent py-4';
        nav.innerHTML = `
        <div class="max-w-6xl mx-auto px-4">
            <div class="flex justify-between items-center">
                <a href="index.html" class="font-bold text-xl tracking-tight text-slate-100 hover:text-blue-400 transition">
                    Dr. Liam T. Pearson-Noseworthy
                </a>
                <div class="hidden md:flex gap-6 text-sm font-medium text-slate-400 items-center">
                    ${links.map(l => `<a href="${l.href}" class="${linkClass(l.id)}">${l.label}</a>`).join('\n                    ')}
                    <a href="#contact" class="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">Get in Touch</a>
                </div>
                <button id="mobile-menu-btn" class="md:hidden text-slate-300 hover:text-white focus:outline-none">
                    <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
                    </svg>
                </button>
            </div>
            <div id="mobile-menu" class="hidden md:hidden mt-4 pb-4 bg-slate-900/95 backdrop-blur-xl border-t border-slate-700 rounded-b-xl">
                <div class="flex flex-col space-y-4 pt-4 px-2 text-center">
                    ${links.map(l => `<a href="${l.href}" class="${mobileLinkClass(l.id)}">${l.label}</a>`).join('\n                    ')}
                    <a href="#contact" class="bg-blue-600 text-white py-3 rounded-lg font-bold mx-4 shadow-lg">Get in Touch</a>
                </div>
            </div>
        </div>`;

        // scroll behaviour
        const handleScroll = () => {
            if (window.scrollY > 50) {
                nav.classList.remove('bg-transparent', 'py-4');
                nav.classList.add('bg-slate-900/95', 'backdrop-blur-sm', 'shadow-md', 'py-3', 'border-b', 'border-slate-700');
            } else {
                nav.classList.add('bg-transparent', 'py-4');
                nav.classList.remove('bg-slate-900/95', 'backdrop-blur-sm', 'shadow-md', 'py-3', 'border-b', 'border-slate-700');
            }
        };
        window.addEventListener('scroll', handleScroll);
        handleScroll();

        // mobile menu toggle
        const btn = document.getElementById('mobile-menu-btn');
        const menu = document.getElementById('mobile-menu');
        if (btn && menu) {
            btn.addEventListener('click', () => menu.classList.toggle('hidden'));
        }
    }

    // --- build footer ---
    const footer = document.getElementById('main-footer');
    if (footer) {
        const year = new Date().getFullYear();
        footer.id = 'contact';
        footer.className = 'py-6 px-4 bg-slate-700 text-white mt-auto border-t border-slate-600';
        footer.innerHTML = `
        <div class="max-w-6xl mx-auto text-center">
            <h2 class="text-xl font-bold mb-4">Ready to optimise your training or research?</h2>
            <div class="flex flex-col sm:flex-row gap-4 justify-center mb-6">
                <a href="mailto:LiamTPearson@gmail.com?subject=Website%20Query" class="flex items-center justify-center bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium transition-all shadow-md hover:shadow-blue-500/20">
                    Email Me
                    <svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.8 5.2a2 2 0 002.4 0L21 8"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8V6a2 2 0 012-2h14a2 2 0 012 2v2"></path></svg>
                </a>
                <a href="https://www.linkedin.com/in/liamtp-n/" target="_blank" class="flex items-center justify-center bg-slate-800 hover:bg-slate-900 text-white px-6 py-2 rounded-lg text-sm font-medium transition-all shadow-md border border-slate-600">
                    Connect on LinkedIn
                    <svg class="w-4 h-4 ml-2" fill="currentColor" viewBox="0 0 24 24"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.75s.784-1.75 1.75-1.75 1.75.79 1.75 1.75-.783 1.75-1.75 1.75zm13.5 12.268h-3v-5.604c0-3.368-4-3.535-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.766 7 2.062v7.173z"/></svg>
                </a>
            </div>
            <div class="pt-4 border-t border-slate-600/50 text-slate-400 text-xs">
                &copy; ${year} Dr. Liam T. Pearson-Noseworthy. All rights reserved.
            </div>
        </div>`;
    }

    // --- shared fade-in animation ---
    document.querySelectorAll('.animate-fade-in').forEach((el, i) => {
        setTimeout(() => el.classList.add('loaded'), 50 * (i + 1));
    });
})();
