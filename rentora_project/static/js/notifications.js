/* ─────────────────────────────────────────────────────────────────
   notifications.js — Rentora notification bell + dropdown
   ───────────────────────────────────────────────────────────────── */

(function () {
    'use strict';

    const btn      = document.getElementById('notifBtn');
    const dropdown = document.getElementById('notifDropdown');
    const badge    = document.getElementById('notifBadge');
    const list     = document.getElementById('notifList');
    const markAll  = document.getElementById('notifMarkAll');
    const chip     = document.getElementById('notifUnreadChip');

    if (!btn) return;  // not logged in

    let loaded = false;

    // ── Toggle ────────────────────────────────────────────────────────
    btn.addEventListener('click', function (e) {
        e.stopPropagation();
        const isOpen = dropdown.classList.toggle('open');
        btn.setAttribute('aria-expanded', isOpen);
        if (isOpen && !loaded) {
            fetchNotifications();
        }
    });

    // Close on outside click
    document.addEventListener('click', function (e) {
        if (!dropdown.contains(e.target) && e.target !== btn) {
            dropdown.classList.remove('open');
            btn.setAttribute('aria-expanded', 'false');
        }
    });

    // ── Fetch & render ────────────────────────────────────────────────
    function fetchNotifications() {
        list.innerHTML = skeletonHTML(3);

        fetch('/notifications/', { credentials: 'same-origin' })
            .then(r => r.json())
            .then(data => {
                loaded = true;
                renderList(data.notifications);
                updateBadge(data.unread_count);
            })
            .catch(() => {
                list.innerHTML = '<div class="notif-empty"><i class="fa-solid fa-wifi-slash"></i><p>Could not load notifications</p></div>';
            });
    }

    function renderList(notifications) {
        if (!notifications.length) {
            list.innerHTML = `
                <div class="notif-empty">
                    <i class="fa-regular fa-bell-slash"></i>
                    <p>No notifications yet</p>
                </div>`;
            updateChip(0);
            return;
        }

        const unread = notifications.filter(n => !n.is_read).length;
        updateChip(unread);

        list.innerHTML = notifications.map(n => `
            <div class="notif-item ${n.is_read ? 'read' : 'unread'}"
                 data-id="${n.id}"
                 data-url="${n.booking_url}"
                 role="button"
                 tabindex="0">
                <div class="notif-icon ${n.color_class}">
                    <i class="fa-solid ${n.icon}"></i>
                </div>
                <div class="notif-body">
                    <div class="notif-msg">${escHtml(n.message)}</div>
                    <div class="notif-time">${n.time_ago}</div>
                </div>
                <div class="notif-dot"></div>
            </div>
        `).join('');

        // Click on each item
        list.querySelectorAll('.notif-item').forEach(item => {
            item.addEventListener('click', onItemClick);
            item.addEventListener('keydown', e => {
                if (e.key === 'Enter' || e.key === ' ') onItemClick.call(item, e);
            });
        });
    }

    // ── Item click — mark read then navigate ──────────────────────────
    function onItemClick(e) {
        const item = this;
        const id   = item.dataset.id;
        const url  = item.dataset.url;

        if (!item.classList.contains('read')) {
            item.classList.remove('unread');
            item.classList.add('read');

            getCsrf().then(csrf => {
                fetch(`/notifications/${id}/read/`, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'X-CSRFToken': csrf },
                }).then(r => r.json()).then(data => {
                    updateBadge(data.unread_count);
                    const remaining = list.querySelectorAll('.notif-item.unread').length;
                    updateChip(remaining);
                });
            });
        }

        dropdown.classList.remove('open');
        btn.setAttribute('aria-expanded', 'false');
        window.location.href = url;
    }

    // ── Mark all read ─────────────────────────────────────────────────
    if (markAll) {
        markAll.addEventListener('click', function () {
            getCsrf().then(csrf => {
                fetch('/notifications/mark-all-read/', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'X-CSRFToken': csrf },
                }).then(r => r.json()).then(() => {
                    list.querySelectorAll('.notif-item.unread').forEach(el => {
                        el.classList.remove('unread');
                        el.classList.add('read');
                    });
                    updateBadge(0);
                    updateChip(0);
                });
            });
        });
    }

    // ── Badge helpers ─────────────────────────────────────────────────
    function updateBadge(count) {
        if (!badge) return;
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.style.display = 'flex';
        } else {
            badge.style.display = 'none';
        }
    }

    function updateChip(count) {
        if (!chip) return;
        if (count > 0) {
            chip.textContent = count;
            chip.style.display = 'inline-flex';
        } else {
            chip.style.display = 'none';
        }
    }

    // ── Poll for new notifications every 60 s ────────────────────────
    setInterval(function () {
        fetch('/notifications/unread/', { credentials: 'same-origin' })
            .then(r => r.json())
            .then(data => {
                updateBadge(data.unread_count);
                if (data.unread_count > 0 && loaded) {
                    loaded = false;  // re-fetch list on next open
                }
            })
            .catch(() => {});
    }, 60000);

    // ── CSRF ──────────────────────────────────────────────────────────
    function getCsrf() {
        const cookie = document.cookie.split(';')
            .map(c => c.trim())
            .find(c => c.startsWith('csrftoken='));
        const token = cookie ? cookie.split('=')[1] : '';
        return Promise.resolve(token);
    }

    // ── Helpers ───────────────────────────────────────────────────────
    function escHtml(str) {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function skeletonHTML(n) {
        return Array.from({ length: n }, () => `
            <div class="notif-skeleton">
                <div class="skel skel-circle"></div>
                <div class="skel-lines">
                    <div class="skel skel-line skel-line--long"></div>
                    <div class="skel skel-line skel-line--short"></div>
                </div>
            </div>
        `).join('');
    }

})();
