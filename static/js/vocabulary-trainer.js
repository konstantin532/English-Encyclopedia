/* Optional transport enhancement. The server owns phase, tokens and evidence. */
(function () {
  'use strict';
  function createTransport(env) {
    let pending = null;
    let busy = false;
    async function transmit() {
      if (!pending || busy) return;
      busy = true;
      env.onPending({ pending: true, busy: true });
      const controller = new env.AbortController();
      let timer;
      try {
        const response = await Promise.race([
          env.fetch(pending.url, { method: 'POST', credentials: 'same-origin', cache: 'no-store',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' },
            body: pending.body, signal: controller.signal }),
          new Promise((resolve, reject) => { timer = env.setTimeout(() => {
            controller.abort(); reject(new Error('timeout'));
          }, env.timeout || 15000); })
        ]);
        if (response.status >= 500 || response.status === 403) throw new Error('unconfirmed');
        const html = await response.text();
        if (!env.onHTML(html, response.status, null, response.url)) throw new Error('unconfirmed');
        pending = null;
      } catch (_) {
        // Unknown acknowledgement: preserve the exact payload, including its token.
      } finally {
        env.clearTimeout(timer);
        busy = false;
        env.onPending({ pending: !!pending, busy: false });
      }
    }
    return {
      async send(url, body) { if (pending || busy) return; pending = { url, body }; return transmit(); },
      retry: transmit,
      hasPending() { return !!pending; },
      isBusy() { return busy; }
    };
  }
  function init(doc, win) {
    if (!doc.querySelector('[data-vocabulary-trainer]') || !win.fetch) return;
    const root = () => doc.querySelector('[data-vocabulary-trainer]');
    const announce = (message, focus) => {
      const status = root()?.querySelector('[data-trainer-status]');
      if (status) { status.textContent = message; if (focus) status.focus(); }
    };
    let transport;
    function controls(state) {
      const box = root()?.querySelector('[data-trainer-network]');
      if (box) box.hidden = !state.pending || state.busy;
      root()?.querySelectorAll('form button, form input, form textarea, form select').forEach(control => {
        if (control.tagName === 'TEXTAREA' || (control.tagName === 'INPUT' &&
            !['hidden', 'radio', 'checkbox'].includes(control.type))) control.readOnly = state.pending;
        else control.disabled = state.pending;
      });
      if (state.busy) announce('Отправляем. Ответ остаётся на странице до подтверждения.');
      else if (state.pending) announce('Подтверждение пока неизвестно. Повторите тот же запрос или проверьте состояние.', true);
    }
    function editedFields(scope) {
      const fields = Array.from(scope.querySelectorAll('textarea[name], input[name]:not([type="hidden"]), select[name]'));
      const edited = fields.filter(field => {
        if (field.type === 'radio') return fields.some(other => other.name === field.name && other.checked !== other.defaultChecked);
        if (field.type === 'checkbox') return field.checked !== field.defaultChecked;
        return field.value !== field.defaultValue;
      }).map(field => ({ name: field.name, type: field.type, value: field.value,
        checked: field.checked, label: field.name === 'mnemonic' ? 'Моя ассоциация' : 'Ваш неподтверждённый ответ' }));
      scope.querySelectorAll('[data-recovery-name]').forEach(field => edited.push({
        name: field.dataset.recoveryName, value: field.value, label: field.dataset.recoveryLabel, recovery: true
      }));
      return edited;
    }
    function restoreFields(incoming, fields) {
      const controls = Array.from(incoming.querySelectorAll('textarea[name], input[name]:not([type="hidden"]), select[name]'));
      fields.forEach(saved => {
        const field = !saved.recovery && controls.find(control => control.name === saved.name &&
          (saved.type !== 'radio' || control.value === saved.value));
        if (field) {
          if (saved.type === 'radio' || saved.type === 'checkbox') field.checked = saved.checked;
          else field.value = saved.value;
        } else {
          const section = doc.createElement('section'); section.className = 'trainer-card';
          const label = doc.createElement('label'); label.htmlFor = 'trainer-recovered-' + saved.name;
          label.textContent = saved.label + ' — не отправлено, можно скопировать' + (saved.value === '' ? ' (поле очищено)' : '');
          const recovered = doc.createElement('textarea'); recovered.id = label.htmlFor;
          recovered.readOnly = true; recovered.value = saved.value;
          recovered.dataset.recoveryName = saved.name; recovered.dataset.recoveryLabel = saved.label;
          section.append(label, recovered); incoming.querySelector('.trainer-header').after(section);
        }
      });
    }
    function render(html, status, preserve, canonicalURL) {
      const parsed = new win.DOMParser().parseFromString(html, 'text/html');
      const incoming = parsed.querySelector('[data-vocabulary-trainer]');
      if (!incoming) return false;
      const previous = root();
      // Same-session stale GET must never undo a newly confirmed phase.
      if (previous.dataset.session === incoming.dataset.session &&
          Number(incoming.dataset.revision) < Number(previous.dataset.revision)) return false;
      previous.replaceWith(incoming);
      if (canonicalURL) win.history.replaceState(null, '', canonicalURL);
      if (preserve) {
        restoreFields(incoming, preserve);
        if (preserve.length) announce('Актуальное состояние загружено. Неподтверждённые поля сохранены на странице; они не отправлены.');
      }
      const focus = incoming.querySelector(status >= 400 ? '[data-trainer-status]' : '[data-trainer-heading]');
      focus?.focus();
      return true;
    }
    transport = createTransport({ fetch: win.fetch.bind(win), setTimeout: win.setTimeout.bind(win),
      clearTimeout: win.clearTimeout.bind(win), AbortController: win.AbortController,
      onHTML: render, onPending: controls });
    let reconciling = false;
    async function reconcile() {
      if (transport.isBusy() || reconciling) return;
      reconciling = true;
      const fields = editedFields(root());
      const notesEditor = root()?.dataset.noteEditor === 'true';
      try {
        let url = win.location.href;
        const endpoint = root()?.dataset.statusUrl;
        if (endpoint) {
          const response = await win.fetch(endpoint, { credentials: 'same-origin', cache: 'no-store' });
          if (!response.ok) throw new Error('status');
          url = (await response.json()).url;
          if (notesEditor) {
            url += (url.includes('?') ? '&' : '?') + 'notes=1';
            if (root().querySelector('input[name="mode"]')?.value === 'spoken') url += '&mode=spoken';
            const rating = root().querySelector('input[name="self_rating"]')?.value;
            if (['good', 'hard', 'again'].includes(rating)) url += '&rating=' + rating;
          }
        }
        const response = await win.fetch(url, { credentials: 'same-origin', cache: 'no-store' });
        if (!response.ok || !render(await response.text(), response.status, fields, response.url)) throw new Error('state');
        controls({ pending: transport.hasPending(), busy: false });
      } catch (_) {
        announce('Не удалось загрузить сохранённое состояние. Текст остаётся на странице; попробуйте снова.', true);
      } finally { reconciling = false; }
    }
    doc.addEventListener('submit', event => {
      const form = event.target;
      if (!form.closest('[data-vocabulary-trainer]')) return;
      event.preventDefault();
      if (transport.hasPending() || reconciling) return;
      const data = new win.FormData(form);
      if (event.submitter?.name) data.append(event.submitter.name, event.submitter.value);
      const payload = new win.URLSearchParams(data).toString();
      transport.send(form.getAttribute('action') || win.location.href, payload);
    });
    doc.addEventListener('click', event => {
      if (event.target.closest('[data-trainer-retry]')) transport.retry();
      if (event.target.closest('[data-trainer-reconcile]')) reconcile();
    });
    win.addEventListener('pageshow', event => { if (event.persisted) reconcile(); });
    const error = root()?.dataset.error;
    if (error) root().querySelector('[data-trainer-status]')?.focus();
    return { reconcile, transport };
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = { createTransport, init };
  if (typeof document !== 'undefined' && typeof window !== 'undefined') {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => init(document, window), { once: true });
    else init(document, window);
  }
})();
