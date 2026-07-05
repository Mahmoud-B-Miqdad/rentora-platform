/* ═══════════════════════════════════════════════════════════════
   base.js — Rentora Shared Behaviour
   Scope: all pages (loaded from base.html)
   ═══════════════════════════════════════════════════════════════ */

/* ── Wishlist toast notification ─────────────────────────────
   Shows briefly when an item is added. Clicking navigates to wishlist. */
function _showWishlistToast() {
    var wlLink = document.querySelector('a[aria-label="My Wishlist"]');
    var wlUrl  = wlLink ? wlLink.href : '/wishlist/';

    var toast = document.getElementById('wl-toast');
    if (!toast) {
        toast = document.createElement('a');
        toast.id        = 'wl-toast';
        toast.className = 'wl-toast';
        toast.href      = wlUrl;
        toast.innerHTML = '<i class="fa-solid fa-heart wl-toast__icon"></i>' +
                          '<span class="wl-toast__text">Added to wishlist!' +
                          '<span class="wl-toast__hint">Tap to view your wishlist</span></span>';
        document.body.appendChild(toast);
    }
    clearTimeout(toast._hideTimer);
    toast.classList.add('wl-toast--show');
    toast._hideTimer = setTimeout(function () {
        toast.classList.remove('wl-toast--show');
    }, 3500);
}

/* ── Wishlist badge helper ────────────────────────────────────
   displayCount = items added since last wishlist page visit.
   seenCount    = total count stored when user last opened wishlist. */
function _updateWishlistBadge(totalCount) {
    var wrapperEl    = document.querySelector('.wishlist-icon-wrapper');
    var counter      = wrapperEl ? wrapperEl.querySelector('.wishlist-counter') : null;
    if (!wrapperEl || !counter) return;

    var seenCount    = parseInt(localStorage.getItem('wishlistSeenCount') || '0', 10);
    var displayCount = Math.max(0, totalCount - seenCount);

    wrapperEl.dataset.count = totalCount;
    if (displayCount > 0) {
        counter.textContent = displayCount;
        counter.style.display = 'flex';
    } else {
        counter.style.display = 'none';
    }
}

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

        /* Update clicked button icon and state classes */
        var icon = btn.querySelector('i');
        if (icon) {
            icon.className = data.saved ? 'fa-solid fa-heart' : 'fa-regular fa-heart';
        }
        btn.classList.toggle('bcard__wish--saved',         !!data.saved);
        btn.classList.toggle('tool-card__fav--on',         !!data.saved);
        btn.classList.toggle('detail-wishlist-btn--saved', !!data.saved);
        btn.classList.toggle('tool-card__wishlist--saved', !!data.saved);

        /* Update header badge (shows count added since last wishlist visit) */
        _updateWishlistBadge(data.count);

        /* Show toast only when adding (not removing) */
        if (data.saved) { _showWishlistToast(); }
    })
    .catch(console.error);
};

/* ── Wishlist badge "seen" logic ──────────────────────────────
   On every page load, compute displayCount = total - seenCount.
   Badge stays hidden (display:none from HTML) unless displayCount > 0. */
document.addEventListener('DOMContentLoaded', function () {
    var wrapper = document.querySelector('.wishlist-icon-wrapper[data-count]');
    if (!wrapper) return;
    var currentCount = parseInt(wrapper.dataset.count, 10) || 0;
    _updateWishlistBadge(currentCount);
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
