/* ─────────────────────────────────────────────────────────────────
   chat.js — Rentora Messaging
   ───────────────────────────────────────────────────────────────── */
(function () {
    'use strict';

    var cfg        = window.ChatConfig || {};
    var input      = document.getElementById('chatInput');
    var sendBtn    = document.getElementById('chatSend');
    var thread     = document.getElementById('chatMessages');
    var attachBtn  = document.getElementById('chatAttachBtn');
    var imageInput = document.getElementById('chatImageInput');
    var attachPrev = document.getElementById('chatAttachPreview');
    var attachThumb= document.getElementById('chatAttachThumb');
    var attachDrop = document.getElementById('chatAttachRemove');
    var lastId     = cfg.lastMsgId  || 0;
    var lastSeenId = cfg.lastSeenId || 0;
    var sending    = false;
    var pendingImage = null;   /* the File selected but not yet sent */
    var POLL_MS    = 3000;

    if (!input || !sendBtn || !thread) return;

    /* Send button is enabled when there is text OR a pending image. */
    function refreshSendState() {
        sendBtn.disabled = !(input.value.trim() || pendingImage);
    }

    /* ── Auto-resize textarea ──────────────────────────────────── */
    input.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        refreshSendState();
    });

    /* ── Attach a photo ────────────────────────────────────────── */
    if (attachBtn && imageInput) {
        attachBtn.addEventListener('click', function () { imageInput.click(); });
        imageInput.addEventListener('change', function () {
            var file = this.files && this.files[0];
            this.value = '';                       /* allow re-picking same file */
            if (!file) return;
            if (!file.type.indexOf) { return; }
            if (file.type.indexOf('image/') !== 0) { alert('Only image files are allowed.'); return; }
            if (file.size > 8 * 1024 * 1024) { alert('Image must be under 8 MB.'); return; }
            pendingImage = file;
            if (attachThumb) attachThumb.src = URL.createObjectURL(file);
            if (attachPrev)  attachPrev.hidden = false;
            refreshSendState();
        });
    }
    if (attachDrop) {
        attachDrop.addEventListener('click', function () {
            pendingImage = null;
            if (attachPrev) attachPrev.hidden = true;
            if (attachThumb && attachThumb.src) { URL.revokeObjectURL(attachThumb.src); attachThumb.src = ''; }
            refreshSendState();
        });
    }

    /* ── Send on Enter (Shift+Enter = newline) ─────────────────── */
    input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled && !sending) sendMessage();
        }
    });

    sendBtn.addEventListener('click', function () {
        if (!sending) sendMessage();
    });

    /* ── Send ──────────────────────────────────────────────────── */
    function sendMessage() {
        var text = input.value.trim();
        var image = pendingImage;
        if ((!text && !image) || sending) return;

        sending = true;
        sendBtn.disabled = true;

        var localPreview = image ? URL.createObjectURL(image) : '';

        // Optimistic render (status = "sending")
        var tempId = 'temp-' + Date.now();
        appendMessage({
            id:         tempId,
            text:       text,
            image_url:  localPreview,
            is_mine:    true,
            is_read:    false,
            sending:    true,
            time:       nowTime(),
            avatar:     cfg.myAvatar,
            avatar_url: cfg.myAvatarUrl,
        });
        input.value = '';
        input.style.height = 'auto';
        // clear the pending attachment now that it's on its way
        pendingImage = null;
        if (attachPrev) attachPrev.hidden = true;
        if (attachThumb) attachThumb.src = '';
        scrollToBottom();

        // Text-only → JSON (unchanged); with a photo → multipart FormData.
        var opts;
        if (image) {
            var fd = new FormData();
            fd.append('text', text);
            fd.append('image', image);
            opts = { method: 'POST', headers: { 'X-CSRFToken': cfg.csrfToken }, body: fd };
        } else {
            opts = {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': cfg.csrfToken },
                body: JSON.stringify({ text: text }),
            };
        }

        fetch(cfg.sendUrl, opts)
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.ok) {
                var tmp = document.querySelector('[data-id="' + tempId + '"]');
                if (tmp) {
                    tmp.setAttribute('data-id', data.message.id);
                    // Swap the local blob preview for the stored image URL — on
                    // BOTH the <img> and its <a href>, so the lightbox (which
                    // matches the link's href against an image extension) works
                    // immediately, without needing a page reload.
                    if (data.message.image_url) {
                        var img  = tmp.querySelector('.chat-msg__image');
                        if (img) img.src = data.message.image_url;
                        var link = tmp.querySelector('.chat-msg__image-link');
                        if (link) link.setAttribute('href', data.message.image_url);
                    }
                    // Upgrade status: "sending" → "sent"
                    var status = tmp.querySelector('.chat-msg__status');
                    if (status) {
                        status.setAttribute('data-msg-id', data.message.id);
                        status.innerHTML = '<i class="fa-solid fa-check msg-status--sent" title="Sent"></i>';
                    }
                }
                lastId = Math.max(lastId, data.message.id);
            }
        })
        .catch(function () {
            var tmp = document.querySelector('[data-id="' + tempId + '"] .chat-msg__bubble');
            if (tmp) {
                tmp.style.opacity = '0.5';
                tmp.title = 'Failed to send — tap to retry';
            }
        })
        .finally(function () {
            sending = false;
        });
    }

    /* ── Poll for new messages ─────────────────────────────────── */
    function poll() {
        fetch(cfg.pollUrl + '?after=' + lastId, {
            credentials: 'same-origin',
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (!data.ok) return;
            if (data.messages && data.messages.length) {
                var wasAtBottom = isAtBottom();
                data.messages.forEach(function (m) {
                    appendMessage(m);
                    lastId = Math.max(lastId, m.id);
                });
                if (wasAtBottom) scrollToBottom();
            }
            // Update read receipts on our own sent messages
            if (data.last_seen_id) {
                updateSeenIndicators(data.last_seen_id);
            }
        })
        .catch(function () {}) // silently ignore poll errors
        .finally(function () {
            setTimeout(poll, POLL_MS);
        });
    }

    /* ── Update "seen" checkmarks up to a given message ID ─────── */
    function updateSeenIndicators(upToId) {
        if (!upToId || upToId <= lastSeenId) return;
        lastSeenId = upToId;
        thread.querySelectorAll('.chat-msg__status[data-msg-id]').forEach(function (el) {
            var msgId = parseInt(el.dataset.msgId, 10);
            if (msgId && msgId <= upToId) {
                el.innerHTML = '<i class="fa-solid fa-check-double msg-status--seen" title="Seen"></i>';
            }
        });
    }

    /* ── Render a message bubble ───────────────────────────────── */
    function appendMessage(m) {
        // Remove empty state if present
        var empty = thread.querySelector('.chat-empty');
        if (empty) empty.remove();

        var isGrouped = isGroupedWithPrev(m.is_mine);

        var row = document.createElement('div');
        row.className = 'chat-msg chat-msg--new ' +
                        (m.is_mine ? 'chat-msg--mine' : 'chat-msg--theirs') +
                        (isGrouped ? ' chat-msg--grouped' : '');
        row.setAttribute('data-id', m.id);

        // Resolve avatar
        var avatarUrl = m.avatar_url ||
                        (m.is_mine ? cfg.myAvatarUrl : cfg.otherAvatarUrl) || '';
        var avatarContent = avatarUrl
            ? '<img src="' + avatarUrl + '" alt="" style="width:100%;height:100%;object-fit:cover;">'
            : escHtml(m.avatar || (m.is_mine ? cfg.myAvatar : cfg.otherAvatar));

        var avatarHtml = '<div class="chat-msg__avatar ' +
            (m.is_mine ? 'chat-msg__avatar--mine' : '') + '">' +
            avatarContent + '</div>';

        var displayTime = m.created_at ? localTime(m.created_at) : (m.time || '');

        // Status indicator (own messages only)
        var statusHtml = '';
        if (m.is_mine) {
            var alreadySeen = m.is_read || (typeof m.id === 'number' && m.id <= lastSeenId);
            var icon;
            if (m.sending) {
                icon = '<i class="fa-regular fa-clock msg-status--sending" title="Sending…"></i>';
            } else if (alreadySeen) {
                icon = '<i class="fa-solid fa-check-double msg-status--seen" title="Seen"></i>';
            } else {
                icon = '<i class="fa-solid fa-check msg-status--sent" title="Sent"></i>';
            }
            statusHtml = '<div class="chat-msg__status"' +
                (m.sending ? '' : ' data-msg-id="' + m.id + '"') +
                '>' + icon + '</div>';
        }

        var bubbleInner = '';
        if (m.image_url) {
            bubbleInner +=
                '<a href="' + m.image_url + '" target="_blank" rel="noopener" class="chat-msg__image-link">' +
                '<img src="' + m.image_url + '" alt="" class="chat-msg__image" loading="lazy"></a>';
        }
        if (m.text) {
            bubbleInner += '<span class="chat-msg__text">' + escHtml(m.text) + '</span>';
        }

        row.innerHTML =
            avatarHtml +
            '<div>' +
            '  <div class="chat-msg__bubble">' + bubbleInner + '</div>' +
            '  <div class="chat-msg__footer">' +
            '    <div class="chat-msg__time">' + displayTime + '</div>' +
                 statusHtml +
            '  </div>' +
            '</div>';

        // Insert a date divider if the date changed
        var typing  = document.getElementById('chatTyping');
        var msgDate = localDate(m.created_at || new Date());
        if (msgDate !== lastDateInThread()) {
            thread.insertBefore(makeDivider(msgDate), typing);
        }
        thread.insertBefore(row, typing);
    }

    /* ── Grouping: same sender as previous message? ────────────── */
    function isGroupedWithPrev(isMine) {
        var msgs = thread.querySelectorAll('.chat-msg');
        if (!msgs.length) return false;
        var last = msgs[msgs.length - 1];
        return isMine ? last.classList.contains('chat-msg--mine')
                      : last.classList.contains('chat-msg--theirs');
    }

    /* ── Scroll helpers ────────────────────────────────────────── */
    function scrollToBottom() {
        thread.scrollTop = thread.scrollHeight;
    }

    function isAtBottom() {
        return thread.scrollHeight - thread.scrollTop - thread.clientHeight < 80;
    }

    /* ── Time / Date helpers (always browser-local timezone) ──── */
    var MONTHS = ['Jan','Feb','Mar','Apr','May','Jun',
                  'Jul','Aug','Sep','Oct','Nov','Dec'];

    function nowTime() { return localTime(new Date()); }

    function localTime(src) {
        var d = (src instanceof Date) ? src : new Date(src);
        return ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
    }

    function localDate(src) {
        var d = (src instanceof Date) ? src : new Date(src);
        return MONTHS[d.getMonth()] + ' ' + ('0' + d.getDate()).slice(-2) + ', ' + d.getFullYear();
    }

    function lastDateInThread() {
        var dividers = thread.querySelectorAll('.chat-date-divider[data-date]');
        return dividers.length ? dividers[dividers.length - 1].getAttribute('data-date') : null;
    }

    function makeDivider(dateStr) {
        var el = document.createElement('div');
        el.className = 'chat-date-divider';
        el.setAttribute('data-date', dateStr);
        el.textContent = dateStr;
        return el;
    }

    /* ── XSS guard ─────────────────────────────────────────────── */
    function escHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/\n/g, '<br>');
    }

    /* ── Boot ──────────────────────────────────────────────────── */
    // Convert server-rendered times (UTC ISO → browser local)
    thread.querySelectorAll('.chat-msg__time[data-ts]').forEach(function (el) {
        el.textContent = localTime(el.getAttribute('data-ts'));
    });

    // Insert date dividers between server-rendered messages
    (function insertServerDividers() {
        var msgs = thread.querySelectorAll('.chat-msg[data-ts]');
        var prev = null;
        msgs.forEach(function (msg) {
            var date = localDate(msg.getAttribute('data-ts'));
            if (date !== prev) {
                msg.parentNode.insertBefore(makeDivider(date), msg);
                prev = date;
            }
        });
    }());

    // Apply initial seen state from server (marks messages seen at page load)
    if (lastSeenId) updateSeenIndicators(lastSeenId);

    scrollToBottom();
    setTimeout(poll, POLL_MS);

}());
