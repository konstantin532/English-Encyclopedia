const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');

test('poem gap verification handles network failures, input focus and async double click', () => {
  const script = fs.readFileSync(path.join(root, 'static/js/story-player.js'), 'utf8');
  const markup = fs.readFileSync(path.join(root, 'templates/poems/detail.html'), 'utf8');
  assert.match(script, /if \(busy\) return/);
  assert.match(script, /if \(!response.ok\) throw new Error/);
  assert.match(script, /firstInvalid\.focus\(\)/);
  assert.match(script, /mark\.textContent = data\.correct \? " — верно"/);
  assert.match(script, /status\.textContent = "Сервер недоступен/);
  assert.match(markup, /data-gaps-status role="status" aria-live="polite"/);
});

test('no-JS supplementary lessons display real text, not a blank listening area', () => {
  const markup = fs.readFileSync(path.join(root, 'templates/core/a1_active_topic.html'), 'utf8');
  assert.match(markup, /<noscript><div role="note">/);
  assert.match(markup, /<ol>\{% for line in topic\.dialogue %\}/);
});


// Run the real click handler and text-range highlighter with both rendered forms.
function phraseHuntBrowser(mode, phrase = "Who's Rose?", fullForm = 'Who is Rose?', hidden = false, rendered = {}) {
  const vm = require('node:vm');
  const marks = [];
  const branch = (name, words, visible) => {
    const root = { name, visible, getClientRects: () => visible ? [{}] : [] };
    root.parts = words.map(word => ({ textContent: word, length: word.length, parent: root }));
    Object.defineProperty(root, 'textContent', { get: () => root.parts.map(n => n.textContent).join('') });
    return root;
  };
  const pieces = value => value.match(/\w+|[^\w]/g);
  const written = branch('written', pieces(rendered.full || fullForm || phrase), !hidden && mode === 'written');
  const spoken = branch('spoken', pieces(rendered.short || phrase), !hidden && mode === 'spoken');
  const note = branch('full', ['полностью: ' + (rendered.full || fullForm || phrase)], !hidden && mode === 'spoken');
  const line = branch('line', [], !hidden);
  line.parts = [...written.parts, ...spoken.parts, ...note.parts];
  const paragraph = branch('paragraph', [], true);
  paragraph.parts = [{ textContent: 'Том: ', length: 5, parent: paragraph }, ...line.parts];
  paragraph.querySelector = selector => selector === '.line-text' ? line : null;
  paragraph.querySelectorAll = () => [written, spoken, note];
  const story = {
    querySelectorAll: selector => selector === 'p' ? [paragraph] : selector === 'mark' ? [...marks] : [],
    normalize() {},
  };
  let scrolls = 0;
  for (const target of [paragraph, written, spoken, note, line]) target.scrollIntoView = () => { scrolls++; };
  const fn = { hidden: true };
  const button = { dataset: { hunt: phrase, huntFull: fullForm }, nextElementSibling: fn, attrs: {},
    addEventListener(event, listener) { this[event] = listener; },
    setAttribute(name, value) { this.attrs[name] = value; },
  };
  const document = {
    cookie: '',
    querySelector: selector => selector === '[data-story-text]' ? story : null,
    querySelectorAll: selector => selector === '[data-hunt]' ? [button] : [],
    createTreeWalker(root) {
      let next = 0;
      return { currentNode: null, nextNode() { this.currentNode = root.parts[next++]; return !!this.currentNode; } };
    },
    createElement: () => ({}),
    createRange() {
      let node, start, end;
      return {
        setStart(value, offset) { node = value; start = offset; },
        setEnd(value, offset) { assert.equal(value, node); end = offset; },
        surroundContents(mark) {
          mark.textContent = node.textContent.slice(start, end);
          mark.visible = node.parent.visible;
          mark.branch = node.parent.name;
          mark.childNodes = [];
          mark.replaceWith = () => { marks.splice(marks.indexOf(mark), 1); };
          marks.push(mark);
        },
      };
    },
  };
  vm.runInNewContext(fs.readFileSync(path.join(root, 'static/js/story-player.js'), 'utf8'), {
    document, window: {}, matchMedia: () => ({matches: true}),
    NodeFilter: { SHOW_TEXT: 4 }, getComputedStyle: () => ({visibility: 'visible'}),
  });
  return { marks, button, fn, get scrolls() { return scrolls; } };
}

const huntForms = [
  ["Who's Rose?", 'Who is Rose?'],
  ["I don't know.", 'I do not know.'],
  ["But it's my house!", 'But it is my house!'],
  ["And who's Rose?", 'And who is Rose?'],
];
for (const [short, full] of huntForms) for (const mode of ['written', 'spoken']) {
  test('phrase hunt highlights the visible ' + mode + ' form: ' + short, () => {
    const app = phraseHuntBrowser(mode, short, full);
    app.button.click();
    const expected = (mode === 'written' ? full : short).replace(/[.!?]$/, '');
    assert.equal(app.marks.map(mark => mark.textContent).join(''), expected);
    assert.ok(app.marks.every(mark => mark.visible && mark.branch === mode));
    assert.equal(app.fn.hidden, false);
    assert.equal(app.button.attrs['aria-expanded'], 'true');
    assert.equal(app.scrolls, 1);
    app.button.click();
    assert.equal(app.marks.map(mark => mark.textContent).join(''), expected);
  });
}

test('phrase hunt does not highlight or reveal text in listening-without-text mode', () => {
  const app = phraseHuntBrowser('spoken', "Who's Rose?", 'Who is Rose?', true);
  app.button.click();
  assert.equal(app.marks.length, 0);
  assert.equal(app.scrolls, 0);
});

for (const apostrophe of ['’', '‘']) {
  test('phrase hunt accepts the typographic apostrophe ' + apostrophe, () => {
    const app = phraseHuntBrowser('spoken', 'Who' + apostrophe + 's Rose?', 'Who is Rose?', false,
      {short: "Who's Rose?"});
    app.button.click();
    assert.equal(app.marks.map(mark => mark.textContent).join(''), "Who's Rose");
    assert.ok(app.marks.every(mark => mark.visible && mark.branch === 'spoken'));
  });
}

test('phrase hunt preserves visible full-form notes for older buttons', () => {
  const app = phraseHuntBrowser('spoken', 'Who is Rose?', '', false,
    {short: "Who's Rose?", full: 'Who is Rose?'});
  app.button.click();
  assert.equal(app.marks.map(mark => mark.textContent).join(''), 'Who is Rose');
  assert.ok(app.marks.every(mark => mark.visible && mark.branch === 'full'));
});

for (const mode of ['written', 'spoken']) {
  test('phrase hunt does not match a different name in ' + mode + ' mode', () => {
    const app = phraseHuntBrowser(mode, "Who's Lily?", 'Who is Lily?', false,
      {short: "Who's Rose?", full: 'Who is Rose?'});
    app.button.click();
    assert.equal(app.marks.length, 0);
    assert.equal(app.scrolls, 0);
  });
}
