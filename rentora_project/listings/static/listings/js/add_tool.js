// ==========================================
// Character Counter
// ==========================================

const description = document.querySelector("textarea[name='description']");
const counter = document.getElementById("charCount");

if (description && counter) {

    counter.textContent = description.value.length;

    description.addEventListener("input", function () {

        counter.textContent = this.value.length;

    });

}



// ==========================================
// Condition Buttons
// ==========================================

const buttons = document.querySelectorAll(".condition-btn");
const hiddenInput = document.getElementById("conditionInput");

buttons.forEach(button => {

    button.addEventListener("click", function () {

        buttons.forEach(btn => btn.classList.remove("active"));

        this.classList.add("active");

        hiddenInput.value = this.dataset.value;

    });

});



// ==========================================
// Image Preview
// ==========================================

const imageInput = document.querySelector("input[type='file']");

if (imageInput) {

    // إنشاء مكان للمعاينة إذا لم يكن موجودًا
    let preview = document.getElementById("previewContainer");

    if (!preview) {

        preview = document.createElement("div");

        preview.id = "previewContainer";

        preview.className = "preview-container";

        imageInput.parentNode.appendChild(preview);

    }

    imageInput.addEventListener("change", function () {

        preview.innerHTML = "";

        const files = Array.from(this.files);

        if (files.length > 8) {

            alert("You can upload a maximum of 8 images.");

            this.value = "";

            return;

        }

        files.forEach(file => {

            if (!file.type.startsWith("image/")) return;

            const reader = new FileReader();

            reader.onload = function (e) {

                const img = document.createElement("img");

                img.src = e.target.result;

                img.className = "preview-image";

                preview.appendChild(img);

            };

            reader.readAsDataURL(file);

        });

    });

}



// ==========================================
// AI Buttons (Temporary)
// ==========================================

const aiBtn = document.querySelector(".ai-btn");

if (aiBtn) {

    aiBtn.addEventListener("click", function () {

        alert("AI Description Generator will be added soon.");

    });

}



const suggestBtn = document.querySelector(".suggest-btn");

if (suggestBtn) {

    suggestBtn.addEventListener("click", function () {

        alert("AI Price Suggestion will be available soon.");

    });

}



const detectBtn = document.querySelector(".detect-btn");

if (detectBtn) {

    detectBtn.addEventListener("click", function () {

        alert("AI Condition Detection will be available soon.");

    });

}
