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

test('geometry compares a visible layout box for flattened mobile contents',()=>{
  const {visibleLayoutBounds}=require('../../scripts/verify_lesson_bookpage.cjs');
  assert.equal(typeof visibleLayoutBounds,'function');
  assert.deepEqual(visibleLayoutBounds('contents',{x:0,width:0},{x:16,width:343}),{x:16,width:343});
  assert.deepEqual(visibleLayoutBounds('grid',{x:16,width:343},{x:32,width:311}),{x:16,width:343});
  assert.throws(()=>visibleLayoutBounds('contents',{x:0,width:0},null),/visible child/);
});
