(() => {
  const storageKey = "codegarden-theme";
  const root = document.documentElement;
  const toggles = Array.from(document.querySelectorAll("[data-theme-toggle]"));

  function applyTheme(value) {
    if (value === "light") {
      root.classList.add("theme-light");
    } else {
      root.classList.remove("theme-light");
    }
  }

  const saved = localStorage.getItem(storageKey);
  applyTheme(saved);

  if (!toggles.length) {
    return;
  }

  function syncToggles(isLight) {
    toggles.forEach((toggle) => {
      toggle.setAttribute("aria-pressed", String(isLight));
      const label = toggle.querySelector("[data-theme-label]");
      if (label) {
        label.textContent = isLight ? "Jasny" : "Ciemny";
      }
    });
  }

  toggles.forEach((toggle) => {
    toggle.addEventListener("click", () => {
      const isLight = root.classList.toggle("theme-light");
      localStorage.setItem(storageKey, isLight ? "light" : "dark");
      syncToggles(isLight);
    });
  });

  syncToggles(root.classList.contains("theme-light"));
})();
