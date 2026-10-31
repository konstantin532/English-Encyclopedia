/* Native disclosures remain usable without JavaScript. No learning state is changed. */
(() => {
  'use strict';
  const menu = document.querySelector('[data-atlas-menu]');
  const compact = window.matchMedia('(max-width: 1100px)');
  if (menu) {
    const fitNavigation = () => { menu.open = !compact.matches; };
    fitNavigation();
    compact.addEventListener('change', fitNavigation);
  }
  const index = document.querySelector('[data-atlas-reader-index]');
  if (index) {
    const reading = window.matchMedia('(min-width: 761px)');
    const fitIndex = () => { index.open = reading.matches; };
    fitIndex();
    reading.addEventListener('change', fitIndex);
  }
})();
