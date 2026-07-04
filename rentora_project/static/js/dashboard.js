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
  const initSubTab = params.get('subtab') || '';

  document.querySelectorAll('.booking-tabs-header, .booking-tabs-nav').forEach(header => {
    const btns     = header.querySelectorAll('.booking-tab-btn');
    const panel    = header.closest('.tab-panel, .section-card');
    const contents = panel ? panel.querySelectorAll('.booking-tab-content') : [];

    function activateSubTab(targetId) {
      btns.forEach(b => b.classList.remove('active'));
      contents.forEach(c => c.classList.remove('active'));
      const btn = header.querySelector(`.booking-tab-btn[data-target="${targetId}"]`);
      const content = document.getElementById(targetId);
      if (btn) btn.classList.add('active');
      if (content) content.classList.add('active');
    }

    btns.forEach(btn => {
      btn.addEventListener('click', function () {
        activateSubTab(this.dataset.target);
      });
    });

    // If URL has ?subtab= and it belongs to this group → activate it
    const subBtn = initSubTab
      ? header.querySelector(`.booking-tab-btn[data-target="${initSubTab}"]`)
      : null;

    if (subBtn) {
      activateSubTab(initSubTab);
    } else {
      // Default: activate first sub-tab in group
      if (btns.length > 0) activateSubTab(btns[0].dataset.target);
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


  // ── Inbox Search ─────────────────────────────────────────
  const inboxSearch = document.getElementById('inboxSearch');
  if (inboxSearch) {
    inboxSearch.addEventListener('input', function () {
      const query = this.value.trim().toLowerCase();
      document.querySelectorAll('#inboxList .inbox-item').forEach(item => {
        const haystack = (item.dataset.search || '').toLowerCase();
        item.classList.toggle('inbox-item--hidden', query.length > 0 && !haystack.includes(query));
      });
    });
  }

});