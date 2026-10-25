const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const sass = require('sass');
const source=path.join(__dirname,'../../static/scss/lesson-bookpage.scss');

test('pilot speech selection owns both foreground and background in polish layer',()=>{
  const css=sass.compile(source).css;
  assert.match(css, /@layer ee-polish/);
  const rule=css.match(/\[data-lesson-bookpage\] \.speech-mode-grid \.btn\[aria-pressed=true\] \{([^}]+)\}/);
  assert.ok(rule, 'pilot needs a paired active-state override, not a global btn change');
  assert.match(rule[1], /color: var\(--surface\)/);
  assert.match(rule[1], /background: var\(--ink\)/);
  assert.match(rule[1], /border-color: var\(--ink\)/);
  assert.match(rule[1], /text-decoration: underline/);
});
test('pilot stylesheet cannot change outer geometry or semantic marker colors',()=>{
  const scss=fs.readFileSync(source,'utf8');
  assert.doesNotMatch(scss, /\.lesson-grid|\.aside|\.page-head|\.studio-sidebar|\.mk\b|--class-\d/);
  assert.doesNotMatch(scss, /!important|outline:\s*(?:0|none)|animation:|transition:/);
  assert.match(scss,/\[data-lesson-bookpage\]/);
});

test('bookpage preserves the established font-family assignments',()=>{
  assert.doesNotMatch(fs.readFileSync(source,'utf8'), /font-family\s*:/);
});
