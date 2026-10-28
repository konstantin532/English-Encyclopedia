/* Native details remain readable without JavaScript. No motion is introduced. */
(() => {
  const root = document.querySelector('[data-editorial-pilot]');
  if (!root || !window.matchMedia) return;
  const wide = window.matchMedia('(min-width: 1100px)');
  const notes = root.querySelectorAll('[data-editorial-note]');
  const sync = () => notes.forEach(note => { note.open = wide.matches; });
  sync();
  wide.addEventListener('change', sync);
})();
