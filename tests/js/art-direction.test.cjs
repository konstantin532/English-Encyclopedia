const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const scss = fs.readFileSync(path.join(root, 'static/scss/art-direction.scss'), 'utf8');
const base = fs.readFileSync(path.join(root, 'templates/base.html'), 'utf8');

test('editorial finish is part of the normal template pipeline', () => {
  assert.match(base, /static 'css\/art-direction\.css'/);
  assert.match(scss, /@layer ee-polish\s*\{/);
  assert.match(scss, /@mixin art-surface\s*\{/);
});

test('editorial treatment preserves existing component geometry and learning markers', () => {
  for (const property of ['grid-template-columns', 'grid-template-rows', 'position: fixed', 'font-size:', 'min-height:', 'max-width:', 'padding:']) {
    assert.equal(scss.includes(property), false, 'unexpected geometry rule: ' + property);
  }
  assert.doesNotMatch(scss, /--class-\d+\s*:/);
  assert.doesNotMatch(scss, /\.mk\s*\{/);
  assert.match(scss, /@media \(forced-colors: active\)/);
  assert.match(scss, /pointer-events: none/);
});
