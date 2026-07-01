document.addEventListener('DOMContentLoaded', function () {

  // ── Sidebar Tab Navigation ──────────────────────────────
  const navLinks    = document.querySelectorAll('.nav-link[data-tab]');
  const tabPanels   = document.querySelectorAll('.tab-panel');

  function activateTab(tabId) {
    // Hide all panels
    tabPanels.forEach(p => p.classList.remove('active'));

    // Deactivate all nav links
    navLinks.forEach(l => l.classList.remove('active'));

    // Show target panel
    const target = document.getElementById('tab-' + tabId);
    if (target) target.classList.add('active');

    // Activate nav link
    const link = document.querySelector('.nav-link[data-tab="' + tabId + '"]');
    if (link) link.classList.add('active');

    // Update URL without reload
    const url = new URL(window.location);
    url.searchParams.set('tab', tabId);
    window.history.pushState({}, '', url);
  }

  navLinks.forEach(link => {
    link.addEventListener('click', function () {
      activateTab(this.dataset.tab);
    });
  });

  // Read tab from URL on load
  const params  = new URLSearchParams(window.location.search);
  const initTab = params.get('tab') || 'overview';
  activateTab(initTab);


  // ── Booking Sub-Tabs (scoped per header group) ──────────
  document.querySelectorAll('.booking-tabs-header, .booking-tabs-nav').forEach(header => {
    const btns     = header.querySelectorAll('.booking-tab-btn');
    const panel    = header.closest('.tab-panel, .section-card');
    const contents = panel ? panel.querySelectorAll('.booking-tab-content') : [];

    btns.forEach(btn => {
      btn.addEventListener('click', function () {
        btns.forEach(b => b.classList.remove('active'));
        contents.forEach(c => c.classList.remove('active'));
        this.classList.add('active');
        const target = document.getElementById(this.dataset.target);
        if (target) target.classList.add('active');
      });
    });

    // Activate first tab in each group by default
    if (btns.length > 0) {
      btns[0].classList.add('active');
      if (contents.length > 0) contents[0].classList.add('active');
    }
  });


  // ── Review Modals (open / close) ────────────────────────
  document.querySelectorAll('[data-review-modal]').forEach(btn => {
    btn.addEventListener('click', function () {
      const modal = document.getElementById('review-modal-' + this.dataset.reviewModal);
      if (modal) modal.classList.add('active');
    });
  });

  document.querySelectorAll('.review-modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay || e.target.closest('[data-modal-close]')) {
        overlay.classList.remove('active');
      }
    });
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      document.querySelectorAll('.review-modal-overlay.active').forEach(m => m.classList.remove('active'));
    }
  });

  // ── Interactive Star Rating Widgets ──────────────────────
  document.querySelectorAll('.star-rating').forEach(widget => {
    const stars = widget.querySelectorAll('i');
    const input = widget.querySelector('input[type="hidden"]');

    function paint(value) {
      stars.forEach(star => {
        const active = Number(star.dataset.value) <= value;
        star.classList.toggle('is-active', active);
        star.classList.toggle('fa-solid', active);
        star.classList.toggle('fa-regular', !active);
      });
    }

    stars.forEach(star => {
      star.addEventListener('click', function () {
        input.value = this.dataset.value;
        paint(Number(this.dataset.value));
      });
      star.addEventListener('mouseenter', function () {
        paint(Number(this.dataset.value));
      });
    });

    widget.addEventListener('mouseleave', function () {
      paint(Number(input.value));
    });
  });

  // ── Require at least one rating before submitting a review ──
  document.querySelectorAll('.review-modal__form').forEach(form => {
    form.addEventListener('submit', function (e) {
      const ratings = form.querySelectorAll('.star-rating input[type="hidden"]');
      const hasRating = Array.from(ratings).some(input => Number(input.value) > 0);
      if (!hasRating) {
        e.preventDefault();
        alert('Please select at least one star rating before submitting.');
      }
    });
  });


  // ── Auto-dismiss Alerts ─────────────────────────────────
  document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = '0';
      alert.style.transition = 'opacity 0.4s';
      setTimeout(() => alert.remove(), 400);
    }, 3500);
  });

});