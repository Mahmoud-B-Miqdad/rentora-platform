/* ═══════════════════════════════════════════════════════════════
   base.js — Rentora Shared Behaviour
   Scope: all pages (loaded from base.html)
   ═══════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

    /* ── Active Nav Link ──────────────────────────────────────
       Mark the nav link whose href matches the current path.    */
    const currentPath = window.location.pathname;
    document.querySelectorAll('.header-nav__link').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('header-nav__link--active');
        }
    });

});