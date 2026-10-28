const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const lib = require('../../static/js/speech-studio.js');
const root = path.join(__dirname, '../..');
const source = fs.readFileSync(path.join(root, 'static/js/speech-studio.js'), 'utf8');

test('all four stages train understanding, echo, recall and independent transfer', () => {
  assert.deepEqual(lib.MODES, ['see', 'echo', 'recall', 'transfer']);
  for (const kind of ['poem', 'twister', 'lesson']) {
    for (const phase of lib.MODES) {
      assert.ok(lib.INSTRUCTIONS[kind][phase].length > 15);
    }
  }
  assert.match(lib.INSTRUCTIONS.poem.recall, /памяти/);
  assert.match(lib.INSTRUCTIONS.twister.echo, /Точность важнее скорости/);
  assert.match(lib.INSTRUCTIONS.lesson.transfer, /без готовой фразы/);
});

test('line navigation cannot escape the source material', () => {
  assert.equal(lib.clampIndex(-9, 5), 0);
  assert.equal(lib.clampIndex(99, 5), 4);
  assert.equal(lib.clampIndex(0, 0), 0);
  assert.equal(lib.clampIndex(2, 5), 2);
});

test('rhythm indicator is only a tap tempo, never a fake speaking score', () => {
  assert.equal(lib.tempoFromTaps([]), null);
  assert.equal(lib.tempoFromTaps([0]), null);
  assert.equal(lib.tempoFromTaps([0, 500, 1000, 1500]), 120);
  assert.equal(lib.tempoFromTaps([0, 1000]), 60);
  assert.equal(lib.tempoFromTaps([0, 100]), null);
  assert.equal(lib.tempoFromTaps([0, 20000]), null);
  assert.match(source, /темп нажатий/);
  assert.doesNotMatch(source, /Это самооценка, а не автоматическая проверка/);
});

test('no cloud speech APIs, telemetry, hidden storage or uploading recordings', () => {
  assert.doesNotMatch(source, /fetch\s*\(/);
  assert.doesNotMatch(source, /XMLHttpRequest/);
  assert.doesNotMatch(source, /localStorage|sessionStorage/);
  assert.doesNotMatch(source, /SpeechRecognition/);
  assert.match(source, /getUserMedia/);
  assert.match(source, /URL\.revokeObjectURL/);
  assert.match(source, /pagehide/);
});

test('all three training surfaces include the actual script and reusable controls', () => {
  const poem = fs.readFileSync(path.join(root, 'templates/poems/detail.html'), 'utf8');
  const week = fs.readFileSync(path.join(root, 'templates/curriculum/week.html'), 'utf8');
  const lesson = fs.readFileSync(path.join(root, 'templates/lessons/detail.html'), 'utf8');
  const twister = fs.readFileSync(path.join(root, 'templates/components/twister_trainer.html'), 'utf8');
  const controls = fs.readFileSync(path.join(root, 'templates/components/speech_studio_controls.html'), 'utf8');
  const recorder = fs.readFileSync(path.join(root, 'templates/components/speech_recorder.html'), 'utf8');
  for (const template of [poem, week, lesson]) assert.match(template, /speech-studio\.js/);
  for (const template of [poem, lesson, twister]) {
    assert.match(template, /data-speech-studio/);
    assert.match(template, /speech_studio_controls\.html/);
    assert.match(template, /data-speech-entry/);
  }
  assert.match(controls, /speech_recorder\.html/);
  assert.match(recorder, /data-speech-record/);
  assert.match(controls, /data-speech-tap/);
  assert.match(controls, /data-speech-reveal/);
  assert.match(recorder, /Запись не отправляется на сервер\./);
});

// Lesson pages omit optional rhythm controls but keep speech navigation/recording.
test('lesson speech initializes and changes fragments without rhythm controls', () => {
  const vm = require('node:vm');
  const element = () => ({
    textContent: '', hidden: false, disabled: false, dataset: {}, childNodes: [],
    listeners: {},
    addEventListener(type, callback) { this.listeners[type] = callback; },
    setAttribute() {},
    replaceChildren() { this.childNodes = []; },
    append(...children) { this.childNodes.push(...children); },
  });
  const fields = new Map();
  for (const name of ['task', 'current', 'stress', 'position', 'instruction',
    'prev', 'next', 'reveal', 'done', 'status', 'record', 'stop', 'delete',
    'playback', 'record-status']) fields.set('[data-speech-' + name + ']', element());
  const entries = ['This is my book.', 'This is my phone.'].map(text => ({
    querySelector(selector) {
      if (selector === '[data-speech-source]') return {childNodes: [{cloneNode() { return {textContent: text}; }}]};
      return null;
    }
  }));
  const modes = lib.MODES.map(mode => Object.assign(element(), {dataset: {speechMode: mode}}));
  const studio = {
    dataset: {speechKind: 'lesson'},
    querySelector(selector) { return fields.get(selector) || null; },
    querySelectorAll(selector) { return selector === '[data-speech-entry]' ? entries : modes; },
    addEventListener() {},
  };
  const document = {readyState: 'complete', querySelectorAll() { return [studio]; }, createElement: element};
  vm.runInNewContext(source, {document, window: {navigator: {}}});
  assert.equal(fields.get('[data-speech-position]').textContent, 'Фрагмент 1 из 2');
  assert.equal(fields.get('[data-speech-record]').disabled, true);
  fields.get('[data-speech-next]').listeners.click();
  assert.equal(fields.get('[data-speech-position]').textContent, 'Фрагмент 2 из 2');
  modes[2].listeners.click();
  assert.equal(studio.dataset.speechMode, 'recall');
  assert.equal(fields.get('[data-speech-reveal]').hidden, false);
  fields.get('[data-speech-done]').listeners.click();
  assert.match(fields.get('[data-speech-status]').textContent, /Отмечено 1 из 2/);
});
