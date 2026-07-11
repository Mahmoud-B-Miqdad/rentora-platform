document.addEventListener('DOMContentLoaded', function () {
 
  // ── Modals ────────────────────────────────────────────────
  document.querySelectorAll('[data-modal-open]').forEach(btn => {
    btn.addEventListener('click', function () {
      const modal = document.getElementById(this.dataset.modalOpen);
      if (modal) modal.classList.add('open');
    });
  });
 
  document.querySelectorAll('[data-modal-close]').forEach(el => {
    el.addEventListener('click', function () {
      this.closest('.con-modal').classList.remove('open');
    });
  });
 
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      document.querySelectorAll('.con-modal.open').forEach(m => m.classList.remove('open'));
    }
  });
 
  // ── Confirm-before-submit forms ───────────────────────────
  document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', function (e) {
      if (!window.confirm(this.dataset.confirm)) e.preventDefault();
    });
  });
 
  // ── Auto-dismiss flash messages ───────────────────────────
  document.querySelectorAll('.con-flash').forEach(flash => {
    setTimeout(() => {
      flash.style.transition = 'opacity .4s';
      flash.style.opacity = '0';
      setTimeout(() => flash.remove(), 400);
    }, 4000);
  });
 
});