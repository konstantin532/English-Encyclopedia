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
  assert.match(source, /не автоматическая проверка/);
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
  for (const template of [poem, week, lesson]) assert.match(template, /speech-studio\.js/);
  for (const template of [poem, lesson, twister]) {
    assert.match(template, /data-speech-studio/);
    assert.match(template, /speech_studio_controls\.html/);
    assert.match(template, /data-speech-entry/);
  }
  assert.match(controls, /data-speech-record/);
  assert.match(controls, /data-speech-tap/);
  assert.match(controls, /data-speech-reveal/);
  assert.match(controls, /на сервер не отправляется/);
});
