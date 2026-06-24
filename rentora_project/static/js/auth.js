/* ═══════════════════════════════════════════════════════════════
   auth.js — Rentora Auth Page Behaviour
   Scope: users/auth.html only
   ═══════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

    /* ── Panel Toggle (Login ↔ Register) ──────────────────────
       Switches between the two panels without a page reload.    */
    const loginPanel    = document.getElementById('panel-login');
    const registerPanel = document.getElementById('panel-register');

    function showPanel(target) {
        const isLogin = target === 'login';
        loginPanel.classList.toggle('auth-panel--active', isLogin);
        registerPanel.classList.toggle('auth-panel--active', !isLogin);
    }

    document.querySelectorAll('[data-show-panel]').forEach(trigger => {
        trigger.addEventListener('click', e => {
            e.preventDefault();
            showPanel(trigger.dataset.showPanel);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    });

    /* ── Password Visibility Toggle ───────────────────────────  */
    document.querySelectorAll('.field__eye').forEach(btn => {
        btn.addEventListener('click', () => {
            const input = btn.closest('.field__control').querySelector('.field__input');
            const icon  = btn.querySelector('i');
            const hidden = input.type === 'password';
            input.type     = hidden ? 'text' : 'password';
            icon.className = hidden ? 'fa-regular fa-eye-slash' : 'fa-regular fa-eye';
        });
    });

    /* ── Demo Credentials Fill ────────────────────────────────  */
    const demoBtn = document.getElementById('btn-demo');
    if (demoBtn) {
        demoBtn.addEventListener('click', () => {
            const emailInput    = document.querySelector('#panel-login [name="email"]');
            const passwordInput = document.querySelector('#panel-login [name="password"]');
            if (emailInput)    emailInput.value    = 'demo@rentora.com';
            if (passwordInput) passwordInput.value = 'Demo1234';
        });
    }

    /* ── Auto-dismiss Flash Messages ──────────────────────────  */
    document.querySelectorAll('.auth-flash').forEach(flash => {
        setTimeout(() => {
            flash.style.transition = 'opacity 0.35s ease, margin-top 0.35s ease, padding 0.35s ease';
            flash.style.opacity    = '0';
            flash.style.marginTop  = '0';
            flash.style.padding    = '0';
            setTimeout(() => flash.remove(), 380);
        }, 5000);
    });

});