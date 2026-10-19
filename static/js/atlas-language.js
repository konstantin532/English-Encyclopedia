/* The Language Atlas — progressive grammatical discovery for the homepage.
 * The original phrase and linguistic markers remain intact, even without JS.
 */
(function (global) {
  "use strict";
  const ROLES = Object.freeze({
    subject: "I — это подлежащее: я, тот, о ком говорится.",
    be: "'m — сокращённая форма am от глагола be. Она связывает I и home.",
    place: "home — здесь означает «дома», без предлога at."
  });
  function describeRole(role) {
    return Object.prototype.hasOwnProperty.call(ROLES, role) ? ROLES[role] : null;
  }
  function canAnimate(mode, reduced) {
    return mode === "full" && !reduced;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { ROLES, describeRole, canAnimate };
  }
  if (!global || !global.document) return;
  const doc = global.document;
  const root = doc.documentElement;
  const reduced = global.matchMedia ? global.matchMedia("(prefers-reduced-motion: reduce)") : { matches: true };
  function enhance(card) {
    const note = card.querySelector("[data-atlas-explanation]");
    const roles = Array.from(card.querySelectorAll("[data-atlas-role]"));
    if (!note || roles.length !== 3) return;
    const original = note.textContent;
    roles.forEach(function (label) {
      const role = label.dataset.atlasRole;
      if (!describeRole(role)) return;
      const button = doc.createElement("button");
      button.type = "button";
      button.className = "atlas-grammar-control";
      button.textContent = label.textContent;
      button.dataset.atlasRole = role;
      button.setAttribute("aria-controls", note.id);
      button.setAttribute("aria-pressed", "false");
      button.addEventListener("click", function () {
        const active = card.dataset.atlasFocus === role;
        if (active) delete card.dataset.atlasFocus;
        else card.dataset.atlasFocus = role;
        note.textContent = active ? original : describeRole(role);
        card.querySelectorAll("button[data-atlas-role]").forEach(function (control) {
          control.setAttribute("aria-pressed", String(!active && control.dataset.atlasRole === role));
        });
        if (!active && canAnimate(root.dataset.motion, reduced.matches) && global.gsap) {
          global.gsap.fromTo(note, { opacity: 0.75 }, { opacity: 1, duration: 0.2, ease: "power2.out", overwrite: "auto",
            onComplete: function () { global.gsap.set(note, { clearProps: "opacity" }); } });
        }
      });
      label.replaceWith(button);
    });
  }
  function init() {
    doc.querySelectorAll("[data-language-atlas]").forEach(enhance);
  }
  if (doc.readyState === "loading") doc.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})(typeof window !== "undefined" ? window : null);
