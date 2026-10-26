const {test}=require('node:test');
const assert=require('node:assert/strict');
test('chapter reading may grow vertically while column alignment remains strict',()=>{
  const {geometryDelta}=require('../../scripts/atlas_geometry.cjs');
  const a={x:264,y:878,width:908,height:1374};
  assert.equal(geometryDelta('chapter','.story-script',a,{...a,y:920,height:1490}),0);
  assert.equal(geometryDelta('chapter','.story-script',a,{...a,x:305}),41);
  assert.equal(geometryDelta('chapter','.story-script',a,{...a,width:826}),82);
});
test('chapter cover, navigation and card dimensions stay protected',()=>{
  const {geometryDelta}=require('../../scripts/atlas_geometry.cjs');
  const a={x:264,y:100,width:908,height:95};
  for(const selector of ['.week-hero','.week-route','.studio-sidebar','.site-header']) {
    assert.equal(geometryDelta('chapter',selector,a,{...a,y:141}),41);
    assert.equal(geometryDelta('chapter',selector,a,{...a,height:120}),25);
  }
  assert.equal(geometryDelta('chapter','.studio-lesson-card',a,{...a,y:400}),0);
  assert.equal(geometryDelta('chapter','.studio-lesson-card',a,{...a,height:120}),25);
});
test('home and catalogue still compare all four rectangle dimensions',()=>{
  const {geometryDelta}=require('../../scripts/atlas_geometry.cjs');
  const a={x:0,y:10,width:100,height:20};
  for(const screen of ['home','collection'])for(const selector of ['.story-script','.studio-lesson-card']) {
    assert.equal(geometryDelta(screen,selector,a,{...a,y:42}),32);
    assert.equal(geometryDelta(screen,selector,a,{...a,height:80}),60);
  }
});
