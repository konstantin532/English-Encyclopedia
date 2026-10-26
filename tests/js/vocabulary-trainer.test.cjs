const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/vocabulary-trainer.js', 'utf8');
const sandbox = { module: { exports: {} }, setTimeout, clearTimeout, AbortController };
vm.runInNewContext(source, sandbox);
const { createTransport, init } = sandbox.module.exports;

function harness(fetch, opts = {}) {
  const html = [], pending = [];
  const transport = createTransport({ fetch, setTimeout, clearTimeout, AbortController,
    onHTML: (text) => { html.push(text); return text.startsWith('<trainer'); },
    onPending: state => pending.push(state), timeout: 20, ...opts });
  return { transport, html, pending };
}
const ok = text => ({ status: 200, text: async () => text });
test('double submit is locked; confirmed server HTML replaces current phase once', async () => {
  let resolve;
  const h = harness(() => new Promise(r => { resolve = r; }));
  const first = h.transport.send('/session/', 'token=original&answer=mine');
  await h.transport.send('/session/', 'token=other&answer=lost');
  resolve(ok('<trainer phase=feedback>'));
  await first;
  assert.equal(h.html.length, 1);
  assert.equal(h.transport.hasPending(), false);
});
test('ambiguous failure preserves immutable same-token payload for retry', async () => {
  const requests = []; let fail = true;
  const h = harness(async (url, options) => {
    requests.push([url, options.body]);
    if (fail) { fail = false; throw new Error('offline'); }
    return ok('<trainer phase=feedback>');
  });
  await h.transport.send('/session/', 'token=original&revision=1&answer=private');
  assert.equal(h.transport.hasPending(), true);
  await h.transport.send('/session/', 'token=new&answer=changed');
  assert.equal(requests.length, 1);
  await h.transport.retry();
  assert.equal(requests[0][1], requests[1][1]);
  assert.equal(h.transport.hasPending(), false);
});
test('timeout and non-trainer/login responses stay unknown, never record a learner failure', async () => {
  const h = harness(() => new Promise(() => {}));
  await h.transport.send('/session/', 'token=x');
  assert.equal(h.transport.hasPending(), true);
  const login = harness(async () => ok('<html>sign in</html>'));
  await login.transport.send('/session/', 'token=x');
  assert.equal(login.transport.hasPending(), true);
});
test('server validation/conflict HTML is rendered; 5xx keeps retry payload', async () => {
  const conflict = harness(async () => ({ status: 409, text: async () => '<trainer unsent=mine>' }));
  await conflict.transport.send('/session/', 'token=x&answer=mine');
  assert.equal(conflict.html.length, 1);
  assert.equal(conflict.transport.hasPending(), false);
  const server = harness(async () => ({ status: 500, text: async () => '<trainer broken>' }));
  await server.transport.send('/session/', 'token=x');
  assert.equal(server.html.length, 0);
  assert.equal(server.transport.hasPending(), true);
});
test('back/pageshow revalidates canonical state, keeps answer and uses no persistent storage', () => {
  const handlers = {};
  const doc = { querySelector: () => ({ dataset: {}, querySelector: () => null }), addEventListener: (name, fn) => handlers[name] = fn };
  const win = { fetch: async () => ok('<trainer>'), addEventListener: (name, fn) => handlers[name] = fn,
    setTimeout, clearTimeout, AbortController };
  init(doc, win);
  assert.equal(typeof handlers.pageshow, 'function');
  assert.equal(typeof handlers.submit, 'function');
  assert.equal(typeof handlers.click, 'function');
  assert.doesNotMatch(source, /localStorage|sessionStorage|innerHTML\s*=/);
  assert.match(source, /textContent/);
});
function browserStub({ incomingRevision = '3', local = 'unsaved words', failPost = false, incomingHasNote = true } = {}) {
  const handlers = {}, requests = [];
  let focusCount = 0;
  function makeRoot(revision, value, hasNote = true) {
    const recovered = [];
    const field = { name: 'answer', id: 'trainer-answer', tagName: 'TEXTAREA', value, defaultValue: 'older saved draft', disabled: false };
    const note = { dataset: {}, name: 'mnemonic', id: 'trainer-mnemonic', tagName: 'TEXTAREA', value: 'server note', defaultValue: 'server note' };
    const status = { textContent: '', focus() { focusCount++; } };
    return { dataset: { session: '1', revision, statusUrl: '/session/status/' }, field, note, status, recovered,
      querySelector(selector) {
        if (selector === '#trainer-answer') return field;
        if (selector === '#trainer-mnemonic') return hasNote ? note : null;
        if (selector === '.trainer-header') return { after(section) { recovered.push(section.children[1]); } };
        if (selector === '[data-trainer-status]') return status;
        if (selector === '[data-trainer-heading]') return { focus() { focusCount++; } };
        if (selector === '[data-trainer-network]') return { hidden: true };
        return null;
      },
      querySelectorAll(selector) { return selector === '[data-recovery-name]' ? recovered : [field, ...(hasNote ? [note] : [])]; },
      replaceWith(next) { current = next; }
    };
  }
  let current = makeRoot('2', local);
  const original = current;
  const incoming = makeRoot(incomingRevision, 'older saved draft', incomingHasNote);
  const doc = { querySelector() { return current; }, addEventListener(name, fn) { handlers[name] = fn; },
    createElement(tag) { return { tagName: tag.toUpperCase(), dataset: {}, children: [], append(...items) { this.children.push(...items); } }; } };
  const win = { location: { href: 'https://preview.test/session/' }, history: { replaceState() {} },
    fetch: async (url, options) => {
      requests.push(url);
      if (options?.method === 'POST' && failPost) { failPost = false; throw new Error('lost response'); }
      if (url.endsWith('/status/')) return { ok: true, json: async () => ({ url: '/session/' }) };
      return { ok: true, status: 200, text: async () => '<canonical>' };
    }, DOMParser: class { parseFromString() { return { querySelector: () => incoming }; } },
    addEventListener(name, fn) { handlers[name] = fn; }, setTimeout, clearTimeout, AbortController };
  const client = init(doc, win);
  return { client, handlers, requests, incoming, original, doc, win, current: () => current, focused: () => focusCount };
}
test('actual pageshow handler fetches owner canonical status and preserves unsubmitted text including empty clear', async () => {
  for (const local of ['my unconfirmed idea', '']) {
    const h = browserStub({ local });
    h.handlers.pageshow({ persisted: true });
    await new Promise(setImmediate);
    assert.deepEqual(h.requests, ['/session/status/', '/session/']);
    assert.equal(h.current(), h.incoming);
    assert.equal(h.incoming.field.value, local);
    assert.ok(h.focused() > 0);
  }
});
test('stale canonical GET cannot replace newer phase/revision or learner text', async () => {
  const h = browserStub({ incomingRevision: '1' });
  await h.client.reconcile();
  assert.equal(h.current(), h.original);
  assert.equal(h.original.field.value, 'unsaved words');
  assert.match(h.original.status.textContent, /Не удалось/);
});

test('named action control cannot clobber the POST URL in enhanced opt-in', async () => {
  const h = browserStub();
  h.win.FormData = function () { return new URLSearchParams('action=enroll&prerequisites=yes'); };
  h.win.URLSearchParams = URLSearchParams;
  const form = { action: { toString: () => '[object HTMLInputElement]' },
    getAttribute: () => null, closest: () => h.original };
  h.handlers.submit({ target: form, preventDefault() {}, submitter: { name: '' } });
  await new Promise(setImmediate);
  assert.equal(h.requests[0], 'https://preview.test/session/');
});
test('canonical recovery retains edited association including an explicit clear and note-editor context', async () => {
  for (const text of ['unsaved association', '']) {
    const h = browserStub();
    h.original.note.value = text;
    h.original.dataset.noteEditor = 'true';
    h.win.location.href = 'https://preview.test/session/?notes=1';
    await h.client.reconcile();
    assert.equal(h.incoming.note.value, text);
    assert.match(h.requests[1], /notes=1/);
  }
});

test('ambiguous note save then reconcile keeps edited or cleared note without an automatic second POST', async () => {
  for (const text of ['pending association', '']) {
    const h = browserStub({ failPost: true });
    h.original.note.value = text;
    h.original.dataset.noteEditor = 'true';
    await h.client.transport.send('/session/?notes=1', 'token=same&mnemonic=' + text);
    assert.equal(h.client.transport.hasPending(), true);
    await h.client.reconcile();
    assert.equal(h.incoming.note.value, text);
    assert.equal(h.requests.length, 3); // Original POST, owner status GET, canonical editor GET only.
    assert.match(h.requests[2], /notes=1/);
    assert.equal(h.client.transport.hasPending(), true);
  }
});

test('if canonical phase removes note editor, unsent note remains copyable and is never submitted', async () => {
  const h = browserStub({ incomingHasNote: false });
  h.original.note.value = 'my association before another-device phase change';
  h.original.dataset.noteEditor = 'true';
  await h.client.reconcile();
  assert.equal(h.incoming.recovered.length, 1);
  assert.equal(h.incoming.recovered[0].value, 'my association before another-device phase change');
  assert.equal(h.incoming.recovered[0].readOnly, true);
  assert.equal(h.incoming.recovered[0].dataset.recoveryName, 'mnemonic');
  assert.equal(h.requests.length, 2);
});
for (const text of ['server-rendered unconfirmed note', '']) {
  test('rendered 400/409 note remains unconfirmed through repeated canonical GET: ' + JSON.stringify(text), async () => {
    const h = browserStub();
    h.original.note.value = text;
    h.original.note.defaultValue = text; // A server-rendered failure, not a locally dirty field.
    h.original.note.dataset = { unconfirmed: 'true' };
    h.original.dataset.noteEditor = 'true';
    await h.client.reconcile();
    assert.equal(h.incoming.note.value, text);
    assert.equal(h.incoming.note.dataset.unconfirmed, 'true');
    assert.equal(h.requests.length, 2); // GET only, never a note/assessment submission.
    h.incoming.note.defaultValue = text;
    await h.client.reconcile();
    assert.equal(h.incoming.note.value, text);
    assert.equal(h.incoming.note.dataset.unconfirmed, 'true');
    assert.equal(h.requests.length, 4);
  });
}
