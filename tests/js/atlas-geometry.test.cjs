const {test}=require('node:test');
const assert=require('node:assert/strict');
test('authored home snapshot checks every rectangle axis and rejects missing cards',()=>{
  const {assertGeometrySnapshot}=require('../../scripts/atlas_geometry.cjs');
  assert.equal(typeof assertGeometrySnapshot,'function');
  const expected={'.hero':[{x:16,y:95,width:358,height:867}],'.card':[{x:55,y:859,width:280,height:273}]};
  assert.doesNotThrow(()=>assertGeometrySnapshot(structuredClone(expected),expected,'home 390'));
  for(const selector of ['.hero','.card'])for(const axis of ['x','y','width','height']){
    const actual=structuredClone(expected);actual[selector][0][axis]+=2;
    assert.throws(()=>assertGeometrySnapshot(actual,expected,'home 390'),new RegExp(axis));
  }
  assert.throws(()=>assertGeometrySnapshot({...expected,'.card':[]},expected,'home 390'),/count/);
  assert.throws(()=>assertGeometrySnapshot({'.hero':expected['.hero']},expected,'home 390'),/selectors/);
});
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

test('authored expanded lesson height replaces only the old chapter card height',()=>{
  const {geometryDelta}=require('../../scripts/atlas_geometry.cjs');
  const before={x:264,y:100,width:908,height:95};
  const expanded={...before,y:400,height:187};
  assert.equal(geometryDelta('chapter','.studio-lesson-card',before,expanded,1440,187),0);
  for(const [axis,delta] of [['x',2],['width',2],['height',2]]) {
    assert.equal(geometryDelta('chapter','.studio-lesson-card',before,{...expanded,[axis]:expanded[axis]+delta},1440,187),2);
  }
  assert.equal(geometryDelta('chapter','.studio-lesson-card',before,{...expanded,height:95},1440,187),92);
  assert.throws(()=>geometryDelta('chapter','.week-hero',before,expanded,1440,187),/lesson/);
  assert.throws(()=>geometryDelta('chapter','.studio-lesson-card',before,expanded,1440,0),/height/);
});

function flowFixture(){
  return {measurements:{'.week-hero':[{x:0,y:100,width:900,height:300}],'.story-script':[{x:0,y:500,width:900,height:200}],'.studio-lesson-card':[{x:0,y:800,width:900,height:95},{x:0,y:905,width:900,height:95}]},flow:{scriptVisible:true,lineCount:2,visibleLines:2,lineHeight:35,lines:[{y:500,height:90},{y:590,height:110}],cardsContainer:{y:800,height:200},paddingTop:0,paddingBottom:0,cardGap:10}};
}
test('vertical reading contract rejects hidden, collapsed or off-flow content',()=>{
  const {assertChapterReadingFlow}=require('../../scripts/atlas_geometry.cjs');
  assert.equal(typeof assertChapterReadingFlow,'function');
  const good=flowFixture();assert.doesNotThrow(()=>assertChapterReadingFlow(good.measurements,good.flow));
  for(const mutate of [
    f=>{f.measurements['.story-script'][0].height=0;},
    f=>{f.measurements['.story-script'][0].y=-9999;},
    f=>{f.flow.visibleLines=0;},
    f=>{f.measurements['.studio-lesson-card'][0].y=-9999;},
    f=>{f.measurements['.studio-lesson-card'][1].y=9999;},
    f=>{f.flow.scriptVisible=false;},
  ]){const f=flowFixture();mutate(f);assert.throws(()=>assertChapterReadingFlow(f.measurements,f.flow));}
});

test('mobile route follows the article but keeps its own size and alignment',()=>{
  const {geometryDelta,assertChapterReadingFlow}=require('../../scripts/atlas_geometry.cjs');
  const a={x:16,y:9000,width:358,height:337};
  assert.equal(geometryDelta('chapter','.week-route',a,{...a,y:10000},390),0);
  assert.equal(geometryDelta('chapter','.week-route',a,{...a,y:10000,height:340},390),3);
  assert.equal(geometryDelta('chapter','.week-route',a,{...a,y:10000},1440),1000);
  const f=flowFixture();f.flow.viewportWidth=390;f.flow.article={y:100,height:1000};f.measurements['.week-route']=[{x:0,y:1120,width:900,height:100}];
  assert.doesNotThrow(()=>assertChapterReadingFlow(f.measurements,f.flow));
  f.measurements['.week-route'][0].y=9999;assert.throws(()=>assertChapterReadingFlow(f.measurements,f.flow));
});
