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


  // ── Booking Sub-Tabs ────────────────────────────────────
  const bookingTabBtns     = document.querySelectorAll('.booking-tab-btn');
  const bookingTabContents = document.querySelectorAll('.booking-tab-content');

  bookingTabBtns.forEach(btn => {
    btn.addEventListener('click', function () {
      bookingTabBtns.forEach(b => b.classList.remove('active'));
      bookingTabContents.forEach(c => c.classList.remove('active'));

      this.classList.add('active');
      const target = document.getElementById(this.dataset.target);
      if (target) target.classList.add('active');
    });
  });

  // Activate first booking tab by default
  if (bookingTabBtns.length > 0) {
    bookingTabBtns[0].classList.add('active');
    bookingTabContents[0].classList.add('active');
  }


  // ── Auto-dismiss Alerts ─────────────────────────────────
  document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = '0';
      alert.style.transition = 'opacity 0.4s';
      setTimeout(() => alert.remove(), 400);
    }, 3500);
  });

});