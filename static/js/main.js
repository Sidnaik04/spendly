// main.js — vanilla JS only

// Render Lucide icons (<i data-lucide="...">); pages still work if the CDN fails
document.addEventListener("DOMContentLoaded", function () {
    if (window.lucide) {
        window.lucide.createIcons();
    }
});
