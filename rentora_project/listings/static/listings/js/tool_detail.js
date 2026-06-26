/* tool_detail.js — Rentora Tool Detail Page */

/* ── Wishlist toggle (global — called via onclick) ──────────────────── */
window.toggleWishlist = function toggleWishlist(btn, toolId) {
    var cfg = window.AppConfig || {};
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
            btn.classList.add('detail-wishlist-btn--saved');
            btn.setAttribute('aria-label', 'Remove from wishlist');
        } else {
            icon.className = 'fa-regular fa-heart';
            btn.classList.remove('detail-wishlist-btn--saved');
            btn.setAttribute('aria-label', 'Save to wishlist');
        }
    })
    .catch(console.error);
};

(function () {
    'use strict';

    var cfg       = window.AppConfig || {};
    var images    = cfg.images    || [];
    var dailyRate = cfg.dailyRate || 0;

    /* ── Image Slider ───────────────────────────────────────────────────── */
    if (images.length > 1) {
        var current = 0;
        var mainImg = document.getElementById('sliderMainImg');
        var dots    = document.querySelectorAll('.img-slider__dot');
        var thumbs  = document.querySelectorAll('.img-slider__thumb');
        var prevBtn = document.getElementById('sliderPrev');
        var nextBtn = document.getElementById('sliderNext');

        function goTo(index) {
            current = (index + images.length) % images.length;
            if (mainImg) mainImg.src = images[current];
            dots.forEach(function (d, i) {
                d.classList.toggle('img-slider__dot--active', i === current);
            });
            thumbs.forEach(function (t, i) {
                t.classList.toggle('img-slider__thumb--active', i === current);
            });
        }

        if (prevBtn) prevBtn.addEventListener('click', function () { goTo(current - 1); });
        if (nextBtn) nextBtn.addEventListener('click', function () { goTo(current + 1); });

        dots.forEach(function (d) {
            d.addEventListener('click', function () { goTo(+d.dataset.index); });
        });
        thumbs.forEach(function (t) {
            t.addEventListener('click', function () { goTo(+t.dataset.index); });
        });
    }

    /* ── Price Estimator ────────────────────────────────────────────────── */
    var startInput  = document.getElementById('start_date');
    var endInput    = document.getElementById('end_date');
    var estimateBox = document.getElementById('priceEstimate');
    var estimateVal = document.getElementById('estimateValue');

    function updateEstimate() {
        if (!startInput || !endInput || !estimateBox) return;
        var s = new Date(startInput.value);
        var e = new Date(endInput.value);
        if (isNaN(s.getTime()) || isNaN(e.getTime()) || e <= s) {
            estimateBox.style.display = 'none';
            return;
        }
        var days  = Math.max(Math.ceil((e - s) / 86400000), 1);
        var total = (days * dailyRate).toFixed(2);
        if (estimateVal) {
            estimateVal.textContent = '$' + total + ' (' + days + ' day' + (days > 1 ? 's' : '') + ')';
        }
        estimateBox.style.display = 'flex';
    }

    if (startInput) startInput.addEventListener('change', updateEstimate);
    if (endInput)   endInput.addEventListener('change', updateEstimate);

    /* Set minimum dates */
    var today = new Date().toISOString().split('T')[0];
    if (startInput) startInput.min = today;
    if (endInput)   endInput.min   = today;

    if (startInput) {
        startInput.addEventListener('change', function () {
            if (endInput) endInput.min = this.value;
        });
    }

})();
