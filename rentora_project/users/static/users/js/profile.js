/* profile.js */

/* ── Avatar image preview ──────────────────────────────────── */
var fileInput = document.getElementById('f-img');
if (fileInput) {
    fileInput.addEventListener('change', function () {
        var file = this.files && this.files[0];
        if (!file) return;

        var reader = new FileReader();
        reader.onload = function (e) {
            var src = e.target.result;

            // If an <img> already exists, just update its src
            var existing = document.getElementById('avatarPreview');
            if (existing) {
                existing.src = src;
                return;
            }

            // Otherwise replace the initials <div> with an <img>
            var initDiv = document.getElementById('avatarInitDiv');
            if (initDiv) {
                var img = document.createElement('img');
                img.src       = src;
                img.alt       = '';
                img.className = 'profile-avatar';
                img.id        = 'avatarPreview';
                initDiv.parentNode.replaceChild(img, initDiv);
            }
        };
        reader.readAsDataURL(file);
    });
}

/* ── Review tab switching ──────────────────────────────────── */
document.querySelectorAll('.review-tab').forEach(function (tab) {
    tab.addEventListener('click', function () {
        document.querySelectorAll('.review-tab').forEach(function (t) {
            t.classList.remove('review-tab--active');
            t.setAttribute('aria-selected', 'false');
        });
        document.querySelectorAll('.review-panel').forEach(function (p) {
            p.hidden = true;
        });

        tab.classList.add('review-tab--active');
        tab.setAttribute('aria-selected', 'true');
        var panel = document.getElementById('tab-' + tab.dataset.tab);
        if (panel) panel.hidden = false;
    });
});

function toggleReportForm() {
	const form = document.getElementById('report-form');
	form.style.display = form.style.display === 'none' ? 'block' : 'none';
}