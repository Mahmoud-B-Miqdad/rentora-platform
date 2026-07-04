/* ═══════════════════════════════════════════════════════════════
   base.js — Rentora Shared Behaviour
   Scope: all pages (loaded from base.html)
   ═══════════════════════════════════════════════════════════════ */

/* ── Wishlist toggle (shared across all pages) ────────────────
   Pages that need per-page overrides (home.js, tool_detail.js)
   can reassign window.toggleWishlist after this file loads.      */
window.toggleWishlist = function toggleWishlist(btn, toolId) {
    var cfg = window.AppConfig || {};
    if (!cfg.toggleWishlistUrl) return;
    var url = cfg.toggleWishlistUrl.replace('/0/', '/' + toolId + '/');

    fetch(url, {
        method: 'POST',
        headers: { 'X-CSRFToken': cfg.csrfToken },
    })
    .then(function (r) {
        if (r.status === 401) { window.location.href = cfg.loginUrl; return null; }
        return r.json();
    })
    .then(function (data) {
        if (!data) return;

        // Update clicked button icon
        var icon = btn.querySelector('i');
        if (icon) {
            icon.className = data.saved ? 'fa-solid fa-heart' : 'fa-regular fa-heart';
        }
        btn.classList.toggle('tool-card__wishlist--saved',    !!data.saved);
        btn.classList.toggle('detail-wishlist-btn--saved',    !!data.saved);

        // Update header counter badge using server-returned count
        var wrapperEl = document.querySelector('.wishlist-icon-wrapper');
        var counter   = wrapperEl ? wrapperEl.querySelector('.wishlist-counter') : null;
        if (wrapperEl) wrapperEl.dataset.count = data.count;

        if (data.count > 0 && data.saved) {
            // Item added — show badge (user hasn't "seen" the new count yet)
            if (counter) {
                counter.textContent    = data.count;
                counter.style.display  = 'flex';
            } else if (wrapperEl) {
                var newBadge = document.createElement('span');
                newBadge.className   = 'wishlist-counter';
                newBadge.textContent = data.count;
                wrapperEl.appendChild(newBadge);
            }
        } else if (!data.saved) {
            // Item removed — update count; hide badge if now at or below last seen
            var seenNow = parseInt(localStorage.getItem('wishlistSeenCount') || '0', 10);
            if (data.count > 0 && data.count > seenNow) {
                if (counter) counter.textContent = data.count;
            } else {
                if (counter) counter.style.display = 'none';
            }
        }
    })
    .catch(console.error);
};

/* ── Wishlist badge "seen" logic ──────────────────────────────
   Badge shows only for items added since the last wishlist visit.
   Uses localStorage.wishlistSeenCount as the "last seen" baseline. */
document.addEventListener('DOMContentLoaded', function () {
    var wrapper = document.querySelector('.wishlist-icon-wrapper[data-count]');
    if (!wrapper) return;

    var currentCount = parseInt(wrapper.dataset.count, 10) || 0;
    var seenCount    = parseInt(localStorage.getItem('wishlistSeenCount') || '0', 10);
    var badge        = wrapper.querySelector('.wishlist-counter');

    // Hide badge if user has already seen this count (or higher)
    if (badge && currentCount <= seenCount) {
        badge.style.display = 'none';
    }
});

document.addEventListener('DOMContentLoaded', () => {

    const header = document.getElementById('site-header');

    /* ── Scroll-aware header ──────────────────────────────────
       Adds .scrolled when page is scrolled past 60px.          */
    if (header) {
        const THRESHOLD = 60;
        function syncHeaderScroll() {
            header.classList.toggle('scrolled', window.scrollY > THRESHOLD);
        }
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

    /* ── User dropdown ────────────────────────────────────────
       Toggle .hdr-user--open on click; close on outside click. */
    const hdrUser    = document.getElementById('hdrUser');
    const hdrUserBtn = document.getElementById('hdrUserBtn');

    if (hdrUser && hdrUserBtn) {
        hdrUserBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            const isOpen = hdrUser.classList.toggle('hdr-user--open');
            hdrUserBtn.setAttribute('aria-expanded', isOpen);
        });

        document.addEventListener('click', function (e) {
            if (!hdrUser.contains(e.target)) {
                hdrUser.classList.remove('hdr-user--open');
                hdrUserBtn.setAttribute('aria-expanded', 'false');
            }
        });

        // Close on Escape key
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                hdrUser.classList.remove('hdr-user--open');
                hdrUserBtn.setAttribute('aria-expanded', 'false');
            }
        });
    }

});
