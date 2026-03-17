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
        footer.className = 'py-12 px-4 bg-slate-800 text-white mt-auto border-t border-slate-700';
        footer.innerHTML = `
        <div class="max-w-3xl mx-auto">
            <div class="text-center mb-8">
                <h2 class="text-2xl font-bold mb-2">Get in Touch</h2>
                <p class="text-slate-400 text-sm">Whether it's a consultancy enquiry, research collaboration, or a general question - drop me a message and I'll get back to you.</p>
            </div>
            <form
                action="https://formspree.io/f/xreyqakv"
                method="POST"
                id="contact-form"
                class="space-y-4"
            >
                <div class="grid sm:grid-cols-2 gap-4">
                    <div>
                        <label for="contact-name" class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Name</label>
                        <input
                            type="text"
                            id="contact-name"
                            name="name"
                            required
                            placeholder="Your name"
                            class="w-full bg-slate-900 border border-slate-700 text-slate-100 placeholder-slate-600 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                        >
                    </div>
                    <div>
                        <label for="contact-email" class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Email</label>
                        <input
                            type="email"
                            id="contact-email"
                            name="email"
                            required
                            placeholder="your@email.com"
                            class="w-full bg-slate-900 border border-slate-700 text-slate-100 placeholder-slate-600 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                        >
                    </div>
                </div>
                <div>
                    <label for="contact-subject" class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Subject</label>
                    <input
                        type="text"
                        id="contact-subject"
                        name="subject"
                        placeholder="e.g. Consultancy enquiry, Research collaboration..."
                        class="w-full bg-slate-900 border border-slate-700 text-slate-100 placeholder-slate-600 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                    >
                </div>
                <div>
                    <label for="contact-message" class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Message</label>
                    <textarea
                        id="contact-message"
                        name="message"
                        required
                        rows="5"
                        placeholder="Tell me what you need..."
                        class="w-full bg-slate-900 border border-slate-700 text-slate-100 placeholder-slate-600 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 transition-colors resize-none"
                    ></textarea>
                </div>
                <div class="flex flex-col sm:flex-row gap-3 items-center justify-between pt-2">
                    <button
                        type="submit"
                        id="contact-submit"
                        class="w-full sm:w-auto bg-blue-600 hover:bg-blue-500 text-white font-bold px-8 py-3 rounded-xl text-sm transition-all duration-200 active:scale-95 border border-blue-500/50 shadow-lg hover:shadow-blue-500/25 flex items-center justify-center gap-2"
                    >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                        Send Message
                    </button>
                    <a href="https://www.linkedin.com/in/liamtp-n/" target="_blank" class="w-full sm:w-auto flex items-center justify-center gap-2 bg-slate-900 hover:bg-slate-700 text-white px-6 py-3 rounded-xl text-sm font-medium transition-all border border-slate-600 hover:border-slate-500">
                        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.75s.784-1.75 1.75-1.75 1.75.79 1.75 1.75-.783 1.75-1.75 1.75zm13.5 12.268h-3v-5.604c0-3.368-4-3.535-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.766 7 2.062v7.173z"/></svg>
                        Connect on LinkedIn
                    </a>
                </div>
                <p id="contact-status" class="text-sm text-center hidden"></p>
            </form>
            <div class="pt-8 mt-8 border-t border-slate-700/50 text-slate-500 text-xs text-center">
                &copy; ${year} Dr. Liam T. Pearson-Noseworthy. All rights reserved.
            </div>
        </div>`;

        // --- Formspree AJAX submission ---
        const form = document.getElementById('contact-form');
        const status = document.getElementById('contact-status');
        const submitBtn = document.getElementById('contact-submit');

        if (form) {
            form.addEventListener('submit', async function (e) {
                e.preventDefault();
                submitBtn.disabled = true;
                submitBtn.textContent = 'Sending...';

                try {
                    const res = await fetch(form.action, {
                        method: 'POST',
                        body: new FormData(form),
                        headers: { 'Accept': 'application/json' }
                    });

                    if (res.ok) {
                        form.reset();
                        status.textContent = "Message sent - I'll be in touch soon.";
                        status.className = 'text-sm text-center text-green-400';
                        status.classList.remove('hidden');
                        submitBtn.textContent = 'Sent';
                    } else {
                        throw new Error('Server error');
                    }
                } catch {
                    status.textContent = 'Something went wrong - please email me directly at LiamTPearson@gmail.com';
                    status.className = 'text-sm text-center text-red-400';
                    status.classList.remove('hidden');
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg> Send Message';
                }
            });
        }
    }

    // --- shared fade-in animation ---
    document.querySelectorAll('.animate-fade-in').forEach((el, i) => {
        setTimeout(() => el.classList.add('loaded'), 50 * (i + 1));
    });
})();
