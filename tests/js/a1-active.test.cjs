const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const a1 = require('../../static/js/a1-active.js');

const root = path.join(__dirname, '../../content/active_a1');
const entries = ['topics_01_08.json', 'topics_09_13.json', 'topics_14_18.json']
  .flatMap(name => JSON.parse(fs.readFileSync(path.join(root, name), 'utf8')));

test('18 connected original topics, and no topic past situation-weeks', () => {
  assert.deepEqual(entries.map(x => x.n), Array.from({length:18}, (_, i) => i + 1));
  for (const item of entries) assert.equal(a1.validTopic(item), true);
  assert.equal(a1.validTopic({...entries[0], n:19}), false);
  assert.equal(a1.validTopic({...entries[0], correct:4}), false);
});

test('prepared model answer accepts spelling variants and limited alternatives', () => {
  assert.equal(a1.compareModelAnswer(' I’m a teacher! ', "I'm a teacher.", []), true);
  assert.equal(a1.compareModelAnswer("  I am a teacher. ", "I'm a teacher.", ['I am a teacher.']), true);
  assert.equal(a1.compareModelAnswer("He's a teacher", "I'm a teacher", []), false);
  assert.equal(a1.compareModelAnswer(' ', 'This is a book.', []), false);
  assert.equal(a1.normalizeAnswer('I’M,   at HOME!'), "i'm at home");
});

test('each model answer is accepted and wrong unrelated words are rejected', () => {
  for (const item of entries) {
    assert.equal(a1.compareModelAnswer(item.answer, item.answer, item.alternatives), true, item.n);
    assert.equal(a1.compareModelAnswer('COMPLETELY UNRELATED WORDS', item.answer, item.alternatives), false, item.n);
  }
});

test('prefer a real en-US voice; do not silently choose other languages', () => {
  const british = { lang: 'en-GB' };
  const american = { lang: 'en_US' };
  assert.equal(a1.getAmericanVoice([british, american]), american);
  assert.equal(a1.getAmericanVoice([british]), null);
  assert.equal(a1.getAmericanVoice([]), null);
});

test('learners are warned that exact model match is not full linguistic assessment', () => {
  const code = fs.readFileSync(path.join(__dirname, '../../static/js/a1-active.js'), 'utf8');
  assert.match(code, /не означает ошибку/);
  assert.match(code, /не произношения/);
  assert.doesNotMatch(code, /fetch\s*\(/);
  assert.doesNotMatch(code, /localStorage\./);
});
