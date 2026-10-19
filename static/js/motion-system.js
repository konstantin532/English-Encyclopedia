/* Living Language Cinema — enhancement only; content is visible without JS. */
(function (global) {
  "use strict";
  const KEY = "ee-motion-mode";
  const MODES = ["full", "balanced", "minimal"];
  const SELECTORS = {
    cards: ".week-card, .studio-lesson-card, .studio-word-card, .studio-note, .map-item, .a1-mission-previews li",
    feedback: ".active-a1-feedback, .active-a1-model, [data-stress-feedback], [data-speech-feedback], [data-a1-builder-result], [data-a1-mission-result], .drill-hint",
    scenes: ".studio-home-heading h1, .studio-home-heading p, .studio-hero-copy .studio-eyebrow, .studio-hero-copy h2, .studio-hero-copy > p, .studio-hero-copy .hero-actions, .studio-hero-art"
  };

  function effectiveMode(saved, reduced) {
    return reduced ? "minimal" : MODES.includes(saved) ? saved : "balanced";
  }
  function shouldAnimate(mode, kind) {
    return mode === "full" || (mode === "balanced" && kind !== "signature");
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { effectiveMode, shouldAnimate, MODES, SELECTORS };
  }
  if (!global || !global.document) return;
  const doc = global.document;
  const root = doc.documentElement;
  const media = global.matchMedia ? global.matchMedia("(prefers-reduced-motion: reduce)") : { matches: false };
  const observers = [];
  const active = new Set();
  let mode;
  let started = false;
  let controls = [];
  let introTimeline = null;

  function readSaved() {
    try { return global.localStorage.getItem(KEY); } catch (_) { return null; }
  }
  function writeSaved(value) {
    try { global.localStorage.setItem(KEY, value); } catch (_) { /* storage may be blocked */ }
  }
  function refresh(next, save) {
    const requested = MODES.includes(next) ? next : "balanced";
    if (media.matches) {
      mode = "minimal";
      if (save || readSaved() !== "minimal") writeSaved("minimal");
    } else {
      mode = requested;
      if (save) writeSaved(mode);
    }
    root.dataset.motion = mode;
    controls.forEach(function (choice) {
      choice.value = mode;
      choice.disabled = false;
      choice.setAttribute("aria-describedby", "motion-mode-hint");
    });
    const hint = doc.getElementById("motion-mode-hint");
    if (hint) hint.textContent = media.matches
      ? "Системное ограничение движения: доступен режим «Минимум»."
      : { full: "Выразительная режиссура при сохранении спокойного чтения.",
          balanced: "Короткие отклики и полезные переходы.",
          minimal: "Без декоративного движения." }[mode];
    controls.forEach(function (choice) {
      Array.from(choice.options).forEach(function (option) {
        option.disabled = media.matches && option.value !== "minimal";
      });
    });
    if (mode === "minimal") {
      if (introTimeline) { introTimeline.progress(1).kill(); introTimeline = null; }
      active.forEach(function (el) {
        if (global.gsap) global.gsap.killTweensOf(el);
        el.style.removeProperty("transform");
        el.style.removeProperty("opacity");
      });
      active.clear();
    }
  }

  function seconds(token, fallback) {
    const value = global.getComputedStyle(root).getPropertyValue(token).trim();
    const n = parseFloat(value);
    if (!Number.isFinite(n)) return fallback;
    return value.endsWith("ms") ? n / 1000 : n;
  }
  function tween(el, from, to, kind) {
    if (!el || !shouldAnimate(mode, kind) || !global.gsap || doc.hidden) return;
    global.gsap.killTweensOf(el);
    active.add(el);
    global.gsap.fromTo(el, from, Object.assign({
      duration: seconds("--motion-duration-standard", 0.28),
      ease: "power2.out",
      overwrite: "auto",
      onComplete: function () {
        active.delete(el);
        global.gsap.set(el, { clearProps: "opacity,transform" });
      }
    }, to));
  }
  // Intentional semantic feedback: neither grading nor saved progress is inferred.
  function resolve(el, state) {
    if (!el || el.hidden) return;
    if (mode === "minimal") return;
    const correct = state === "ok" || state === "done";
    tween(el, { opacity: 0.65, y: correct && mode === "full" ? 5 : 2 },
      { opacity: 1, y: 0, duration: seconds("--motion-duration-fast", 0.2) }, "component");
  }

  function enter(el, kind) {
    if (!el || el.hidden) return;
    const scene = kind === "scene";
    const dx = scene && mode === "full" ? 6 : 0;
    tween(el, { opacity: 0.75, y: dx },
      { opacity: 1, y: 0, duration: seconds("--motion-duration-standard", 0.28) },
      scene ? "scene" : "component");
  }

  function intro() {
    if (mode !== "full" || !global.gsap) return;
    if (!doc.querySelector(".studio-home-hero")) {
      const heading = doc.querySelector(".week-hero-copy h1, .page-head h1, .entry-word, .active-a1-hero h1, .studio-auth-story h2");
      if (heading) tween(heading, { opacity: 0.7, y: 6 },
        { opacity: 1, y: 0, duration: seconds("--motion-duration-expressive", 0.48) }, "signature");
      return;
    }
    const title = doc.querySelector(".studio-home-heading h1");
    const subtitle = doc.querySelector(".studio-home-heading p");
    const texts = Array.from(doc.querySelectorAll(".studio-hero-copy > .studio-eyebrow, .studio-hero-copy > h2, .studio-hero-copy > p, .studio-hero-copy > .hero-actions"));
    const art = doc.querySelector(".studio-hero-art");
    const timeline = global.gsap.timeline({ defaults: { ease: "power2.out" } });
    introTimeline = timeline;
    if (title) timeline.fromTo(title, { autoAlpha: 0.78, y: 8 }, { autoAlpha: 1, y: 0, duration: 0.38, clearProps: "all" });
    if (subtitle) timeline.fromTo(subtitle, { opacity: 0.4 }, { opacity: 1, duration: 0.25, clearProps: "opacity" }, "-=0.2");
    if (texts.length) timeline.fromTo(texts, { opacity: 0.3, y: 6 }, { opacity: 1, y: 0, duration: 0.3, stagger: 0.085, clearProps: "opacity,transform" }, "-=0.12");
    if (art) timeline.fromTo(art, { opacity: 0.75 }, { opacity: 1, duration: 0.46, clearProps: "opacity" }, "-=0.4");
    timeline.eventCallback("onComplete", function () { introTimeline = null; });
  }

  function revealCards() {
    const list = Array.from(doc.querySelectorAll(SELECTORS.cards + ", .active-a1-panel, .speech-studio"));
    if (!list.length || !("IntersectionObserver" in global) || mode === "minimal") return;
    const observer = new global.IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        observer.unobserve(entry.target);
        if (mode === "full") {
          tween(entry.target, { opacity: 0.73, y: 7 },
            { opacity: 1, y: 0, duration: seconds("--motion-duration-standard", 0.28) }, "scene");
        } else {
          tween(entry.target, { opacity: 0.8 }, { opacity: 1, duration: 0.18 }, "component");
        }
      });
    }, { threshold: 0.05, rootMargin: "0px 0px -10px 0px" });
    list.forEach(function (el) { observer.observe(el); });
    observers.push(observer);
  }

  function readingRoute() {
    const links = Array.from(doc.querySelectorAll(".toc a[href^='#']"));
    if (!links.length || !("IntersectionObserver" in global)) return;
    const targets = new Map();
    links.forEach(function (link) {
      const id = link.getAttribute("href").slice(1);
      const section = doc.getElementById(id);
      if (section) targets.set(section, link);
    });
    if (!targets.size) return;
    const observer = new global.IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting || entry.target.hidden) return;
        links.forEach(function (link) { link.removeAttribute("aria-current"); });
        const link = targets.get(entry.target);
        if (link) link.setAttribute("aria-current", "location");
      });
    }, { rootMargin: "-8% 0px -72% 0px", threshold: 0 });
    targets.forEach(function (_, el) { observer.observe(el); });
    observers.push(observer);
  }

  function feedbackWatch() {
    if (!global.MutationObserver) return;
    doc.querySelectorAll(SELECTORS.feedback).forEach(function (el) {
      const observer = new global.MutationObserver(function (entries) {
        if (entries.some(function (e) { return e.type === "childList" || e.attributeName === "hidden" || e.attributeName === "data-state"; })) {
          resolve(el, el.dataset.state || "info");
        }
      });
      observer.observe(el, { attributes: true, attributeFilter: ["hidden", "data-state"], childList: true });
      observers.push(observer);
    });
  }

  function events() {
    // No new focus targets, no scrolling or interception of a real user action.
    doc.addEventListener("click", function (event) {
      const target = event.target.closest && event.target.closest("button, a, summary");
      if (!target || !shouldAnimate(mode, "micro")) return;
      if (target.matches(".choice, .active-a1-mission-tab, .studio-nav > a, .btn, [data-a1-builder-word], [data-stress-choices] button")) {
        tween(target, { scale: 0.985 }, { scale: 1, duration: 0.14 }, "micro");
      }
    });
    doc.querySelectorAll("details").forEach(function (details) {
      details.addEventListener("toggle", function () {
        if (!details.open || !shouldAnimate(mode, "component")) return;
        const elements = Array.from(details.children).filter(function (el) { return el.tagName !== "SUMMARY"; }).slice(0, 5);
        elements.forEach(function (el) {
          tween(el, { opacity: 0.65, y: mode === "full" ? 5 : 0 },
            { opacity: 1, y: 0, duration: 0.22 }, "component");
        });
      });
    });
  }
  function stop() {
    observers.forEach(function (observer) { observer.disconnect(); });
    if (introTimeline) { introTimeline.kill(); introTimeline = null; }
    if (global.gsap) active.forEach(function (el) { global.gsap.killTweensOf(el); });
    active.clear();
  }
  function init() {
    if (started) return;
    started = true;
    controls = Array.from(doc.querySelectorAll("[data-motion-control]"));
    refresh(readSaved(), false);
    controls.forEach(function (choice) {
      choice.addEventListener("change", function () { refresh(choice.value, true); });
    });
    if (media.addEventListener) media.addEventListener("change", function () { refresh(readSaved(), false); });
    events();
    feedbackWatch();
    readingRoute();
    revealCards();
    intro();
    global.addEventListener("pagehide", stop);
    global.addEventListener("pageshow", function (event) { if (event.persisted) { readingRoute(); } });
  }
  global.EnglishMotion = { effectiveMode: effectiveMode, shouldAnimate: shouldAnimate, resolve: resolve, enter: enter,
    get mode() { return mode; }, setMode: function (value) { refresh(value, true); } };
  if (doc.readyState === "loading") doc.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})(typeof window !== "undefined" ? window : null);
