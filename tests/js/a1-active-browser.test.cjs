const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../static/js/a1-active.js'), 'utf8');
const topics = JSON.parse(fs.readFileSync(path.join(__dirname, '../../content/active_a1/topics_01_08.json'), 'utf8'));
const repairs = JSON.parse(fs.readFileSync(path.join(__dirname, '../../content/active_a1/error_repairs_01_18.json'), 'utf8'));

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
  appendChild(child) {this.children.push(child);}
  replaceChildren() {this.children = [];}
  querySelector() {return null;}
}

function buildBrowser() {
  const topic = {...topics[0], repair: repairs[0]};
  const elements = new Map();
  const find = (selector) => {
    if (!elements.has(selector)) elements.set(selector, new Element());
    return elements.get(selector);
  };
  const root = {
    querySelector: find,
    querySelectorAll: () => [],
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
    elements, find, timers,
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
