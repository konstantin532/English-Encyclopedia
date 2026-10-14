// Единственная автоматическая анимация сайта: слова живого предложения
// получают свои линии по очереди, как будто разбор делается на глазах.
window.addEventListener("load", () => {
  const box = document.querySelector("[data-specimen]");
  if (!box || !window.gsap) return;
  const marks = box.querySelectorAll(".mk");
  const caps = box.querySelectorAll(".specimen-cap");
  const mm = gsap.matchMedia();
  mm.add("(prefers-reduced-motion: no-preference)", () => {
    const tl = gsap.timeline({ delay: 0.35, defaults: { ease: "power2.out" } });
    tl.fromTo(marks, { "--mk-reveal": 0 }, { "--mk-reveal": 1, duration: 0.5, stagger: 0.11 }, 0)
      .fromTo(caps, { autoAlpha: 0, y: -6 }, { autoAlpha: 1, y: 0, duration: 0.4, stagger: 0.11 }, 0.08);
    return () => tl.revert();
  });
});
