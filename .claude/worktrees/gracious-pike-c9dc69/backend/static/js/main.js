document.addEventListener("DOMContentLoaded", function () {
  // Mobile menu toggle
  var btn = document.getElementById("mobile-menu-btn");
  var nav = document.getElementById("mobile-nav");
  if (btn && nav) {
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      nav.classList.toggle("open");
    });
    document.addEventListener("click", function () {
      nav.classList.remove("open");
    });
    nav.addEventListener("click", function (e) {
      e.stopPropagation();
    });
  }

  // Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener("click", function (e) {
      var target = document.querySelector(this.getAttribute("href"));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: "smooth" });
      }
    });
  });
});
