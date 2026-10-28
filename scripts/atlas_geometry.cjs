const assert=require('node:assert/strict');
function assertGeometrySnapshot(actual,expected,label){
  assert.ok(expected,`${label}: missing authored geometry snapshot`);
  assert.deepEqual(Object.keys(actual).sort(),Object.keys(expected).sort(),`${label}: geometry selectors changed`);
  for(const [selector,boxes] of Object.entries(expected)){
    assert.equal(actual[selector].length,boxes.length,`${label}: ${selector} count changed`);
    boxes.forEach((box,index)=>{
      for(const axis of ['x','y','width','height']){
        const value=actual[selector][index][axis];
        assert.ok(Number.isFinite(value)&&Math.abs(value-box[axis])<=1,`${label}: ${selector}[${index}] ${axis}: expected ${box[axis]}, got ${value}`);
      }
    });
  }
}
// Only authored reading height may change; shell and column geometry stay invariant.
function geometryDelta(screen,selector,before,after,viewportWidth=Infinity){
  let keys=['x','y','width','height'];
  if(screen==='chapter'&&selector==='.story-script')keys=['x','width'];
  else if(screen==='chapter'&&(selector==='.studio-lesson-card'||(selector==='.week-route'&&viewportWidth<700)))keys=['x','width','height'];
  return Math.max(...keys.map(key=>Math.abs(before[key]-after[key])));
}
function assertChapterReadingFlow(measurements,flow){
  const script=measurements['.story-script'][0],hero=measurements['.week-hero'][0];
  const cards=measurements['.studio-lesson-card'];
  assert.ok(script&&hero&&cards.length&&flow,'chapter reading flow missing');
  assert.ok(flow.scriptVisible&&flow.lineCount>0&&flow.visibleLines===flow.lineCount,'chapter script text must remain visible');
  assert.ok(script.height>0&&script.y>=hero.y+hero.height-1,'script must follow the cover with positive height');
  for(const line of flow.lines)assert.ok(line.height>0&&line.y>=script.y-1&&line.y+line.height<=script.y+script.height+1,'script line escapes reading box');
  const distance=cards[0].y-(script.y+script.height);
  assert.ok(distance>=-1&&distance<=Math.max(512,flow.lineHeight*12),'lesson cards must follow the script within a bounded reading gap');
  assert.ok(Math.abs(cards[0].y-flow.cardsContainer.y-flow.paddingTop)<=1,'first card detaches from its container');
  for(let i=1;i<cards.length;i++)assert.ok(Math.abs(cards[i].y-cards[i-1].y-cards[i-1].height-flow.cardGap)<=1,'lesson card order/gap changed');
  if(flow.viewportWidth<700){
    const route=measurements['.week-route'][0],bottom=flow.article.y+flow.article.height;
    assert.ok(route&&route.height>0&&route.y>=bottom-1&&route.y-bottom<=128,'mobile route must follow the article within its layout gap');
  }
  const last=cards[cards.length-1];
  assert.ok(Math.abs(last.y+last.height-(flow.cardsContainer.y+flow.cardsContainer.height-flow.paddingBottom))<=1,'last card escapes its container');
}
module.exports={geometryDelta,assertChapterReadingFlow,assertGeometrySnapshot};
