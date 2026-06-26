/* home.js — Rentora Home Page */
(function () {
    'use strict';

    var cfg = window.AppConfig || {};

    /* ── Wishlist toggle (called via onclick on tool cards) ─────────────── */
    window.toggleWishlist = function toggleWishlist(btn, toolId) {
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
            var icon = btn.querySelector('i');
            if (data.saved) {
                icon.className = 'fa-solid fa-heart';
                btn.classList.add('tool-card__wishlist--saved');
            } else {
                icon.className = 'fa-regular fa-heart';
                btn.classList.remove('tool-card__wishlist--saved');
            }
        })
        .catch(console.error);
    };

})();
