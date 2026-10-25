/* Optional reading routes for all 28 A1 lessons.
 * All seven original layers remain available and visible by default.
 * No audio, grading, learner progress, or lesson content is changed.
 */
(function (global) {
  "use strict";

  const ROUTES = Object.freeze({
    essentials: [1, 3, 5, 7],
    reasons: [1, 2, 3, 4, 5, 7],
    full: [1, 2, 3, 4, 5, 6, 7],
  });

  function showSection(mode, id) {
    const allowed = ROUTES[mode];
    if (!allowed) return true; // Unknown mode fails open, never loses the lesson.
    if (id === "sound-notes" || id === "contractions") return true;
    const match = /^layer-([1-7])$/.exec(String(id || ""));
    return !match || allowed.includes(Number(match[1]));
  }

  function init(doc, win) {
    const guide = doc.querySelector("[data-a1-learning-route]");
    const reader = doc.querySelector("[data-lesson-reader]");
    if (!guide || !reader) return;
    const sections = Array.from(reader.querySelectorAll("section.layer"));
    const buttons = Array.from(guide.querySelectorAll("[data-a1-route-mode]"));
    const message = guide.querySelector("[data-a1-route-status]");
    const bookpage = doc.querySelector("[data-lesson-bookpage]");
    if (!message || sections.filter(s => /^layer-[1-7]$/.test(s.id)).length !== 7 ||
        buttons.length !== 3) return; // Incomplete markup: original view remains unchanged.

    function setMode(mode) {
      if (!ROUTES[mode]) mode = "full";
      sections.forEach(function (section) {
        section.hidden = !showSection(mode, section.id);
      });
      buttons.forEach(function (button) {
        button.setAttribute("aria-pressed", String(button.dataset.a1RouteMode === mode));
      });
      message.textContent = {
        essentials: "Суть: основные примеры, разговорные формы и самостоятельная практика. Остальные шаги доступны в режиме «Полностью».",
        reasons: "Почему: происхождение слов, логика грамматики и примеры. Исключения доступны в режиме «Полностью».",
        full: "Полностью: доступны все семь шагов урока и дополнительная практика.",
      }[mode];
      if (bookpage) {
        message.textContent = {
          essentials: "Суть: показаны 4 из 7 шагов объяснения. Скрыты шаги 2, 4, 6 — откройте «Полностью», чтобы прочитать их. Краткая опора и практика не меняются.",
          reasons: "Почему: показаны 6 из 7 шагов объяснения. Скрыт шаг 6 — откройте «Полностью», чтобы прочитать его. Краткая опора и практика не меняются.",
          full: "Полностью: показаны 7 из 7 шагов объяснения. Краткая опора и практика не меняются.",
        }[mode];
      }
    }

    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        setMode(button.dataset.a1RouteMode);
      });
    });
    // A table-of-contents or deep link must never point into a hidden layer.
    function openLinkedSection() {
      let anchor;
      try { anchor = decodeURIComponent(String(win.location.hash || "").replace(/^#/, "")); }
      catch (_) { return; }
      const target = sections.find(function (section) { return section.id === anchor; });
      if (target && target.hidden) {
        setMode("full");
        if (typeof target.scrollIntoView === "function") target.scrollIntoView();
      }
    }
    win.addEventListener("hashchange", openLinkedSection);
    setMode("full");
    guide.hidden = false; // Progressive enhancement: with JS off, everything stays readable.
    openLinkedSection();
  }

  if (typeof module !== "undefined" && module.exports)
    module.exports = { ROUTES, showSection, init };
  if (typeof document !== "undefined" && typeof window !== "undefined") {
    if (document.readyState === "loading")
      document.addEventListener("DOMContentLoaded", function () { init(document, window); }, {once: true});
    else init(document, window);
  }
})(typeof window !== "undefined" ? window : globalThis);
