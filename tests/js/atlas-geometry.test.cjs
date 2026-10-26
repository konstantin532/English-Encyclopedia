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
