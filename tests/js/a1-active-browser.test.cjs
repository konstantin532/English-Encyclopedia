const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../static/js/a1-active.js'), 'utf8');
const readEntries = files => files.flatMap(file => JSON.parse(fs.readFileSync(path.join(__dirname, '../../content/active_a1', file), 'utf8')));
const topics = readEntries(['topics_01_08.json', 'topics_09_13.json', 'topics_14_18.json', 'topics_19_20.json', 'topics_21_22.json']);
const repairs = readEntries(['error_repairs_01_18.json', 'error_repairs_19_20.json', 'error_repairs_21_22.json']);
const scenarios = readEntries(['scenarios_01_06.json', 'scenarios_07_12.json', 'scenarios_13_18.json', 'scenarios_19_20.json', 'scenarios_21_22.json']);

class Element {
  constructor() {
    this.listeners = {};
    this.dataset = {};
    this.hidden = false;
    this.disabled = false;
    this.textContent = '';
    this.value = '';
    this.children = [];
    this.attrs = {};
  }
  addEventListener(name, fn) { this.listeners[name] = fn; }
  dispatch(name) {
    assert.equal(typeof this.listeners[name], 'function', 'missing ' + name + ' listener');
    this.listeners[name]({preventDefault() {}});
  }
  setAttribute(k,v) {this.attrs[k] = v;}
  removeAttribute(k) {delete this.attrs[k];}
  focus() { this.attrs.focused = true; }
  appendChild(child) {this.children.push(child);}
  replaceChildren() {this.children = [];}
  querySelector() {return null;}
}

function buildBrowser(number = 1) {
  const scenario = scenarios.find(s => s.n === number);
  const topic = {...topics.find(t => t.n === number), repair: repairs.find(r => r.n === number), missions: scenario.missions, twists: scenario.twists};
  const elements = new Map();
  const find = (selector) => {
    if (!elements.has(selector)) elements.set(selector, new Element());
    return elements.get(selector);
  };
  const missionTabs = Array.from({length:6}, (_,i) => {
    const el = new Element();
    el.dataset.a1MissionIndex = String(i);
    return el;
  });
  const root = {
    querySelector: find,
    querySelectorAll: selector => selector === '[data-a1-mission-index]' ? missionTabs : [],
  };
  const document = {
    querySelector: selector => selector === '[data-active-a1]' ? root : null,
    getElementById: id => id === 'a1-active-topic-data'
      ? { textContent: JSON.stringify(topic) } : null,
    createElement: () => new Element(),
  };
  const speechListeners = new Map();
  const timers = new Map();
  let voiceList = [], spoken = [], nextTimer = 1, canceled = 0;
  const speechSynthesis = {
    getVoices() { return voiceList; },
    addEventListener(k, fn) { speechListeners.set(k, fn); },
    removeEventListener(k, fn) {
      if (speechListeners.get(k) === fn) speechListeners.delete(k);
    },
    speak(u) { spoken.push(u.text); },
    cancel() { canceled++; },
  };
  class Utterance { constructor(text) { this.text = text; } }
  const win = {
    speechSynthesis,
    SpeechSynthesisUtterance: Utterance,
    setTimeout(fn) { const id = nextTimer++; timers.set(id, fn); return id; },
    clearTimeout(id) { timers.delete(id); },
    addEventListener() {},
  };
  vm.runInNewContext(source, { window:win, document, module:{exports:{}} });
  return {
    elements, find, timers, missionTabs,
    voicesChanged(voices) { voiceList = voices; speechListeners.get('voiceschanged')?.(); },
    get spoken() {return spoken;},
    get canceled() {return canceled;},
    get hasListener() {return speechListeners.has('voiceschanged');},
  };
}

test('late en-US voice makes first click play without requiring a second click', () => {
  const app = buildBrowser();
  app.find('[data-a1-play]').dispatch('click');
  assert.match(app.find('[data-a1-audio-status]').textContent, /Загружаем/);
  assert.equal(app.hasListener, true);
  assert.equal(app.spoken.length, 0);
  app.voicesChanged([{lang:'en-GB'}, {lang:'en-US'}]);
  assert.equal(app.spoken[0], topics[0].dialogue[0][1]);
  assert.equal(app.hasListener, false);
  assert.equal(app.timers.size, 0);
});

test('stopping cancels pending voice request and cannot start stale audio later', () => {
  const app = buildBrowser();
  app.find('[data-a1-play]').dispatch('click');
  assert.equal(app.hasListener, true);
  app.find('[data-a1-stop]').dispatch('click');
  assert.equal(app.hasListener, false);
  app.voicesChanged([{lang:'en-US'}]);
  assert.deepEqual(app.spoken, []);
  assert.match(app.find('[data-a1-audio-status]').textContent, /остановлено/i);
});

test('voice timeout falls back to readable transcript without crashing', () => {
  const app = buildBrowser();
  app.find('[data-a1-play]').dispatch('click');
  assert.equal(app.timers.size, 1);
  [...app.timers.values()][0]();
  assert.match(app.find('[data-a1-audio-status]').textContent, /Голос en-US не найден/);
  assert.equal(app.hasListener, false);
  assert.deepEqual(app.spoken, []);
});

test('six situations are navigable and model text stays hidden until each attempt', () => {
  const app = buildBrowser();
  const result = app.find('[data-a1-mission-result]');
  const answer = app.find('[data-a1-mission-answer]');
  assert.equal(result.hidden, true);
  assert.match(app.find('[data-a1-mission-progress]').textContent, /Ситуация 1 из 6/);
  answer.value = 'This is my book.';
  app.find('[data-a1-mission-form]').dispatch('submit');
  assert.equal(result.hidden, false);
  assert.equal(app.find('[data-a1-mission-example]').textContent, scenarios[0].missions[0].example);
  assert.match(app.find('[data-a1-mission-progress]').textContent, /Попробовано: 1 из 6/);
  app.find('[data-a1-mission-next]').dispatch('click');
  assert.equal(result.hidden, true);
  assert.equal(app.find('[data-a1-mission-title]').textContent, scenarios[0].missions[1].title);
  answer.value = 'A different reply';
  app.find('[data-a1-mission-prev]').dispatch('click');
  assert.equal(answer.value, 'This is my book.');
  assert.equal(result.hidden, false);
});

test('last story has two unique improvisation twists, each requires a new attempt', () => {
  const app = buildBrowser();
  app.missionTabs[5].dispatch('click');
  assert.equal(app.find('[data-a1-mission-twist-controls]').hidden, false);
  const result = app.find('[data-a1-mission-result]');
  const answer = app.find('[data-a1-mission-answer]');
  answer.value = 'This is my phone.';
  app.find('[data-a1-mission-form]').dispatch('submit');
  assert.equal(result.hidden, false);
  app.find('[data-a1-mission-twist]').dispatch('click');
  assert.equal(result.hidden, true);
  assert.equal(app.find('[data-a1-mission-scene]').textContent, scenarios[0].twists[0].scene);
  answer.value = 'This is my book.';
  app.find('[data-a1-mission-form]').dispatch('submit');
  assert.equal(app.find('[data-a1-mission-example]').textContent, scenarios[0].twists[0].example);
  app.find('[data-a1-mission-twist]').dispatch('click');
  assert.equal(result.hidden, true);
  assert.equal(app.find('[data-a1-mission-scene]').textContent, scenarios[0].twists[1].scene);
  app.find('[data-a1-mission-twist]').dispatch('click');
  assert.equal(app.find('[data-a1-mission-scene]').textContent, scenarios[0].missions[5].scene);
  assert.equal(result.hidden, false);
  assert.match(app.find('[data-a1-mission-progress]').textContent, /Попробовано: 1 из 6/);
});

test('blank input cannot reveal sample and new page does not remember answers', () => {
  const app = buildBrowser();
  app.find('[data-a1-mission-form]').dispatch('submit');
  assert.equal(app.find('[data-a1-mission-result]').hidden, true);
  const another = buildBrowser();
  assert.equal(another.find('[data-a1-mission-result]').hidden, true);
  assert.match(another.find('[data-a1-mission-progress]').textContent, /Попробовано: 0 из 6/);
});

for (const number of [19, 20, 21, 22]) {
  test('extended topic ' + number + ' starts its missions and hides every new twist model', () => {
    const app = buildBrowser(number);
    const scenario = scenarios.find(s => s.n === number);
    const result = app.find('[data-a1-mission-result]');
    assert.equal(result.hidden, true);
    assert.equal(app.find('[data-a1-mission-title]').textContent, scenario.missions[0].title);
    app.find('[data-a1-mission-answer]').value = scenario.missions[0].example;
    app.find('[data-a1-mission-form]').dispatch('submit');
    assert.equal(result.hidden, false);
    app.missionTabs[5].dispatch('click');
    for (const twist of scenario.twists) {
      app.find('[data-a1-mission-twist]').dispatch('click');
      assert.equal(result.hidden, true);
      assert.equal(app.find('[data-a1-mission-scene]').textContent, twist.scene);
      app.find('[data-a1-mission-answer]').value = twist.example;
      app.find('[data-a1-mission-form]').dispatch('submit');
      assert.equal(result.hidden, false);
      assert.equal(app.find('[data-a1-mission-example]').textContent, twist.example);
    }
  });
}

test('like to read is accepted as a natural alternative in error repair', () => {
  const app = buildBrowser(20);
  app.find('[data-a1-repair-answer]').value = 'I like to read.';
  app.find('[data-a1-repair-form]').dispatch('submit');
  assert.equal(app.find('[data-a1-repair-feedback]').dataset.state, 'ok');
  assert.equal(app.find('[data-a1-repair-explanation]').hidden, false);
});
