/* A week unfolds like an atlas entry; the HTML works before this enhancement runs. */
(function (global) {
  "use strict";
  const doc = global.document;
  const page = doc.querySelector("[data-week-motion]");
  const gsap = global.gsap;
  if (!page || !gsap) return;
  const root = doc.documentElement;
  const media = global.matchMedia("(prefers-reduced-motion: reduce)");
  const { Flip, ScrollTrigger, SplitText } = global;
  gsap.registerPlugin(...[Flip, ScrollTrigger, SplitText].filter(Boolean));
  const cards = Array.from(page.querySelectorAll("[data-week-flip]"));
  const seen = new WeakSet();
  const reveals = [];
  const triggers = [];
  let cardAnimation = null;
  let titleAnimation = null;
  let split = null;
  let titlePlayed = false;
  let sharedNavigation = false;
  let suspended = false;
  let enabled = null;

  function allowed() {
    return !media.matches && root.dataset.motion !== "minimal";
  }
  function duration(token, fallback) {
    const value = global.getComputedStyle(root).getPropertyValue(token).trim();
    const number = parseFloat(value);
    const seconds = value.endsWith("ms") ? number / 1000 : number;
    return Math.min(0.45, Math.max(0.18, Number.isFinite(seconds) ? seconds : fallback));
  }
  function refresh() {
    if (ScrollTrigger) ScrollTrigger.refresh();
  }
  function finishCards() {
    const animation = cardAnimation;
    cardAnimation = null;
    if (animation) animation.progress(1).kill();
    cards.forEach(card => card.removeAttribute("data-week-flip-running"));
  }
  function finishTitle() {
    const animation = titleAnimation;
    titleAnimation = null;
    if (animation) animation.progress(1).kill();
    if (split) { split.revert(); split = null; }
  }

  cards.forEach(card => {
    const summary = card.querySelector("summary");
    const body = card.querySelector("[data-week-lesson-body]");
    summary.addEventListener("click", event => {
      // The browser supplies keyboard activation too; links keep their own default action.
      if (event.defaultPrevented || event.button > 0 || event.target.closest("a, button, input, select")) return;
      if (!Flip || !allowed()) return;
      event.preventDefault();
      finishCards();
      const state = Flip.getState(cards);
      card.open = !card.open;
      cards.forEach(item => item.setAttribute("data-week-flip-running", ""));
      cardAnimation = Flip.from(state, {
        duration: duration("--week-motion-layout", 0.36),
        ease: "power2.out",
        scale: false,
        onComplete() {
          cardAnimation = null;
          cards.forEach(item => item.removeAttribute("data-week-flip-running"));
          refresh();
        }
      });
      if (card.open && body) {
        cardAnimation.fromTo(body, { opacity: 0.55 }, {
          opacity: 1, duration: 0.18, clearProps: "opacity"
        }, 0);
      }
    });
    // Native disclosure is the fallback when a plugin is missing or motion is off.
    card.addEventListener("toggle", () => { if (!cardAnimation) refresh(); });
  });

  function titleEntry() {
    if (!SplitText || titlePlayed || sharedNavigation) return;
    titlePlayed = true;
    const ready = doc.fonts ? doc.fonts.ready : Promise.resolve();
    ready.then(() => global.requestAnimationFrame(() => {
      if (!allowed() || suspended || sharedNavigation || doc.hidden) return;
      const title = page.querySelector("[data-week-title]");
      if (!title) return;
      split = SplitText.create(title, { type: "words", tag: "span", aria: "auto" });
      // Ink comes into focus; the title never changes position or holds up reading.
      titleAnimation = gsap.timeline({ onComplete() {
        titleAnimation = null;
        if (split) { split.revert(); split = null; }
      } });
      titleAnimation.fromTo(split.words, { opacity: 0.55 }, {
        opacity: 1, duration: 0.24, stagger: { amount: 0.12 }, ease: "power2.out"
      }, 0);
    }));
  }

  function sectionEntries() {
    if (!ScrollTrigger) return;
    page.querySelectorAll("article.prose > section.layer").forEach(section => {
      if (seen.has(section)) return;
      const heading = section.querySelector("h2");
      if (!heading) return;
      triggers.push(ScrollTrigger.create({
        trigger: section,
        start: "top 88%",
        once: true,
        onEnter() {
          seen.add(section);
          // A new stop on the reading route: only its label changes, never the lesson body.
          if (allowed() && !suspended) reveals.push(gsap.fromTo(heading, { opacity: 0.6 }, {
            opacity: 1, duration: duration("--motion-duration-standard", 0.28),
            ease: "power2.out", clearProps: "opacity"
          }));
        }
      }));
    });
  }
  function cleanup() {
    finishCards();
    finishTitle();
    triggers.splice(0).forEach(trigger => trigger.kill());
    reveals.splice(0).forEach(animation => animation.progress(1).kill());
  }
  function sync() {
    const next = allowed() && !suspended;
    if (next === enabled) return;
    enabled = next;
    if (!next) cleanup();
    else { sectionEntries(); titleEntry(); }
  }
  new global.MutationObserver(sync).observe(root, { attributes: true, attributeFilter: ["data-motion"] });
  media.addEventListener("change", sync);
  global.addEventListener("pagehide", () => { suspended = true; sync(); });
  global.addEventListener("pageshow", event => { if (event.persisted) { suspended = false; sync(); } });
  global.addEventListener("pagereveal", event => {
    if (!event.viewTransition) return;
    sharedNavigation = true;
    titlePlayed = true;
    finishTitle();
    if (!allowed()) event.viewTransition.skipTransition();
  });
  global.addEventListener("pageswap", event => {
    if (event.viewTransition && !allowed()) event.viewTransition.skipTransition();
  });
  sync();
})(window);
