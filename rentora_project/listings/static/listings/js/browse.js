/* browse.js — Rentora Browse Tools Page */
(function () {
    'use strict';
 
    var cfg = window.AppConfig || {};
 
    /* ── Price range slider ─────────────────────────────────────────────── */
    var range = document.getElementById('priceRange');
    var label = document.getElementById('priceLabel');
 
    if (range && label) {
        function updateSlider() {
            var pct = (range.value / range.max) * 100;
            range.style.setProperty('--pct', pct + '%');
            label.textContent = 'Up to $' + range.value;
        }
        range.addEventListener('input', updateSlider);
        updateSlider();
        range.addEventListener('change', function () { range.form.submit(); });
    }
 
    /* ── Real-time search ───────────────────────────────────────────────── */
    var searchInput = document.getElementById('liveSearch');
    var toolsGrid   = document.getElementById('toolsGrid');
    var liveCount   = document.getElementById('liveCountNum');
    var spinner     = document.getElementById('searchSpinner');
    var debounceTimer = null;
 
    if (searchInput && toolsGrid) {
        searchInput.addEventListener('input', function () {
            clearTimeout(debounceTimer);
            var q = this.value.trim();
 
            debounceTimer = setTimeout(function () {
                var form   = document.getElementById('filterForm');
                var data   = new FormData(form);
                data.set('q', q);
                data.delete('page');
                var params = new URLSearchParams(data).toString();
                var url    = cfg.browseUrl + '?' + params;
 
                if (spinner) spinner.style.display = 'inline-block';
 
                fetch(url, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                })
                .then(function (r) { return r.json(); })
                .then(function (resp) {
                    toolsGrid.innerHTML = resp.html;
                    if (liveCount) liveCount.textContent = resp.count;
                })
                .catch(console.error)
                .finally(function () {
                    if (spinner) spinner.style.display = 'none';
                });
            }, 280);
        });
    }
 
})();
 
/* ── Wishlist counter helper (shared) ───────────────────────────────── */
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
            var badge = document.createElement('span');
            badge.className   = 'wishlist-counter';
            badge.textContent = next;
            wrapper.appendChild(badge);
        }
    } else {
        if (counter) counter.remove();
    }
}
 
/* ── Wishlist toggle (global — called via onclick) ──────────────────── */
window.toggleWishlist = function toggleWishlist(btn, toolId) {
    var cfg = window.AppConfig || {};
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
            btn.classList.add('bcard__wish--saved');
            updateWishlistCounter(+1);
        } else {
            icon.className = 'fa-regular fa-heart';
            btn.classList.remove('bcard__wish--saved');
            updateWishlistCounter(-1);
        }
    })
    .catch(console.error);
};