// Маркеры: подсказка с классом при наведении/фокусе и переключатель «в цвете / без цвета».
(() => {
  const root = document.documentElement;

  function csrf() {
    const m = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  // --- Переключатель цвета ---
  const toggle = document.querySelector("[data-markers-toggle]");
  const sync = () => toggle && toggle.setAttribute("aria-pressed", String(root.dataset.markers !== "mono"));
  sync();
  toggle?.addEventListener("click", () => {
    const mono = root.dataset.markers !== "mono";
    if (mono) root.dataset.markers = "mono"; else delete root.dataset.markers;
    sync();
    try { localStorage.setItem("ee-markers", mono ? "mono" : "color"); } catch (e) { /* хранилище недоступно */ }
    const url = toggle.dataset.saveUrl;
    if (url) fetch(url, { method: "POST", headers: { "X-CSRFToken": csrf(), "X-Requested-With": "fetch" } });
  });

  // --- Подсказка у маркера ---
  const tip = document.createElement("div");
  tip.className = "mk-tip";
  tip.setAttribute("role", "tooltip");
  document.body.appendChild(tip);

  function show(el) {
    const label = el.dataset.label;
    if (!label) return;
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

  document.querySelectorAll(".mk[data-label]").forEach((el) => {
    if (!el.closest("a, button")) el.tabIndex = 0;
  });
  document.addEventListener("pointerover", (e) => { const el = e.target.closest?.(".mk[data-label]"); el ? show(el) : hide(); });
  document.addEventListener("focusin", (e) => { const el = e.target.closest?.(".mk[data-label]") || e.target.querySelector?.(":scope > .mk[data-label]"); el ? show(el) : hide(); });
  document.addEventListener("focusout", hide);
  window.addEventListener("scroll", hide, { passive: true });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") hide(); });
})();
