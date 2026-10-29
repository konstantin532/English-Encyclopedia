/* Native details remain readable without JavaScript. No motion is introduced. */
(() => {
  const root = document.querySelector('[data-editorial-pilot]');
  if (!root || !window.matchMedia) return;
  const wide = window.matchMedia('(min-width: 1100px)');
  const disclosures = root.querySelectorAll('[data-editorial-note], [data-editorial-guide]');
  const sync = () => disclosures.forEach(disclosure => { disclosure.open = wide.matches; });
  sync();
  wide.addEventListener('change', sync);
})();
