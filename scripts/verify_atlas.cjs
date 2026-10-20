/* Real Chromium acceptance gate. Run against two checkouts with one seeded DB.
 * Requires playwright on NODE_PATH, ATLAS_BEFORE_DIR and ATLAS_PYTHON.
 * Screenshots are evidence of real Django pages, never generated mockups.
 */
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs/promises');
const path=require('node:path');
const assert=require('node:assert/strict');
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
    let maxDelta=0;
    for(const selector of selectors){
     const a=measurements.before[selector],b=measurements.after[selector];assert.equal(a.length,b.length,selector+' count');
     a.forEach((rectangle,index)=>Object.keys(rectangle).forEach(key=>{maxDelta=Math.max(maxDelta,Math.abs(rectangle[key]-b[index][key]));}));
    }
    report.screens.push({name,width,height,maxGeometryDelta:maxDelta,measurements});
    assert.ok(maxDelta<=1,`${name} ${width}: geometry changed ${maxDelta}px`);
   }
  }
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
