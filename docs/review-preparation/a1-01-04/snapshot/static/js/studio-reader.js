// Размер текста урока: применяется к объяснениям и к заданиям, запоминается в браузере ученика.
(() => {
  const reader = document.querySelector("[data-lesson-reader]");
  const practice = document.querySelector("[data-lesson-practice]");
  const smaller = document.querySelector("[data-reader-smaller]");
  const larger = document.querySelector("[data-reader-larger]");
  const output = document.querySelector("[data-reader-size]");
  if (!reader || !smaller || !larger || !output) return;
  const KEY = "ee-reader-size";
  const base = Math.round(parseFloat(getComputedStyle(reader).fontSize));
  let size = base;
  try { const saved = parseInt(localStorage.getItem(KEY), 10); if (saved >= 15 && saved <= 24) size = saved; } catch (e) { /* хранилище недоступно */ }
  const update = () => {
    reader.style.fontSize = `${size}px`;
    if (practice) practice.style.setProperty("--reader-scale", String(size / base));
    output.textContent = String(size);
    smaller.disabled = size <= 15;
    larger.disabled = size >= 24;
    try { localStorage.setItem(KEY, String(size)); } catch (e) { /* хранилище недоступно */ }
  };
  smaller.addEventListener("click", () => { size = Math.max(15, size - 1); update(); });
  larger.addEventListener("click", () => { size = Math.min(24, size + 1); update(); });
  update();
})();
