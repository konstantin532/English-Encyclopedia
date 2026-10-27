/* Пазл тренировки фраз: карточки складываются в поле ответа. Без JS поле остаётся обычным вводом. */
(function () {
  'use strict';
  function setup(form) {
    const bank = form.querySelector('[data-puzzle-bank]');
    const tools = form.querySelector('[data-puzzle-tools]');
    const input = form.querySelector('input[name="answer"]');
    if (!bank || !tools || !input) return;
    const used = [];
    const render = () => { input.value = used.map((b) => b.dataset.word).join(' '); };
    bank.hidden = false;
    tools.hidden = false;
    input.readOnly = true;
    input.value = '';
    bank.addEventListener('click', (event) => {
      const tile = event.target.closest('button[data-word]');
      if (!tile || tile.disabled) return;
      tile.disabled = true;
      used.push(tile);
      render();
      const next = bank.querySelector('button[data-word]:not(:disabled)');
      (next || form.querySelector('button[type="submit"]')).focus();
    });
    tools.querySelector('[data-puzzle-undo]').addEventListener('click', () => {
      const tile = used.pop();
      if (tile) { tile.disabled = false; render(); }
    });
    tools.querySelector('[data-puzzle-reset]').addEventListener('click', () => {
      used.splice(0).forEach((tile) => { tile.disabled = false; });
      render();
    });
  }
  document.querySelectorAll('form[data-phrase-puzzle]').forEach(setup);
})();
