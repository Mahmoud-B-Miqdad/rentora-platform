document.addEventListener('DOMContentLoaded', function () {
 
    // ==================================================
    // Condition buttons
    // ==================================================
 
    const conditionButtons = document.querySelectorAll('.condition-btn');
    const conditionInput   = document.getElementById('conditionInput');
 
    conditionButtons.forEach(function (btn) {
        btn.addEventListener('click', function () {
            conditionButtons.forEach(function (b) { b.classList.remove('active'); });
            btn.classList.add('active');
            conditionInput.value = btn.dataset.value;
        });
    });
 
 
    // ==================================================
    // Description character counter + minimum-length hint
    // ==================================================
 
    const descriptionField = document.getElementById('descriptionField');
    const charCount        = document.getElementById('charCount');
    const minCharWarning   = document.getElementById('minCharWarning');
 
    const MIN_DESCRIPTION_LENGTH = 20;
 
    function updateCharCount() {
        const length = descriptionField.value.length;
        charCount.textContent = length;
 
        if (length > 0 && length < MIN_DESCRIPTION_LENGTH) {
            minCharWarning.textContent =
                ' — at least ' + MIN_DESCRIPTION_LENGTH + ' characters required (' +
                (MIN_DESCRIPTION_LENGTH - length) + ' more needed)';
            minCharWarning.classList.add('visible');
        } else {
            minCharWarning.textContent = '';
            minCharWarning.classList.remove('visible');
        }
    }
 
    if (descriptionField && charCount) {
        descriptionField.addEventListener('input', updateCharCount);
        updateCharCount(); // run once on load in case of pre-filled value
    }
 
});