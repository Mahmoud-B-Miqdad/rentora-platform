/* browse.js — Rentora Browse Tools Page */
(function () {
    'use strict';

    var cfg = window.AppConfig || {};

    /* ── Mobile filter drawer ───────────────────────────────────────────── */
    var drawer  = document.getElementById('filterDrawer');
    var overlay = document.getElementById('filterOverlay');
    var openBtn = document.getElementById('filterToggleBtn');
    var closeBtn = document.getElementById('filterClose');

    function openDrawer() {
        if (!drawer) return;
        drawer.classList.add('is-open');
        overlay.classList.add('is-open');
        openBtn && openBtn.classList.add('is-active');
        document.body.style.overflow = 'hidden';
    }
    function closeDrawer() {
        if (!drawer) return;
        drawer.classList.remove('is-open');
        overlay.classList.remove('is-open');
        openBtn && openBtn.classList.remove('is-active');
        document.body.style.overflow = '';
    }

    openBtn  && openBtn.addEventListener('click', openDrawer);
    closeBtn && closeBtn.addEventListener('click', closeDrawer);
    overlay  && overlay.addEventListener('click', closeDrawer);
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeDrawer();
    });

    /* ── Mobile sort dropdown ───────────────────────────────────────────── */
    var mobileSort = document.getElementById('mobileSortSelect');
    if (mobileSort) {
        mobileSort.addEventListener('change', function () {
            var form = document.getElementById('filterForm');
            var data = form ? new FormData(form) : new FormData();
            data.set('sort', this.value);
            data.delete('page');
            window.location.href = (cfg.browseUrl || '/') + '?' + new URLSearchParams(data).toString();
        });
    }
 
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
/* toggleWishlist is defined globally in base.js and handles badge updates */