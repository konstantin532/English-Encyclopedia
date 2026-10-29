const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {diffPixels,screensDown,mainContentVerdict,newProblems,buildSummary,percent}=require('../../scripts/visual_review_lib.cjs');

function image(width,height,rgba=[255,255,255,255]){
  const data=new Uint8ClampedArray(width*height*4);
  for(let i=0;i<data.length;i+=4)data.set(rgba,i);
  return data;
}
function paint(data,width,x,y,rgba){data.set(rgba,(y*width+x)*4);}

test('identical images have no difference and no change box',()=>{
  const a=image(4,3),b=image(4,3);
  assert.deepEqual(diffPixels(a,b,4,3,3),{changed:0,compared:12,ratio:0,box:null});
});

test('anti-aliasing noise below tolerance is ignored, real change is boxed',()=>{
  const a=image(10,10),b=image(10,10);
  paint(b,10,1,1,[245,245,245,255]); // noise
  paint(b,10,6,2,[0,0,0,255]);
  paint(b,10,8,7,[200,0,0,255]);
  const result=diffPixels(a,b,10,10,10);
  assert.equal(result.changed,2);
  assert.deepEqual(result.box,{x:6,y:2,width:3,height:6});
});

test('a page that grows counts the extra rows as changed content',()=>{
  const a=image(5,4),b=image(5,6);
  const result=diffPixels(a,b,5,4,6);
  assert.equal(result.changed,10);
  assert.equal(result.compared,30);
  assert.deepEqual(result.box,{x:0,y:4,width:5,height:2});
});

test('main content pushed several screens down is a regression (PR #141 mobile lesson)',()=>{
  const verdict=mainContentVerdict({before:1297,after:3361,viewportHeight:844,maxScreens:2.5});
  assert.equal(verdict.status,'fail');
  assert.match(verdict.reason,/3\.98/);
});

test('main content within the limit passes, a pre-existing problem only warns',()=>{
  assert.equal(mainContentVerdict({before:900,after:1000,viewportHeight:844,maxScreens:2.5}).status,'ok');
  assert.equal(mainContentVerdict({before:2400,after:2500,viewportHeight:844,maxScreens:2.5}).status,'warn');
});

test('moving down by more than a screen fails even if it was already low',()=>{
  assert.equal(mainContentVerdict({before:2200,after:3300,viewportHeight:844,maxScreens:2.5}).status,'fail');
});

test('losing the main content fails; never having it only warns',()=>{
  assert.equal(mainContentVerdict({before:500,after:null,viewportHeight:900,maxScreens:2}).status,'fail');
  assert.equal(mainContentVerdict({before:null,after:null,viewportHeight:900,maxScreens:2}).status,'warn');
});

test('only problems absent before the change are reported as new',()=>{
  assert.deepEqual(newProblems(['a','b'],['b','c']),['c']);
  assert.deepEqual(newProblems([],[]),[]);
});

test('summary is a sticky markdown comment with a row per screenshot',()=>{
  const md=buildSummary([
    {title:'Урок: кафе',width:390,status:'fail',diff:{ratio:0.42},height:{before:17991,after:17422},main:{before:1.54,after:3.98},notes:['главное начинается на 3.98 экрана']},
    {title:'Главная',width:1440,status:'ok',diff:{ratio:0},height:{before:2210,after:2210},main:{before:0.1,after:0.1},notes:[]},
  ],{runUrl:'https://example.test/run/1'});
  assert.match(md,/^<!-- visual-review -->/);
  assert.match(md,/❌ Визуальная проверка/);
  assert.match(md,/17991 → 17422px/);
  assert.match(md,/1\.54 → 3\.98/);
  assert.match(md,/Изменился вид 1 из 2 снимков/);
  assert.match(md,/example\.test\/run\/1/);
  assert.equal(md.split('\n').filter(line=>line.startsWith('| ❌')||line.startsWith('| ✅')).length,2);
});

test('helpers format positions and percentages for people',()=>{
  assert.equal(screensDown(1266,844),1.5);
  assert.equal(screensDown(null,844),null);
  assert.equal(percent(0),'0%');
  assert.equal(percent(0.0004),'<0.1%');
  assert.equal(percent(0.256),'25.6%');
});

test('every reviewed page has a route, a main-content selector and sane limits',()=>{
  const pages=JSON.parse(fs.readFileSync(path.join(__dirname,'../../scripts/visual_review_pages.json'),'utf8'));
  assert.ok(pages.viewports.length>=2);
  assert.ok(pages.viewports.some(v=>v.width<=390),'phone width is reviewed');
  assert.ok(pages.pages.length>=8);
  const names=new Set();
  for(const page of pages.pages){
    assert.match(page.route,/^\/[^\s]*\/$|^\/$/,page.name);
    assert.ok(page.main&&page.title,page.name);
    assert.ok(!names.has(page.name),`duplicate ${page.name}`);names.add(page.name);
  }
  for(const viewport of pages.viewports)assert.ok(viewport.maxScreens>=1&&viewport.maxScreens<=4);
});
