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

test('test-tone manifests cannot be used as speech', () => {
  const track = { url: '/static/audio/cafe-lab/voice_natural.mp3',
                  timings: Array.from({length: 6}, (_, i) => ({line:i,start:i,end:i+0.8})) };
  assert.equal(lesson.selectAudioTrack({engine:'test',tracks:{natural:track}}, 'natural'), null);
  assert.equal(lesson.selectAudioTrack({engine:'kokoro',tracks:{natural:track}}, 'natural'), track);
  assert.equal(lesson.selectAudioTrack(null, 'natural'), null);
  assert.equal(lesson.selectAudioTrack({engine:'kokoro',tracks:{}}, 'natural'), null);
  assert.equal(lesson.selectAudioTrack({engine:'kokoro',tracks:{natural:{...track,timings:[]}}}, 'natural'), null);
});

test('line highlighting only selects the actual spoken interval', () => {
  const timings = [{line:0,start:0.4,end:1.5},{line:1,start:2,end:3}];
  assert.equal(lesson.activeDialogueLine(timings, 0), -1);
  assert.equal(lesson.activeDialogueLine(timings, 0.4), 0);
  assert.equal(lesson.activeDialogueLine(timings, 1.5), -1);
  assert.equal(lesson.activeDialogueLine(timings, 2.5), 1);
  assert.equal(lesson.activeDialogueLine(timings, NaN), -1);
  assert.equal(lesson.activeDialogueLine(null, 1), -1);
});

test('dictation checks exact words but ignores punctuation, spacing and case', () => {
  assert.equal(lesson.isCorrectDictation(2, 'Two coffees?'), true);
  assert.equal(lesson.isCorrectDictation(2, '  TWO,   coffees!  '), true);
  assert.equal(lesson.isCorrectDictation(2, 'two teas'), false);
  assert.equal(lesson.isCorrectDictation(2, 'two coffee'), false);
  assert.equal(lesson.isCorrectDictation(3, 'No, sorry. One tea and one coffee, please.'), true);
  assert.equal(lesson.isCorrectDictation(3, 'no sorry one tea and one coffee please'), true);
  assert.equal(lesson.isCorrectDictation(3, 'No sorry two coffees please'), false);
  assert.equal(lesson.isCorrectDictation(3, ''), false);
});

test('dictation only permits the two purposely selected lines', () => {
  assert.equal(lesson.isCorrectDictation(0, lesson.DIALOGUE[0]), false);
  assert.equal(lesson.isCorrectDictation(5, 'Thank you!'), false);
  assert.equal(lesson.isCorrectDictation(-1, 'Two coffees?'), false);
  assert.equal(lesson.isCorrectDictation(999, 'Two coffees?'), false);
  assert.equal(lesson.normalizeDictation(' I’d LIKE one tea, PLEASE! '), "i'd like one tea please");
});
