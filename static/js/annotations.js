// Видимость маркеров; сохранённый выбор цвета остаётся отдельной настройкой.
(() => {
  const root = document.documentElement;

  function csrf() {
    const m = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  const toggle = document.querySelector("[data-markers-toggle]");
  const status = document.querySelector("[data-markers-status]");
  const isEnabled = () => root.dataset.markers !== "off";
  const apply = enabled => {
    root.dataset.markers = enabled ? (root.dataset.markersColor === "mono" ? "mono" : "color") : "off";
    toggle?.setAttribute("aria-pressed", String(enabled));
  };
  apply(isEnabled());
  let saving = false;
  toggle?.addEventListener("click", async () => {
    if (saving) return;
    const previous = isEnabled();
    const enabled = !previous;
    apply(enabled);
    refreshFocus(); hide();
    const url = toggle.dataset.saveUrl;
    if (!url) {
      try {
        localStorage.setItem("ee-markers-enabled", String(enabled));
        localStorage.setItem("ee-markers", root.dataset.markersColor === "mono" ? "mono" : "color");
      } catch (e) { /* Режим работает и без доступа к хранилищу. */ }
      return;
    }
    saving = true; toggle.disabled = true;
    try {
      const res = await fetch(url, {
        method: "POST", credentials: "same-origin",
        headers: {"X-CSRFToken": csrf(), "X-Requested-With": "fetch", "Content-Type": "application/x-www-form-urlencoded"},
        body: "enabled=" + String(enabled),
      });
      if (!res.ok) throw new Error("Unable to save marker preference");
      const result = await res.json();
      if (typeof result.enabled !== "boolean") throw new Error("Invalid marker preference");
      apply(result.enabled);
      if (status) status.textContent = "";
    } catch (e) {
      apply(previous);
      if (status) status.textContent = "Не удалось сохранить выбор. Попробуйте ещё раз.";
    } finally {
      saving = false; toggle.disabled = false; refreshFocus();
    }
  });

  // --- Подсказка у маркера ---
  const tip = document.createElement("div");
  tip.className = "mk-tip";
  tip.setAttribute("role", "tooltip");
  document.body.appendChild(tip);

  function show(el) {
    const label = el.dataset.label;
    if (!label || (!isEnabled() && !el.closest("[data-language-atlas]"))) { hide(); return; }
    tip.textContent = label;
    const r = el.getBoundingClientRect();
    tip.style.left = "0px";
    tip.style.top = "0px";
    tip.setAttribute("data-show", "");
    const w = tip.offsetWidth;
    const x = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), window.innerWidth - w - 8);
    tip.style.left = `${x + window.scrollX}px`;
    tip.style.top = `${r.top + window.scrollY - tip.offsetHeight - 10}px`;
  }
  const hide = () => tip.removeAttribute("data-show");

  function refreshFocus() {
    document.querySelectorAll(".mk[data-label]").forEach(el => {
      if (el.closest("a, button, [data-language-atlas]")) return;
      if (isEnabled()) el.tabIndex = 0; else el.removeAttribute("tabindex");
    });
  }
  refreshFocus();
  document.addEventListener("pointerover", (e) => { const el = e.target.closest?.(".mk[data-label]"); el ? show(el) : hide(); });
  document.addEventListener("focusin", (e) => { const el = e.target.closest?.(".mk[data-label]") || e.target.querySelector?.(":scope > .mk[data-label]"); el ? show(el) : hide(); });
  document.addEventListener("focusout", hide);
  window.addEventListener("scroll", hide, { passive: true });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") hide(); });
})();
