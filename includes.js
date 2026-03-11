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
        <div class="max-w-6xl mx-auto">
            <div class="max-w-xl mx-auto mb-8">
                <h2 class="text-xl font-bold mb-6 text-center">Ready to optimise your training or research?</h2>
                <div id="form-success" class="hidden bg-green-900/30 border border-green-700/50 text-green-400 text-sm text-center p-4 rounded-xl mb-4">
                    Thanks for your message - I'll be in touch shortly.
                </div>
                <div id="contact-form-wrap">
                    <div class="space-y-4 mb-6">
                        <div class="grid sm:grid-cols-2 gap-4">
                            <input type="text" id="cf-name" placeholder="Name" required class="w-full bg-slate-800 border border-slate-600 text-white text-sm px-4 py-3 rounded-lg focus:outline-none focus:border-blue-500 placeholder-slate-500 transition-colors">
                            <input type="email" id="cf-email" placeholder="Email" required class="w-full bg-slate-800 border border-slate-600 text-white text-sm px-4 py-3 rounded-lg focus:outline-none focus:border-blue-500 placeholder-slate-500 transition-colors">
                        </div>
                        <select id="cf-subject" class="w-full bg-slate-800 border border-slate-600 text-slate-400 text-sm px-4 py-3 rounded-lg focus:outline-none focus:border-blue-500 transition-colors">
                            <option value="" disabled selected>What can I help with?</option>
                            <option value="Performance Consulting">Performance & Health Consulting</option>
                            <option value="Academic Services">Academic & Data Services</option>
                            <option value="ROM App Feedback">ROM-Based App Feedback</option>
                            <option value="General Enquiry">General Enquiry</option>
                        </select>
                        <textarea id="cf-message" rows="4" placeholder="Your message..." required class="w-full bg-slate-800 border border-slate-600 text-white text-sm px-4 py-3 rounded-lg focus:outline-none focus:border-blue-500 placeholder-slate-500 transition-colors resize-none"></textarea>
                        <button type="button" id="cf-submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg transition-all shadow-lg hover:shadow-blue-600/30 text-sm">
                            Send Message
                        </button>
                    </div>
                </div>
                <div class="flex justify-center gap-4">
                    <a href="https://www.linkedin.com/in/liamtp-n/" target="_blank" class="flex items-center justify-center bg-slate-800 hover:bg-slate-900 text-white px-6 py-2 rounded-lg text-sm font-medium transition-all shadow-md border border-slate-600">
                        Connect on LinkedIn
                        <svg class="w-4 h-4 ml-2" fill="currentColor" viewBox="0 0 24 24"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.75s.784-1.75 1.75-1.75 1.75.79 1.75 1.75-.783 1.75-1.75 1.75zm13.5 12.268h-3v-5.604c0-3.368-4-3.535-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.766 7 2.062v7.173z"/></svg>
                    </a>
                </div>
            </div>
            <div class="pt-4 border-t border-slate-600/50 text-slate-400 text-xs text-center">
                &copy; ${year} Dr. Liam T. Pearson-Noseworthy. All rights reserved.
            </div>
        </div>`;

        // Contact form submission via Formspree
        const cfSubmit = document.getElementById('cf-submit');
        if (cfSubmit) {
            cfSubmit.addEventListener('click', async () => {
                const name = document.getElementById('cf-name');
                const email = document.getElementById('cf-email');
                const subject = document.getElementById('cf-subject');
                const message = document.getElementById('cf-message');

                if (!name.value.trim() || !email.value.trim() || !message.value.trim()) {
                    [name, email, message].forEach(f => {
                        if (!f.value.trim()) f.style.borderColor = '#ef4444';
                    });
                    return;
                }

                cfSubmit.disabled = true;
                cfSubmit.textContent = 'Sending...';

                try {
                    const res = await fetch('https://formspree.io/f/xreyqakv', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                        body: JSON.stringify({
                            name: name.value.trim(),
                            email: email.value.trim(),
                            subject: subject.value,
                            message: message.value.trim()
                        })
                    });
                    if (res.ok) {
                        document.getElementById('contact-form-wrap').classList.add('hidden');
                        document.getElementById('form-success').classList.remove('hidden');
                    } else {
                        cfSubmit.textContent = 'Error - try again';
                        cfSubmit.disabled = false;
                    }
                } catch (e) {
                    cfSubmit.textContent = 'Error - try again';
                    cfSubmit.disabled = false;
                }
            });

            // Clear red borders on input
            ['cf-name', 'cf-email', 'cf-message'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.addEventListener('input', () => el.style.borderColor = '');
            });
        }
    }

    // --- shared fade-in animation ---
    document.querySelectorAll('.animate-fade-in').forEach((el, i) => {
        setTimeout(() => el.classList.add('loaded'), 50 * (i + 1));
    });
})();
