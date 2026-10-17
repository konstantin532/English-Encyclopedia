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
  assert.equal(a1.normalizeAnswer('I’M,   at HOME!'), 'im at home');
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

test('missing apostrophes and surrounding quotes count as the same target words', () => {
  assert.equal(a1.compareModelAnswer('Im a teacher!', "I'm a teacher.", []), true);
  assert.equal(a1.compareModelAnswer('“Im a teacher.”', "I'm a teacher.", []), true);
  assert.equal(a1.compareModelAnswer('Its next to the bank!', "It's next to the bank.", []), true);
  assert.equal(a1.compareModelAnswer('Tom has a key', "Tom's a key", []), false);
  assert.equal(a1.normalizeAnswer("‘I’m’ here"), "im here");
});

test('word-order builder keeps duplicated words as distinct selectable buttons', () => {
  const words = a1.builderTokens('One tea and one coffee, please.');
  assert.deepEqual(words, ['One', 'tea', 'and', 'one', 'coffee,', 'please.']);
  assert.equal(a1.builderCorrect(words, [0, 1, 2, 3, 4, 5]), true);
  assert.equal(a1.builderCorrect(words, [0, 3, 2, 1, 4, 5]), false);
  assert.equal(a1.builderCorrect(words, [0, 1, 2, 3, 4]), false);
  assert.equal(a1.builderCorrect(words, [0, 1, 2, 3, 4, 4]), false);
  assert.equal(a1.builderPhrase(words, [0, 1, 2]), 'One tea and');
});

test('letter-spelling builder preserves T-O-M rather than one unmovable block', () => {
  const letters = a1.builderTokens('T-O-M');
  assert.deepEqual(letters, ['T', 'O', 'M']);
  assert.equal(a1.builderPhrase(letters, [0, 1, 2]), 'T-O-M');
  assert.equal(a1.builderPhrase(letters, [1, 0, 2]), 'O-T-M');
  assert.equal(a1.builderCorrect(letters, [0, 1, 2]), true);
  assert.equal(a1.builderCorrect(letters, [2, 1, 0]), false);
});

test('all eighteen model answers support at least two builder elements', () => {
  for (const item of entries) {
    const tokens = a1.builderTokens(item.answer);
    assert.ok(tokens.length >= 2, 'topic ' + item.n);
    assert.equal(a1.builderCorrect(tokens, tokens.map((_, i) => i)), true, 'topic ' + item.n);
    assert.equal(a1.builderCorrect(tokens, tokens.map((_, i) => i).reverse()), false, 'topic ' + item.n);
  }
});

test('each lesson has its own correctable grammar error and explanation', () => {
  const repairs = JSON.parse(fs.readFileSync(path.join(root, 'error_repairs_01_18.json'), 'utf8'));
  assert.equal(repairs.length, 18);
  assert.deepEqual(repairs.map(r => r.n), Array.from({length:18}, (_,i) => i+1));
  for (const r of repairs) {
    assert.ok(r.reason.length >= 30, 'lesson ' + r.n);
    assert.ok(r.hint.length >= 10, 'lesson ' + r.n);
    assert.notEqual(a1.normalizeAnswer(r.wrong), a1.normalizeAnswer(r.correct), 'lesson ' + r.n);
    assert.equal(a1.compareModelAnswer(r.correct, r.correct, []), true, 'lesson ' + r.n);
    assert.equal(a1.compareModelAnswer(r.wrong, r.correct, []), false, 'lesson ' + r.n);
  }
});

test('each of eighteen lessons adds exactly six bespoke scenarios and two twists', () => {
  const scenarios = ['scenarios_01_06.json','scenarios_07_12.json','scenarios_13_18.json']
    .flatMap(file => JSON.parse(fs.readFileSync(path.join(root,file),'utf8')));
  assert.deepEqual(scenarios.map(s => s.n), Array.from({length:18},(_,i)=>i+1));
  const titles = [], scenes = [];
  for(const s of scenarios){
    assert.equal(a1.validMissions(s), true, 'lesson '+s.n);
    for(const [idx,mission] of s.missions.entries()){
      assert.equal(mission.id, idx+1);
      assert.ok(mission.scene.length >= 20);
      assert.ok(mission.prompt.length >= 15);
      assert.ok(mission.example.trim().length >= 1);
      assert.ok(mission.coach.length >= 15);
      assert.ok(mission.example.length <= 200);
      titles.push(mission.title);
      scenes.push(mission.scene);
      assert.equal(a1.scenarioVariant(s,idx,0).example,mission.example);
    }
    assert.equal(a1.scenarioVariant(s,5,1).example,s.twists[0].example);
    assert.equal(a1.scenarioVariant(s,5,2).example,s.twists[1].example);
    assert.equal(a1.scenarioVariant(s,5,3),null);
    assert.equal(a1.scenarioVariant(s,4,1).example,s.missions[4].example);
  }
  assert.equal(titles.length,108);
  assert.equal(new Set(titles).size,108);
  assert.equal(new Set(scenes).size,108);
  assert.equal(scenarios.reduce((n,s)=>n+s.twists.length,0),36);
});

test('mission validator rejects incomplete, duplicated or malformed mission slots', () => {
  const scenario=JSON.parse(fs.readFileSync(path.join(root,'scenarios_01_06.json'),'utf8'))[0];
  assert.equal(a1.validMissions({...scenario, missions: scenario.missions.slice(0,5)}),false);
  assert.equal(a1.validMissions({...scenario, missions: scenario.missions.map(m=>({...m,id:1}))}),false);
  assert.equal(a1.validMissions({...scenario, twists: []}),false);
  assert.equal(a1.scenarioVariant(scenario,-1,0),null);
  assert.equal(a1.scenarioVariant(scenario,6,0),null);
});

test('the six open-ended situations never pretend to auto-grade creative language', () => {
  const js=fs.readFileSync(path.join(__dirname,'../../static/js/a1-active.js'),'utf8');
  const template=fs.readFileSync(path.join(__dirname,'../../templates/core/a1_active_topic.html'),'utf8');
  assert.match(js,/самостоятель|No backend|NEVER auto-graded|после самостоятельного/i);
  assert.match(template,/Другие верные формулировки тоже возможны/);
  assert.match(template,/система не оценивает свободную речь автоматически/);
  assert.doesNotMatch(js,/fetch\s*\(/);
  assert.doesNotMatch(js,/localStorage\./);
});
