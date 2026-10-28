/* The Language Atlas: the educational markers remain the source of truth.
 * Explanations live outside the layout, so discovery never moves the chapter below.
 */
(function (global) {
  "use strict";
  const ROLES = Object.freeze({
    subject: "I — «я»: кто говорит.",
    be: "'m — короткая запись am. Здесь помогает сказать «я дома».",
    place: "home — здесь означает «дома», без предлога at."
  });
  function describeRole(role) {
    return Object.prototype.hasOwnProperty.call(ROLES, role) ? ROLES[role] : null;
  }
  function canAnimate(mode, reduced) { return mode === "full" && !reduced; }
  if (typeof module !== "undefined" && module.exports) module.exports = { ROLES, describeRole, canAnimate };
  if (!global || !global.document) return;
  const doc = global.document;
  const reduced = global.matchMedia ? global.matchMedia("(prefers-reduced-motion: reduce)") : { matches: true };
  const selectors = { subject: '[data-cat="T"]', be: '[data-cat="D"]', place: '[data-cat="S"]' };
  function enhance(card, index) {
    const note = card.querySelector("[data-atlas-explanation]");
    const roles = Array.from(card.querySelectorAll("[data-atlas-role]"));
    if (!note || roles.length !== 3 || card.dataset.atlasReady) return;
    card.dataset.atlasReady = "true";
    const panel = doc.createElement("div");
    panel.id = "atlas-discovery-" + index;
    panel.className = "atlas-discovery";
    panel.hidden = true;
    panel.setAttribute("role", "status");
    panel.setAttribute("aria-live", "polite");
    doc.body.appendChild(panel);
    const controls = [];
    let source = null;
    function close() {
      delete card.dataset.atlasFocus;
      panel.hidden = true;
      controls.forEach(function (control) { control.setAttribute("aria-expanded", "false"); });
      if (global.gsap) { global.gsap.killTweensOf(panel); global.gsap.set(panel, { clearProps: "opacity" }); }
      source = null;
    }
    function positionPanel() {
      if (!source) return;
      const anchor = card.getBoundingClientRect();
      const box = panel.getBoundingClientRect();
      panel.style.left = Math.max(16, Math.min(anchor.left, global.innerWidth - box.width - 16)) + "px";
      // Prefer the empty space below the paper; clamp to the viewport on small screens.
      panel.style.top = Math.max(16, Math.min(anchor.bottom + 12, global.innerHeight - box.height - 16)) + "px";
    }
    function reveal(role, control) {
      if (card.dataset.atlasFocus === role) { close(); return; }
      close();
      source = control;
      card.dataset.atlasFocus = role;
      controls.forEach(function (item) { item.setAttribute("aria-expanded", String(item.dataset.atlasRole === role)); });
      panel.textContent = describeRole(role);
      panel.hidden = false;
      positionPanel();
      if (canAnimate(doc.documentElement.dataset.motion, reduced.matches) && global.gsap) {
        global.gsap.fromTo(panel, { opacity: 0.65 }, { opacity: 1, duration: 0.18, overwrite: "auto" });
      }
    }
    function wire(control, role, word) {
      control.dataset.atlasRole = role;
      control.setAttribute("aria-controls", panel.id);
      control.setAttribute("aria-expanded", "false");
      control.setAttribute("aria-label", (word ? control.textContent + ": " : "") + "Объяснить: " + describeRole(role));
      control.addEventListener("click", function () { reveal(role, control); });
      if (word) {
        control.setAttribute("role", "button");
        control.tabIndex = 0;
        control.addEventListener("keydown", function (event) {
          if (event.key === "Enter" || event.key === " ") { event.preventDefault(); reveal(role, control); }
        });
      }
      controls.push(control);
    }
    roles.forEach(function (label) {
      const role = label.dataset.atlasRole;
      if (!describeRole(role)) return;
      const button = doc.createElement("button");
      button.type = "button";
      button.className = "atlas-grammar-control";
      button.textContent = label.textContent;
      wire(button, role, false);
      label.replaceWith(button);
      const word = card.querySelector(".studio-phrase " + selectors[role]);
      if (word) wire(word, role, true);
    });
    doc.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && source) { const previous = source; close(); previous.focus(); }
    });
    doc.addEventListener("pointerdown", function (event) {
      if (!card.contains(event.target) && !panel.contains(event.target)) close();
    });
    doc.addEventListener("focusin", function (event) {
      if (!card.contains(event.target) && !panel.contains(event.target)) close();
    });
    global.addEventListener("resize", close, { passive: true });
    global.addEventListener("scroll", positionPanel, { passive: true, capture: true });
    if (reduced.addEventListener) reduced.addEventListener("change", close);
    // Existing motion settings own the lifecycle; switching modes cancels local motion.
    if (global.MutationObserver) new global.MutationObserver(close).observe(doc.documentElement, { attributes: true, attributeFilter: ["data-motion"] });
  }
  function init() { doc.querySelectorAll("[data-language-atlas]").forEach(enhance); }
  if (doc.readyState === "loading") doc.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})(typeof window !== "undefined" ? window : null);
