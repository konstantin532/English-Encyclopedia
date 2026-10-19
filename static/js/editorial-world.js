/* Living Language: scene accents and player atmosphere.
 * The existing motion-system owns content animations. This module only animates
 * decorative bookplate strokes, never content or layout.
 */
(function (global) {
  "use strict";
  const SIGNATURES = ".studio-home-hero, .week-hero, .studio-specimen-section .specimen, .story-player, .entry .example, .independent-result";
  function allowsOrnamentMotion(mode, reduced, forced) {
    return mode === "full" && !reduced && !forced;
  }
  function isPlaying(pressed) {
    return pressed === "true";
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { SIGNATURES, allowsOrnamentMotion, isPlaying };
  }
  if (!global || !global.document) return;
  const doc = global.document;
  const root = doc.documentElement;
  const reduced = global.matchMedia ? global.matchMedia("(prefers-reduced-motion: reduce)") : { matches: true };
  const contrast = global.matchMedia ? global.matchMedia("(forced-colors: active)") : { matches: false };
  const seen = new WeakSet();
  let sceneObserver = null;
  let playerObserver = null;
  let rootObserver = null;
  let strokeTargets = [];
  let activeStrokes = [];
  let enabled = false;

  function canAnimate() {
    return allowsOrnamentMotion(root.dataset.motion, reduced.matches, contrast.matches) && !!global.gsap && !doc.hidden;
  }
  function stop() {
    activeStrokes.forEach(function (el) {
      if (global.gsap) {
        global.gsap.killTweensOf(el);
        global.gsap.set(el, { clearProps: "transform,opacity" });
      }
    });
    activeStrokes = [];
  }
  function updateMode() {
    enabled = canAnimate();
    if (!enabled) stop();
  }
  function paintStroke(target) {
    if (seen.has(target)) return;
    seen.add(target);
    const stroke = target.querySelector(":scope > .editorial-ornament");
    if (!stroke || !enabled) return;
    activeStrokes.push(stroke);
    global.gsap.fromTo(stroke, { scaleX: 0.06, opacity: 0.3 }, {
      scaleX: 1, opacity: 1, duration: 0.6, ease: "power2.out",
      overwrite: "auto",
      onComplete: function () {
        global.gsap.set(stroke, { clearProps: "transform,opacity" });
        activeStrokes = activeStrokes.filter(function (item) { return item !== stroke; });
      }
    });
  }
  function decorate() {
    strokeTargets = Array.from(doc.querySelectorAll(SIGNATURES));
    strokeTargets.forEach(function (target) {
      if (target.querySelector(":scope > .editorial-ornament")) return;
      const stroke = doc.createElement("span");
      stroke.className = "editorial-ornament";
      stroke.setAttribute("aria-hidden", "true");
      target.appendChild(stroke);
    });
  }
  function connectScenes() {
    if (!strokeTargets.length) return;
    if (!global.IntersectionObserver) {
      strokeTargets.forEach(paintStroke);
      return;
    }
    sceneObserver = new global.IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        sceneObserver.unobserve(entry.target);
        paintStroke(entry.target);
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -24px 0px" });
    strokeTargets.forEach(function (target) { sceneObserver.observe(target); });
  }
  function setPlayerState(player, button) {
    if (isPlaying(button.getAttribute("aria-pressed"))) {
      player.dataset.editorialPlaying = "true";
    } else {
      delete player.dataset.editorialPlaying;
    }
  }
  function connectPlayers() {
    if (!global.MutationObserver) return;
    const buttons = Array.from(doc.querySelectorAll(".story-player [data-play]"));
    if (!buttons.length) return;
    buttons.forEach(function (button) {
      const player = button.closest(".story-player");
      if (player) setPlayerState(player, button);
    });
    playerObserver = new global.MutationObserver(function (records) {
      records.forEach(function (record) {
        const button = record.target;
        const player = button.closest(".story-player");
        if (player) setPlayerState(player, button);
      });
    });
    buttons.forEach(function (button) {
      playerObserver.observe(button, { attributes: true, attributeFilter: ["aria-pressed"] });
    });
  }
  function dispose() {
    stop();
    if (sceneObserver) sceneObserver.disconnect();
    if (playerObserver) playerObserver.disconnect();
    if (rootObserver) rootObserver.disconnect();
    sceneObserver = playerObserver = rootObserver = null;
  }
  function connect() {
    updateMode();
    connectScenes();
    connectPlayers();
    if (global.MutationObserver) {
      rootObserver = new global.MutationObserver(updateMode);
      rootObserver.observe(root, { attributes: true, attributeFilter: ["data-motion"] });
    }
  }
  function init() {
    decorate();
    connect();
    [reduced, contrast].forEach(function (media) {
      if (media.addEventListener) media.addEventListener("change", updateMode);
    });
    doc.addEventListener("visibilitychange", updateMode);
    global.addEventListener("pagehide", dispose);
    global.addEventListener("pageshow", function (event) {
      if (event.persisted) connect();
    });
  }
  if (doc.readyState === "loading") doc.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})(typeof window !== "undefined" ? window : null);
