/* Editorial light interactions for English Encyclopedia.
 * Presentation-only enhancement; no changes to content or navigation.
 */
(function (global) {
  "use strict";
  const TARGETS = ".studio-home-hero, .studio-lesson-card, .studio-word-card, .week-card";
  function canIlluminate(mode, reduced, forced, finePointer) {
    return finePointer && !reduced && !forced && (mode === "full" || mode === "balanced");
  }
  function relativeLight(x, y, rect) {
    const width = Math.max(1, rect.width);
    const height = Math.max(1, rect.height);
    const clamp = function (n) { return Math.max(0, Math.min(100, Math.round(n))); };
    return { x: clamp(((x - rect.left) / width) * 100) + "%",
      y: clamp(((y - rect.top) / height) * 100) + "%" };
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { canIlluminate, relativeLight, TARGETS };
  }
  if (!global || !global.document) return;
  const doc = global.document;
  const root = doc.documentElement;
  const fine = global.matchMedia ? global.matchMedia("(hover: hover) and (pointer: fine)") : { matches: false };
  const reduced = global.matchMedia ? global.matchMedia("(prefers-reduced-motion: reduce)") : { matches: true };
  const forced = global.matchMedia ? global.matchMedia("(forced-colors: active)") : { matches: false };
  let hot = null;
  let pending = null;
  let frame = 0;
  let enabled = false;

  function clear() {
    pending = null;
    if (frame && global.cancelAnimationFrame) global.cancelAnimationFrame(frame);
    frame = 0;
    if (hot) {
      hot.removeAttribute("data-art-hot");
      hot.style.removeProperty("--art-light-x");
      hot.style.removeProperty("--art-light-y");
      hot = null;
    }
  }
  function sync() {
    enabled = canIlluminate(root.dataset.motion, reduced.matches, forced.matches, fine.matches);
    if (enabled) root.dataset.artInteractive = "on";
    else {
      delete root.dataset.artInteractive;
      clear();
    }
  }
  function apply() {
    frame = 0;
    if (!enabled || !pending || pending.target !== hot || !hot.isConnected) return;
    const coords = relativeLight(pending.x, pending.y, hot.getBoundingClientRect());
    hot.style.setProperty("--art-light-x", coords.x);
    hot.style.setProperty("--art-light-y", coords.y);
    pending = null;
  }
  function pointerMove(event) {
    if (!enabled || (event.pointerType && event.pointerType !== "mouse")) return;
    const target = event.target.closest && event.target.closest(TARGETS);
    if (!target || !doc.contains(target)) {
      clear();
      return;
    }
    if (hot !== target) {
      clear();
      hot = target;
      hot.setAttribute("data-art-hot", "true");
    }
    pending = { target: target, x: event.clientX, y: event.clientY };
    if (!frame && global.requestAnimationFrame) frame = global.requestAnimationFrame(apply);
  }
  function pointerOut(event) {
    if (!hot) return;
    if (event.relatedTarget && hot.contains(event.relatedTarget)) return;
    const destination = event.relatedTarget?.closest?.(TARGETS);
    if (destination !== hot) clear();
  }
  function init() {
    sync();
    doc.addEventListener("pointermove", pointerMove, { passive: true });
    doc.addEventListener("pointerout", pointerOut, { passive: true });
    global.addEventListener("blur", clear);
    global.addEventListener("pagehide", clear);
    global.addEventListener("pageshow", sync);
    [fine, reduced, forced].forEach(function (mq) {
      if (mq.addEventListener) mq.addEventListener("change", sync);
      else if (mq.addListener) mq.addListener(sync);
    });
    if (global.MutationObserver) {
      const observer = new global.MutationObserver(sync);
      observer.observe(root, { attributes: true, attributeFilter: ["data-motion"] });
    }
  }
  if (doc.readyState === "loading") doc.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})(typeof window !== "undefined" ? window : null);
