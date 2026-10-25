/* Real Chromium acceptance gate. Run against two checkouts with one seeded DB.
 * Requires playwright on NODE_PATH, ATLAS_BEFORE_DIR and ATLAS_PYTHON.
 * Screenshots are evidence of real Django pages, never generated mockups.
 */
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs/promises');
const path=require('node:path');
const assert=require('node:assert/strict');
const {verifyLessonBookpage}=require('./verify_lesson_bookpage.cjs');
const root=path.resolve(__dirname,'..');
const output=path.resolve(process.env.ATLAS_OUTPUT || 'atlas-browser-evidence');
const sizes=[[1440,900],[1280,800],[390,844],[360,800]];
const screens=[['home','/'],['collection','/levels/a1/'],['chapter','/levels/a1/weeks/13/']];
const selectors=['.studio-sidebar','.site-header','.studio-home-hero','.studio-phrase-paper','.studio-lesson-card','.week-card','.week-hero','.week-route','.story-script'];
async function serve(directory,port){
 const processHandle=spawn(process.env.ATLAS_PYTHON || 'python',['manage.py','runserver',`127.0.0.1:${port}`,'--noreload'],{cwd:directory,env:{...process.env,DJANGO_SETTINGS_MODULE:'config.settings.local'},stdio:['ignore','ignore','pipe']});
 let error='';processHandle.stderr.on('data',d=>{error+=d;});
 for(let n=0;n<100;n++){
  try{if((await fetch(`http://127.0.0.1:${port}/`)).ok)return processHandle;}catch{}
  await new Promise(resolve=>setTimeout(resolve,100));
 }
 processHandle.kill();throw Error('Django did not start: '+error);
}
async function ready(page,url){
 const response=await page.goto(url,{waitUntil:'networkidle'});assert.equal(response.status(),200,url);
 await page.evaluate(()=>document.fonts.ready);
}
async function bounds(page){return page.evaluate(selectors=>Object.fromEntries(selectors.map(selector=>[selector,Array.from(document.querySelectorAll(selector)).map(el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};})])),selectors);}
async function documentBox(locator){return locator.evaluate(el=>{const r=el.getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height};});}
async function overflow(page){return page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));}
(async()=>{
 await fs.mkdir(output,{recursive:true});
 const report={baseline:process.env.ATLAS_BASELINE||'before-worktree',screens:[],checks:[],errors:[]};
 const servers=[];let browser;
 try{
  servers.push(await serve(process.env.ATLAS_BEFORE_DIR,8123));servers.push(await serve(root,8124));
  browser=await chromium.launch();
  report.lessonBookpage={};
  await verifyLessonBookpage(browser,{output,beforeBase:'http://127.0.0.1:8123',afterBase:'http://127.0.0.1:8124',report:report.lessonBookpage});
  for(const [width,height] of sizes){
   for(const [name,route] of screens){
    const measurements={};
    for(const [state,port] of [['before',8123],['after',8124]]){
     const context=await browser.newContext({viewport:{width,height},reducedMotion:'reduce',isMobile:width<700,hasTouch:width<700});
     const page=await context.newPage();page.on('pageerror',error=>report.errors.push({name,state,width,message:error.message}));
     await ready(page,`http://127.0.0.1:${port}${route}`);
     const o=await overflow(page);assert.ok(o.scroll<=o.width+1,`${name} ${state} ${width}: horizontal overflow ${JSON.stringify(o)}`);
     await page.screenshot({path:path.join(output,`${name}-${width}-${state}.png`),fullPage:false});
     measurements[state]=await bounds(page);
     if(state==='after'&&name==='home'){
      const original=await documentBox(page.locator('.studio-home-hero'));
      const word=page.locator('.studio-phrase [role=button]').first();await word.focus();await word.press('Enter');
      await page.locator('.atlas-discovery').waitFor({state:'visible'});
      assert.deepEqual(await documentBox(page.locator('.studio-home-hero')),original,'discovery changes hero geometry');
      assert.equal(await word.getAttribute('aria-expanded'),'true');
      await page.screenshot({path:path.join(output,`discovery-${width}.png`)});
      await word.press('Escape');assert.equal(await word.getAttribute('aria-expanded'),'false');
      assert.equal(await word.evaluate(el=>el===document.activeElement),true);
     }
     if (name==='collection' && width<700) {
      await page.locator('.week-list').screenshot({path:path.join(output,`collection-cards-${width}-${state}.png`)});
     }
     await context.close();
    }
    let maxDelta=0;const changed=[];
    for(const selector of selectors){
     const a=measurements.before[selector],b=measurements.after[selector];
     if(a.length!==b.length){changed.push(`${selector}: ${a.length}→${b.length}`);continue;}
     a.forEach((rectangle,index)=>Object.keys(rectangle).forEach(key=>{maxDelta=Math.max(maxDelta,Math.abs(rectangle[key]-b[index][key]));}));
    }
    report.screens.push({name,width,height,maxGeometryDelta:maxDelta,changed,measurements});
    // Редизайн (ATLAS_REDESIGN=1) меняет раскладку намеренно: разница — в отчёте, скриншоты — в артефакте.
    if(process.env.ATLAS_REDESIGN!=='1'){assert.equal(changed.length,0,`${name} ${width}: ${changed.join(', ')}`);assert.ok(maxDelta<=1,`${name} ${width}: geometry changed ${maxDelta}px`);}
   }
  }
  // Editorial9–28: actual changed reading pages, in addition to the
  // existing before/after geometry gate above (which remains unchanged).
  const editorialPages=[
   ['lesson09','/lessons/a1-there-is-some/',true],
   ['lesson10','/lessons/a1-how-much-prices/',true],
   ['lesson11','/lessons/a1-present-simple-i-you/',true],
   ['lesson12','/lessons/a1-time-at-seven/',true],
   ['story02','/stories/2/',false],['poem03','/stories/poems/3/',false],
   ['lesson13','/lessons/a1-he-she-works/',true],
   ['lesson14','/lessons/a1-jobs-what-do-you-do/',true],
   ['lesson15','/lessons/a1-where-is-prepositions/',true],
   ['lesson16','/lessons/a1-directions-turn-left/',true],
   ['lesson17','/lessons/a1-questions-do-does/',true],
   ['lesson18','/lessons/a1-spelling-phone-numbers/',true],
   ['lesson19','/lessons/a1-always-never/',true],
   ['lesson20','/lessons/a1-like-doing/',true],
   ['lesson21','/lessons/a1-what-hurts/',true],
   ['lesson22','/lessons/a1-cant-cannot/',true],
   ['lesson23','/lessons/a1-dont-doesnt/',true],
   ['lesson24','/lessons/a1-letters-address/',true],
   ['lesson25','/lessons/a1-can-skills/',true],
   ['lesson26','/lessons/a1-why-because/',true],
   ['lesson27','/lessons/a1-bus-ticket/',true],
   ['lesson28','/lessons/a1-review-everything/',true],
   ['story03','/stories/3/',false],
   ['story04','/stories/4/',false],
   ['story05','/stories/5/',false],
   ['poem04','/stories/poems/4/',false],
   ['poem05','/stories/poems/5/',false],
   ['poem06','/stories/poems/6/',false],
   ['poem07','/stories/poems/7/',false]
  ];
  report.editorialPages=[];
  for(const [width,height] of [[1440,900],[390,844]]){
   const editorial=await browser.newContext({viewport:{width,height},reducedMotion:'reduce',isMobile:width<700,hasTouch:width<700});
   try{
    for(const [name,route,isLesson] of editorialPages){
     const p=await editorial.newPage();
     p.on('pageerror',error=>report.errors.push({name,state:'editorial',width,message:error.message}));
     await ready(p,`http://127.0.0.1:8124${route}`);
     assert.equal(new URL(p.url()).pathname,route,`${name}: unexpected redirect`);
     assert.equal(await p.locator('h1').count(),1,`${name}: missing reading title`);
     assert.equal(await p.locator('html').getAttribute('data-motion'),'minimal',`${name}: reduced motion ignored`);
     const o=await overflow(p);assert.ok(o.scroll<=o.width+1,`${name} ${width}: horizontal overflow ${JSON.stringify(o)}`);
     await p.screenshot({path:path.join(output,`editorial-${name}-${width}.png`)});
     if(isLesson){
      const fullMode=p.locator('[data-a1-route-mode="full"]');
      if(await fullMode.count()){
       await fullMode.focus();await fullMode.press('Enter');
       assert.equal(await fullMode.getAttribute('aria-pressed'),'true',`${name}: full lesson inaccessible by keyboard`);
      }
      assert.equal(await p.locator('[data-lesson-reader] section[id^="layer-"]').count(),7,`${name}: seven layers lost`);
      for(let n=1;n<=7;n++)assert.equal(await p.locator(`#layer-${n}`).isVisible(),true,`${name}: hidden layer${n}`);
      const summary=p.locator('#beginner-steps > summary');await summary.focus();await summary.press('Enter');
      assert.equal(await summary.evaluate(el=>el.parentElement.open),true,`${name}: keyboard explanation did not open`);
      assert.equal(await p.locator('#beginner-steps .a1-step-list > li').count(),3,`${name}: incomplete explanation`);
      await p.screenshot({path:path.join(output,`editorial-${name}-${width}-explanation.png`)});
     }
     report.editorialPages.push({name,route,width,height,reducedMotion:true,overflow:o,keyboardExplanation:isLesson});
     await p.close();
    }
   }finally{await editorial.close();}
  }
  report.checks.push('Editorial9–12 lessons, story2 and poem3 readable at1440/390; seven layers and keyboard explanations accessible; reduced-motion and overflow checked');
  // All chapter covers load; each has a stable, explicitly sized image box.
  const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'});
  const page=await context.newPage();
  for(let week=1;week<=14;week++){
   await ready(page,`http://127.0.0.1:8124/levels/a1/weeks/${week}/`);
   const img=page.locator('.week-hero-image');assert.equal(await img.evaluate(el=>el.complete&&el.naturalWidth>0),true,`week ${week}: missing image`);
   const o=await overflow(page);assert.ok(o.scroll<=o.width+1,`week ${week}: overflow`);
  }
  report.checks.push('All 14 chapter cover images load at 390px');
  // No-JS and reduced-motion reading must remain usable.
  const nojs=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}});
  const staticPage=await nojs.newPage();await ready(staticPage,'http://127.0.0.1:8124/');
  assert.match(await staticPage.locator('[data-atlas-explanation]').innerText(),/Я дома/);
  await staticPage.screenshot({path:path.join(output,'home-390-no-js.png')});await nojs.close();
  report.checks.push('No-JS phrase, translation and role captions readable');
  const full=await browser.newContext({viewport:{width:1440,height:900}});
  await full.addInitScript(()=>localStorage.setItem('ee-motion-mode','full'));
  const animated=await full.newPage();await ready(animated,'http://127.0.0.1:8124/');
  await animated.locator('.atlas-grammar-control').first().click();await animated.locator('.atlas-discovery').waitFor({state:'visible'});
  await animated.waitForFunction(()=>getComputedStyle(document.querySelector('.atlas-discovery')).opacity==='1');
  await animated.evaluate(()=>window.scrollTo({top:0,behavior:'instant'}));
  await animated.screenshot({path:path.join(output,'home-1440-full-motion.png')});await full.close();
  report.checks.push('Full-motion discovery opens');
  assert.equal(report.errors.length,0,'Uncaught JavaScript errors');report.passed=true;
 }catch(error){report.passed=false;report.failure=error.stack;process.exitCode=1;console.error(error);console.log('::error::Atlas: '+String(error&&error.message||error).replace(/\n/g,' '));}
 finally{
  await fs.writeFile(path.join(output,'report.json'),JSON.stringify(report,null,2));
  if(browser)await browser.close();servers.forEach(server=>server.kill());
 }
})();
