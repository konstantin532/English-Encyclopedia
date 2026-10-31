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
    assert.match(page.route, /^\/(?!\/)\S*$/, page.name);
    const url = new URL(page.route, 'https://atlas.example.test');
    assert.equal(url.origin, 'https://atlas.example.test', page.name);
    assert.match(url.pathname, /^\/[^\s]*\/$|^\/$/, page.name);
    assert.equal(url.hash, '', page.name);
    assert.ok(page.main&&page.title,page.name);
    assert.ok(['student','guest','pending','teacher'].includes(page.audience),page.name);
    assert.ok(!names.has(page.name),`duplicate ${page.name}`);names.add(page.name);
  }
  for(const viewport of pages.viewports)assert.ok(viewport.maxScreens>=1&&viewport.maxScreens<=4);
});

// Exercise the CLI with real child processes. The tiny HTTP servers expose only
// the database selected at the process boundary; no Django/browser install is needed.
function databaseFixture(t) {
  const os=require('node:os');
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'visual-review-db-'));
  t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
  const before=path.join(directory,'before'),after=path.join(directory,'after');
  for(const checkout of [before,after]){
    fs.mkdirSync(checkout,{recursive:true});
    fs.writeFileSync(path.join(checkout,'manage.py'),
      "require('node:http').createServer((req,res)=>res.end(JSON.stringify({database:process.env.DATABASE_URL,checkout:process.cwd()}))).listen(Number(process.argv[3].split(':').pop()),'127.0.0.1');");
  }
  fs.mkdirSync(path.join(after,'scripts'));
  for(const file of ['visual_review.cjs','visual_review_lib.cjs','visual_review_pages.json']){
    fs.copyFileSync(path.join(__dirname,'../../scripts',file),path.join(after,'scripts',file));
  }
  // Record user seeding separately: this HTTP fixture has no Django installation.
  const seeded=path.join(directory,'seeded.json');
  fs.writeFileSync(path.join(after,'scripts/browser_auth.cjs'), "const fs=require('node:fs');exports.seedBrowserUser=(checkout,database,options={})=>{const p=process.env.VR_FIXTURE_SEEDED;const rows=fs.existsSync(p)?JSON.parse(fs.readFileSync(p)):[];rows.push({checkout,database,pending:!!options.pending});fs.writeFileSync(p,JSON.stringify(rows));};exports.learnerState=async()=>({cookies:[],origins:[]});");
  const modules=path.join(directory,'node_modules');
  fs.mkdirSync(path.join(modules,'playwright'),{recursive:true});
  fs.writeFileSync(path.join(modules,'playwright/index.js'),
    "exports.chromium={launch:async()=>{const before=await(await fetch('http://127.0.0.1:8133')).json();const after=await(await fetch('http://127.0.0.1:8134')).json();require('node:fs').writeFileSync(process.env.VR_FIXTURE_OBSERVATIONS,JSON.stringify({before,after}));throw Error('Fixture stops before browser capture');}};");
  const observations=path.join(directory,'observed.json');
  return {before,after,observations,seeded,run(overrides){
    return require('node:child_process').spawnSync(process.execPath,[path.join(after,'scripts/visual_review.cjs')],{
      cwd:after,windowsHide:true,encoding:'utf8',timeout:20000,
      env:{...process.env,NODE_PATH:modules,ATLAS_PYTHON:process.execPath,ATLAS_BEFORE_DIR:before,
        DATABASE_URL:'sqlite:///inherited-shared.sqlite3',ATLAS_BEFORE_DATABASE_URL:'',ATLAS_AFTER_DATABASE_URL:'',
        VR_BEFORE_URL:'',VR_AFTER_URL:'',VR_OUTPUT:path.join(directory,'report'),VR_FIXTURE_OBSERVATIONS:observations,VR_FIXTURE_SEEDED:seeded,...overrides},
    });
  }};
}

test('each checkout serves its own database even when a shared DATABASE_URL is inherited',t=>{
  const fixture=databaseFixture(t);
  const result=fixture.run({ATLAS_BEFORE_DATABASE_URL:'sqlite:///before.sqlite3',ATLAS_AFTER_DATABASE_URL:'sqlite:///after.sqlite3'});
  assert.ifError(result.error);
  assert.equal(result.status,1,'fixture intentionally stops after observing both running servers');
  assert.ok(fs.existsSync(fixture.observations),result.stderr);
  const seeds=JSON.parse(fs.readFileSync(fixture.seeded,'utf8'));
  assert.deepEqual(seeds,[{checkout:fixture.before,database:'sqlite:///before.sqlite3',pending:true},{checkout:fixture.after,database:'sqlite:///after.sqlite3',pending:true}]);
  const actual=JSON.parse(fs.readFileSync(fixture.observations,'utf8'));
  assert.deepEqual(actual,{
    before:{database:'sqlite:///before.sqlite3',checkout:fixture.before},
    after:{database:'sqlite:///after.sqlite3',checkout:fixture.after},
  });
});

test('managed servers refuse missing or shared database URLs instead of inheriting one database',t=>{
  for(const urls of [{},{ATLAS_BEFORE_DATABASE_URL:'sqlite:///same.sqlite3',ATLAS_AFTER_DATABASE_URL:'sqlite:///same.sqlite3'}]){
    const fixture=databaseFixture(t);
    const result=fixture.run(urls);
    assert.ifError(result.error);
    assert.equal(result.status,1);
    assert.equal(fs.existsSync(fixture.observations),false,'database validation must stop before servers/browser start');
    const report=JSON.parse(fs.readFileSync(path.join(path.dirname(fixture.observations),'report/report.json'),'utf8'));
    assert.match(report[0].notes.join(' '),/ATLAS_BEFORE_DATABASE_URL.*ATLAS_AFTER_DATABASE_URL/);
  }
});
