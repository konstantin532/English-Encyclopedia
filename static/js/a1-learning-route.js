/* Complete A1 explanations. Old depth preferences never hide lesson text.
 * Only top-level explanation sections and their contents links are normalized.
 * Exercise answers, player variants and other reading modes are untouched. */
(function (global) {
  "use strict";
  function init(doc) {
    const root = doc.querySelector("[data-a1-full-lesson]");
    if (!root) return;
    const reader = root.querySelector("[data-lesson-reader]");
    if (!reader) return;
    Array.from(reader.querySelectorAll("section.layer")).forEach(function (section) {
      if (!/^layer-[1-7]$/.test(section.id) &&
          section.id !== "sound-notes" && section.id !== "contractions") return;
      section.hidden = false;
      section.removeAttribute("aria-hidden");
      section.style.removeProperty("display");
    });
    Array.from(root.querySelectorAll(".toc a[href^='#layer-']")).forEach(function (link) {
      if (!/^#layer-[1-7]$/.test(link.hash)) return;
      link.removeAttribute("aria-disabled");
      link.removeAttribute("tabindex");
    });
  }
  if (typeof module !== "undefined" && module.exports) module.exports = { init };
  if (typeof document !== "undefined" && typeof window !== "undefined") {
    if (document.readyState === "loading")
      document.addEventListener("DOMContentLoaded", function () { init(document); });
    else init(document);
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
