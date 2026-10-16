const { test } = require('node:test');
const assert = require('node:assert/strict');
const lesson = require('../../static/js/cafe-lab.js');

test('one vs two portions use singular and plural correctly', () => {
  assert.equal(lesson.buildSentence(1, 'tea', 'like'), "I'd like one tea, please.");
  assert.equal(lesson.buildSentence(2, 'tea', 'like'), "I'd like two teas, please.");
  assert.equal(lesson.buildSentence(3, 'coffee', 'can'), "Can I have three coffees, please?");
});

test('sentence builder selects alternative polite question', () => {
  assert.equal(lesson.buildSentence(1, 'coffee', 'can'), "Can I have one coffee, please?");
});

test('invalid selections are rejected rather than interpreted', () => {
  for (const [number, item, style] of [[0,'tea','like'],[2,'juice','like'],[2,'tea','give']]) {
    assert.throws(() => lesson.buildSentence(number, item, style), /Unknown sentence selection/);
  }
});

test('translation tracks the chosen product and count', () => {
  assert.equal(lesson.buildTranslation(1, 'tea'), 'Мне один чай, пожалуйста.');
  assert.equal(lesson.buildTranslation(2, 'tea'), 'Мне два чая, пожалуйста.');
  assert.equal(lesson.buildTranslation(3, 'coffee'), 'Мне три кофе, пожалуйста.');
});

test('dialogue comprehension does not accept the order Tom actually wanted', () => {
  assert.equal(lesson.isCorrectListenAnswer('b'), true);
  assert.equal(lesson.isCorrectListenAnswer('a'), false);
  assert.equal(lesson.isCorrectListenAnswer('c'), false);
});

test('speech synthesis chooses an en-US voice only', () => {
  const uk = { lang: 'en-GB', name: 'UK voice' };
  const us = { lang: 'en-US', name: 'American voice' };
  assert.equal(lesson.chooseAmericanVoice([uk, us]), us);
  assert.equal(lesson.chooseAmericanVoice([{lang:'fr-FR'}, uk]), null);
  assert.equal(lesson.chooseAmericanVoice([]), null);
});

test('sample dialogue is original and contains both misunderstood and corrected orders', () => {
  assert.ok(lesson.DIALOGUE.includes('Two coffees?'));
  assert.ok(lesson.DIALOGUE.some(line => line.includes('One tea and one coffee')));
  assert.equal(lesson.DIALOGUE.length, 6);
});
