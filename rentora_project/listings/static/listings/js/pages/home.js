/* home.js — Rentora Home Page */
(function () {
    'use strict';

    var cfg = window.AppConfig || {};

    /* ── Stats Counter Animation ─────────────────────────────────────────────
       Counts up from 0 to data-count when the stats section enters the
       viewport. Uses IntersectionObserver for performance.                   */
    (function initCounters() {
        var counters = document.querySelectorAll('.stat-item__val[data-count]');
        if (!counters.length) return;

        function animateCounter(el) {
            var target   = parseFloat(el.dataset.count) || 0;
            var suffix   = el.dataset.suffix  || '';
            var decimals = parseInt(el.dataset.decimal || '0', 10);
            var duration = 1800;
            var start    = null;

            function step(timestamp) {
                if (!start) start = timestamp;
                var progress = Math.min((timestamp - start) / duration, 1);
                var ease     = 1 - Math.pow(1 - progress, 3); /* cubic ease-out */
                var value    = target * ease;
                el.textContent = value.toFixed(decimals) + suffix;
                if (progress < 1) requestAnimationFrame(step);
            }
            requestAnimationFrame(step);
        }

        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.3 });

        counters.forEach(function (el) { observer.observe(el); });
    }());
 
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
 
})();