/* ═══════════════════════════════════════════════════════════════
   base.js — Rentora Shared Behaviour
   Scope: all pages (loaded from base.html)
   ═══════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

    const header = document.getElementById('site-header');

    /* ── Scroll-aware header ──────────────────────────────────
       Adds .scrolled when page is scrolled past 60px.
       Removes it when back at the top.                         */
    if (header) {
        const THRESHOLD = 60;

        function syncHeaderScroll() {
            header.classList.toggle('scrolled', window.scrollY > THRESHOLD);
        }

        // Initialise on load (handles page refresh mid-scroll)
        syncHeaderScroll();
        window.addEventListener('scroll', syncHeaderScroll, { passive: true });
    }

    /* ── Active Nav Link ──────────────────────────────────────
       Marks the nav link whose href matches the current path.  */
    const currentPath = window.location.pathname;
    document.querySelectorAll('.header-nav__link').forEach(link => {
        const href = link.getAttribute('href');
        if (href && href !== '#' && currentPath === href) {
            link.classList.add('header-nav__link--active');
        }
    });

});
