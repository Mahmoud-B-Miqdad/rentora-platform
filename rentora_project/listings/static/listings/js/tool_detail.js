/* tool_detail.js — Rentora Tool Detail Page */
/* toggleWishlist is defined globally in base.js */

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

    /* Auto-scroll to booking panel when a booking error is present */
    var errorAlert = document.getElementById('bookingErrorAlert');
    if (errorAlert) {
        setTimeout(function () {
            errorAlert.closest('#bookingPanel').scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 120);
    }

    if (startInput) {
        startInput.addEventListener('change', function () {
            if (endInput) endInput.min = this.value;
        });
    }

    /* ── Availability Calendar ──────────────────────────────────────────── */
    (function () {
        var gridEl        = document.getElementById('availGrid');
        var monthEl       = document.getElementById('availMonthLabel');
        var yearEl        = document.getElementById('availYearLabel');
        var prevBtn       = document.getElementById('availPrev');
        var nextBtn       = document.getElementById('availNext');
        var selectionEl   = document.getElementById('availSelection');
        var selectionText = document.getElementById('availSelectionText');
        if (!gridEl) return;

        var dataEl       = document.getElementById('booked-ranges-data');
        var bookedRanges = dataEl ? JSON.parse(dataEl.textContent) : [];

        var monthNames = ['January','February','March','April','May','June',
                          'July','August','September','October','November','December'];
        var monthShort = ['Jan','Feb','Mar','Apr','May','Jun',
                          'Jul','Aug','Sep','Oct','Nov','Dec'];

        function parseISO(str) {
            var p = str.split('-');
            return new Date(+p[0], +p[1] - 1, +p[2]);
        }
        function fmt(d) {
            return d.getFullYear() + '-' +
                   String(d.getMonth() + 1).padStart(2, '0') + '-' +
                   String(d.getDate()).padStart(2, '0');
        }
        function fmtDisplay(d) {
            return monthShort[d.getMonth()] + ' ' + d.getDate();
        }

        var bookedSet = new Set();
        bookedRanges.forEach(function (r) {
            var d = parseISO(r.start), end = parseISO(r.end);
            while (d <= end) { bookedSet.add(fmt(d)); d.setDate(d.getDate() + 1); }
        });

        function isBooked(d)  { return bookedSet.has(fmt(d)); }
        function rangeHasBooked(s, e) {
            var d = new Date(s);
            while (d <= e) { if (isBooked(d)) return true; d.setDate(d.getDate() + 1); }
            return false;
        }

        var todayMid = new Date();
        todayMid.setHours(0, 0, 0, 0);

        var viewYear  = todayMid.getFullYear();
        var viewMonth = todayMid.getMonth();
        var selStart  = null;
        var selEnd    = null;

        function updateSelectionBar() {
            if (!selectionEl || !selectionText) return;
            if (selStart && selEnd) {
                var days = Math.round((selEnd - selStart) / 86400000);
                selectionText.textContent =
                    fmtDisplay(selStart) + '  →  ' + fmtDisplay(selEnd) +
                    '   ·   ' + days + ' day' + (days !== 1 ? 's' : '');
                selectionEl.classList.add('avail-cal__selection--active');
            } else if (selStart) {
                selectionText.textContent = fmtDisplay(selStart) + '  →  Pick check-out date';
                selectionEl.classList.remove('avail-cal__selection--active');
            } else {
                selectionText.textContent = 'Select check-in & check-out dates';
                selectionEl.classList.remove('avail-cal__selection--active');
            }
        }

        function syncInputs() {
            if (!startInput) return;
            if (selStart) {
                startInput.value = fmt(selStart);
                startInput.dispatchEvent(new Event('change'));
            }
            if (selEnd && endInput) {
                endInput.value = fmt(selEnd);
                endInput.dispatchEvent(new Event('change'));
            }
            updateSelectionBar();
        }

        function onDayClick(cell) {
            var d = parseISO(cell.dataset.date);
            if (!selStart || selEnd) {
                selStart = d; selEnd = null;
            } else if (d < selStart) {
                selStart = d; selEnd = null;
            } else if (rangeHasBooked(selStart, d)) {
                selStart = d; selEnd = null;
            } else {
                selEnd = d;
            }
            syncInputs();
            render();
        }

        function render() {
            if (monthEl) monthEl.textContent = monthNames[viewMonth];
            if (yearEl)  yearEl.textContent  = viewYear;
            gridEl.innerHTML = '';

            var firstDay    = new Date(viewYear, viewMonth, 1);
            var startOffset = firstDay.getDay();
            var daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();

            for (var i = 0; i < startOffset; i++) {
                var pad = document.createElement('span');
                pad.className = 'avail-day avail-day--pad';
                gridEl.appendChild(pad);
            }

            for (var day = 1; day <= daysInMonth; day++) {
                var d    = new Date(viewYear, viewMonth, day);
                var cell = document.createElement('button');
                cell.type      = 'button';
                cell.className = 'avail-day';
                /* Wrap number in <span> so the ::before range-strip renders behind it */
                cell.innerHTML = '<span>' + day + '</span>';

                var isPast = d < todayMid;
                var booked = isBooked(d);

                if (isPast) {
                    cell.classList.add('avail-day--past');
                    cell.disabled = true;
                } else if (booked) {
                    cell.classList.add('avail-day--booked');
                    cell.disabled = true;
                    cell.title = 'Already booked';
                } else {
                    cell.classList.add('avail-day--available');
                    cell.dataset.date = fmt(d);
                    cell.addEventListener('click', function () { onDayClick(this); });
                }

                var fmtD = fmt(d);
                if (selStart && fmtD === fmt(selStart)) {
                    cell.classList.add(selEnd ? 'avail-day--range-start' : 'avail-day--selected');
                }
                if (selEnd && fmtD === fmt(selEnd)) {
                    cell.classList.add('avail-day--range-end');
                }
                if (selStart && selEnd && d > selStart && d < selEnd) {
                    cell.classList.add('avail-day--in-range');
                }

                gridEl.appendChild(cell);
            }
        }

        if (prevBtn) prevBtn.addEventListener('click', function () {
            viewMonth--; if (viewMonth < 0) { viewMonth = 11; viewYear--; } render();
        });
        if (nextBtn) nextBtn.addEventListener('click', function () {
            viewMonth++; if (viewMonth > 11) { viewMonth = 0; viewYear++; } render();
        });

        render();
        updateSelectionBar();
    })();

    /* ── Lazy Map (IntersectionObserver + dynamic Leaflet) ──────────────────── */
    (function () {
        var mapEl = document.getElementById('toolMap');
        if (!mapEl) return;

        var mapUrl   = mapEl.dataset.mapUrl;
        var toolName = mapEl.dataset.toolName;
        var toolLoc  = mapEl.dataset.toolLocation;
        var loaded   = false;

        function showError() {
            mapEl.innerHTML =
                '<div class="detail-map-no-coords">' +
                '<i class="fa-solid fa-location-dot"></i>' +
                '<span>' + toolLoc + '</span>' +
                '</div>';
            mapEl.classList.remove('detail-map-container--loading');
        }

        function initMap(lat, lon) {
            /* Inject Leaflet CSS */
            var link  = document.createElement('link');
            link.rel  = 'stylesheet';
            link.href = 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.min.css';
            document.head.appendChild(link);

            /* Inject Leaflet JS, init map on load */
            var script    = document.createElement('script');
            script.src    = 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.min.js';
            script.onload = function () {
                mapEl.classList.remove('detail-map-container--loading');
                mapEl.innerHTML = '';

                var map = L.map(mapEl, {
                    center: [lat, lon],
                    zoom: 14,
                    zoomControl: true,
                    scrollWheelZoom: false,
                });

                L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
                    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
                    subdomains: 'abcd',
                    maxZoom: 19,
                }).addTo(map);

                var pin = L.divIcon({
                    className: '',
                    html: '<div class="tool-map-pin"><i class="fa-solid fa-screwdriver-wrench"></i></div>',
                    iconSize:   [44, 44],
                    iconAnchor: [22, 44],
                    popupAnchor:[0, -46],
                });

                L.marker([lat, lon], { icon: pin })
                    .addTo(map)
                    .bindPopup(
                        '<div class="tool-map-popup">' +
                        '<strong>' + toolName + '</strong>' +
                        '<span>' + toolLoc + '</span>' +
                        '</div>',
                        { maxWidth: 200 }
                    )
                    .openPopup();

                L.circle([lat, lon], {
                    radius: 400,
                    color: '#2563eb',
                    fillColor: '#2563eb',
                    fillOpacity: 0.06,
                    weight: 1.5,
                    dashArray: '6 4',
                }).addTo(map);
            };
            script.onerror = showError;
            document.head.appendChild(script);
        }

        function fetchAndRender() {
            if (loaded) return;
            loaded = true;
            fetch(mapUrl)
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data.lat && data.lon) {
                        initMap(data.lat, data.lon);
                    } else {
                        showError();
                    }
                })
                .catch(showError);
        }

        /* Trigger when map container nears the viewport */
        if ('IntersectionObserver' in window) {
            var observer = new IntersectionObserver(function (entries) {
                entries.forEach(function (e) {
                    if (e.isIntersecting) { fetchAndRender(); observer.disconnect(); }
                });
            }, { rootMargin: '200px' });
            observer.observe(mapEl);
        } else {
            /* Fallback for old browsers */
            fetchAndRender();
        }
    }());

})();
