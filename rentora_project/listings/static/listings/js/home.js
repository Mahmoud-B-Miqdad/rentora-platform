/* home.js — Rentora Home Page */
(function () {
    'use strict';
 
    var cfg = window.AppConfig || {};
 
    /* ── AI Smart Search ─────────────────────────────────────────────────── */
    var form  = document.getElementById('heroSearchForm');
    var input = document.getElementById('heroSearchInput');
    var btn   = document.getElementById('heroSearchBtn');
 
    function setLoading(on) {
        if (!btn) return;
        if (on) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i><span>AI thinking…</span>';
            btn.classList.add('hero__search-btn--loading');
            if (input) input.disabled = true;
        } else {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-robot"></i><span>AI Search</span>';
            btn.classList.remove('hero__search-btn--loading');
            if (input) input.disabled = false;
        }
    }
 
    if (form) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
 
            var query = (input ? input.value : '').trim();
            if (!query) return;
 
            /* If no smart-search URL configured, fall back immediately */
            if (!cfg.smartSearchUrl) {
                window.location.href = cfg.browseUrl + '?q=' + encodeURIComponent(query);
                return;
            }
 
            setLoading(true);
 
            fetch(cfg.smartSearchUrl, {
                method:  'POST',
                headers: {
                    'X-CSRFToken':  cfg.csrfToken,
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'q=' + encodeURIComponent(query),
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                window.location.href = data.redirect ||
                    (cfg.browseUrl + '?q=' + encodeURIComponent(query));
            })
            .catch(function () {
                /* Network / server error — degrade silently */
                window.location.href = cfg.browseUrl + '?q=' + encodeURIComponent(query);
            });
        });
    }
 
    /* ── Wishlist counter helper ─────────────────────────────────────────── */
    function updateWishlistCounter(delta) {
        var counter = document.querySelector('.wishlist-counter');
        var wrapper = document.querySelector('.wishlist-icon-wrapper');
        if (!wrapper) return;
 
        var current = counter ? parseInt(counter.textContent, 10) : 0;
        var next    = Math.max(0, current + delta);
 
        if (next > 0) {
            if (counter) {
                counter.textContent = next;
            } else {
                /* Create counter badge if it doesn't exist yet */
                var badge = document.createElement('span');
                badge.className   = 'wishlist-counter';
                badge.textContent = next;
                wrapper.appendChild(badge);
            }
        } else {
            /* Remove badge when count reaches 0 */
            if (counter) counter.remove();
        }
    }
 
    /* ── Wishlist toggle (called via onclick on tool cards) ─────────────── */
    window.toggleWishlist = function toggleWishlist(btn, toolId) {
        var url = cfg.toggleWishlistUrl.replace('/0/', '/' + toolId + '/');
 
        fetch(url, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': cfg.csrfToken,
            },
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
                updateWishlistCounter(+1);
            } else {
                icon.className = 'fa-regular fa-heart';
                btn.classList.remove('tool-card__wishlist--saved');
                updateWishlistCounter(-1);
            }
        })
        .catch(console.error);
    };
 
})();