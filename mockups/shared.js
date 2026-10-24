(function () {
  const key = "journal-mockup-theme";
  const root = document.documentElement;
  const stored = localStorage.getItem(key);
  if (stored === "light" || stored === "dark") {
    root.setAttribute("data-theme", stored);
  }
  document.querySelectorAll("[data-theme-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const next =
        root.getAttribute("data-theme") === "dark" ||
        (!root.getAttribute("data-theme") &&
          window.matchMedia("(prefers-color-scheme: dark)").matches)
          ? "light"
          : "dark";
      root.setAttribute("data-theme", next);
      localStorage.setItem(key, next);
      btn.textContent = next === "dark" ? "Light appearance" : "Dark appearance";
    });
  });
  const btn = document.querySelector("[data-theme-toggle]");
  if (btn) {
    const dark =
      root.getAttribute("data-theme") === "dark" ||
      (!root.getAttribute("data-theme") &&
        window.matchMedia("(prefers-color-scheme: dark)").matches);
    btn.textContent = dark ? "Light appearance" : "Dark appearance";
  }
})();
