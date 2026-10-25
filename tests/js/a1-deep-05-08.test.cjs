const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const active = require('../../static/js/a1-active.js');
const rows = JSON.parse(fs.readFileSync(path.join(__dirname, '../../content/active_a1/topics_01_08.json'), 'utf8'));

test('cafe local models accept a short taught request without changing its drink', () => {
  const row = rows.find(row => row.n === 5);
  for (const answer of ['Coffee, please.', 'A coffee, please.', 'Can I have a coffee, please?']) {
    assert.equal(active.compareModelAnswer(answer, row.answer, row.alternatives), true, answer);
  }
  for (const answer of ['Tea, please.', 'I do not like coffee.', 'Coffee is my phone.']) {
    assert.equal(active.compareModelAnswer(answer, row.answer, row.alternatives), false, answer);
  }
});

test('active quantity and ownership answers preserve number, food and person', () => {
  const quantity = rows.find(row => row.n === 6);
  for (const answer of ['Three coffees, please.', "I'd like three coffees, please."]) {
    assert.equal(active.compareModelAnswer(answer, quantity.answer, quantity.alternatives), true, answer);
  }
  for (const answer of ['Thirteen coffees, please.', 'Three teas, please.', 'Three coffee, please.']) {
    assert.equal(active.compareModelAnswer(answer, quantity.answer, quantity.alternatives), false, answer);
  }
  const owner = rows.find(row => row.n === 8);
  for (const answer of ["This is Tom's book.", "This is not Anna's book.", "This is Anna's phone."]) {
    assert.equal(active.compareModelAnswer(answer, owner.answer, owner.alternatives), false, answer);
  }
});
