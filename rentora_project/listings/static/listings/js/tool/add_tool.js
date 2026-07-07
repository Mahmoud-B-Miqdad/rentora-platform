// ── Tab Switching ─────────────────────────────────────────────────────────────

const tabs   = document.querySelectorAll('.step-tab');
const panels = document.querySelectorAll('.tab-panel');

function activateTab(targetId) {
    tabs.forEach(t => t.classList.toggle('active', t.dataset.target === targetId));
    panels.forEach(p => p.classList.toggle('hidden', p.id !== targetId));
}

tabs.forEach(tab => {
    tab.addEventListener('click', () => activateTab(tab.dataset.target));
});

// "Continue" button → switch to images panel
document.getElementById('btnNext').addEventListener('click', () => {
    activateTab('panelImages');
    window.scrollTo({ top: 0, behavior: 'smooth' });
});


// ── Character Counter ─────────────────────────────────────────────────────────

const descTA   = document.getElementById('id_description');
const charSpan = document.getElementById('charCount');

if (descTA && charSpan) {
    charSpan.textContent = descTA.value.length;
    descTA.addEventListener('input', () => {
        charSpan.textContent = descTA.value.length;
    });
}


// ── Condition Buttons ─────────────────────────────────────────────────────────

const condBtns  = document.querySelectorAll('.cond-btn');
const condInput = document.getElementById('conditionInput');

condBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        condBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        condInput.value = btn.dataset.value;
    });
});


// ── Image Drag & Drop + Preview ───────────────────────────────────────────────

const dropZone   = document.getElementById('dropZone');
const imageInput = document.getElementById('imageInput');
const browseBtn  = document.getElementById('browseBtn');
const previewGrid = document.getElementById('previewGrid');
const imgCounter  = document.getElementById('imgCounter');

const MAX_IMAGES = 8;
let dt = new DataTransfer();

// Open file browser
browseBtn.addEventListener('click', e => { e.stopPropagation(); imageInput.click(); });
dropZone.addEventListener('click', () => imageInput.click());

// File input change (browser dialog)
imageInput.addEventListener('change', function () {
    addFiles(Array.from(this.files));
    this.value = '';          // reset so the same file can be re-added if removed
});

// Drag events
dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    addFiles(Array.from(e.dataTransfer.files));
});

function addFiles(files) {
    files.forEach(file => {
        if (!file.type.startsWith('image/')) return;
        if (dt.files.length >= MAX_IMAGES) {
            alert(`You can upload a maximum of ${MAX_IMAGES} images.`);
            return;
        }
        dt.items.add(file);
    });
    imageInput.files = dt.files;
    renderPreviews();
    updateCounter();
}

function removeFile(idx) {
    const newDt = new DataTransfer();
    Array.from(dt.files).forEach((f, i) => { if (i !== idx) newDt.items.add(f); });
    dt = newDt;
    imageInput.files = dt.files;
    renderPreviews();
    updateCounter();
}

function updateCounter() {
    const n = dt.files.length;
    imgCounter.textContent = n > 0 ? `${n} / ${MAX_IMAGES} image${n !== 1 ? 's' : ''} selected` : '';
}

function renderPreviews() {
    previewGrid.innerHTML = '';
    Array.from(dt.files).forEach((file, i) => {
        const reader = new FileReader();
        reader.onload = e => {
            const item = document.createElement('div');
            item.className = 'preview-item' + (i === 0 ? ' preview-primary' : '');
            item.innerHTML = `
                <img src="${e.target.result}" alt="">
                <button type="button" class="preview-remove" title="Remove">
                    <i class="fa-solid fa-xmark"></i>
                </button>
                ${i === 0 ? '<span class="preview-badge">Cover</span>' : ''}
            `;
            item.querySelector('.preview-remove').addEventListener('click', e => {
                e.stopPropagation();
                removeFile(i);
            });
            previewGrid.appendChild(item);
        };
        reader.readAsDataURL(file);
    });
}


// ── AI Placeholder Alerts ─────────────────────────────────────────────────────

document.getElementById('btnAI')?.addEventListener('click', () =>
    alert('AI Description Generator — coming soon!')
);
document.getElementById('btnSuggest')?.addEventListener('click', () =>
    alert('AI Price Suggestion — coming soon!')
);
document.getElementById('btnDetect')?.addEventListener('click', () =>
    alert('AI Condition Detection — coming soon!')
);
