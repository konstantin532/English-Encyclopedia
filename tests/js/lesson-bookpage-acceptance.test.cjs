const {test}=require('node:test');
const assert=require('node:assert/strict');
const {contrastRatio}=require('../../scripts/verify_lesson_bookpage.cjs');

test('contrast calculation uses linear sRGB luminance, not average channel values',()=>{
  assert.equal(contrastRatio('rgb(255, 255, 255)','rgb(0, 0, 0)'),21);
  assert.equal(contrastRatio('rgb(255, 255, 255)','rgb(255, 255, 255)'),1);
  assert.ok(contrastRatio('rgb(20, 32, 51)','rgb(255, 255, 255)')>15);
});
test('unresolved or translucent color measurements cannot silently pass contrast',()=>{
  for(const color of ['transparent','rgba(255, 255, 255, 0.5)','var(--ink)','linear-gradient(red,blue)']){
    assert.throws(()=>contrastRatio(color,'rgb(255, 255, 255)'),/opaque rgb/);
  }
});
