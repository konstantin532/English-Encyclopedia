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
