/* Progressive enhancement for slow Android networks and rapid double taps.
 * Does not store learner answers in localStorage or send them elsewhere.
 * Server-side single-use batch tokens remain the authoritative protection.
 */
(function (root) {
  "use strict";
  function init(doc, win) {
    const error = doc.querySelector(".independent-form-error[role='alert']");
    // A server-rendered 400 should land screen readers on the explanation,
    // not leave TalkBack at the top with the previous failed answers hidden.
    if (error && typeof error.focus === "function") error.focus();
    const form = doc.querySelector("[data-blind-batch]");
    if (!form) return;
    const button = form.querySelector("[data-batch-submit]");
    const status = form.querySelector("[data-batch-status]");
    if (!button || !status) return;
    let sending = false;
    const originalLabel = button.textContent;
    function restore() {
      sending = false;
      button.disabled = false;
      button.textContent = originalLabel;
      status.textContent = "";
    }
    form.addEventListener("submit", function (event) {
      if (sending) {
        event.preventDefault();
        return;
      }
      sending = true;
      button.disabled = true;
      button.textContent = "Отправляем ответы…";
      status.textContent = "Четыре ответа отправляются. Не нажимайте повторно.";
    });
    // Mobile browsers may restore forms from back-forward cache.
    win.addEventListener("pageshow", restore);
  }
  if (typeof module !== "undefined" && module.exports) module.exports = { init };
  if (typeof document !== "undefined" && typeof window !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", function () { init(document, window); }, {once: true});
    } else {
      init(document, window);
    }
  }
})(typeof window !== "undefined" ? window : globalThis);
