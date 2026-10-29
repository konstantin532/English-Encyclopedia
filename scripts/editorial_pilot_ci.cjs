/* Run the Stage 0 matrix and paired LCP sampling in the same CI environment. */
const {spawn}=require('node:child_process');
const fs=require('node:fs/promises');
const path=require('node:path');
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..');
const output=path.resolve(process.env.EE_QA_OUTPUT||'atlas-browser-evidence/editorial-pilot');
const servers=[];
async function serve(dir,port){
 const child=spawn(process.env.ATLAS_PYTHON||'python',['manage.py','runserver',`127.0.0.1:${port}`,'--noreload'],{cwd:dir,env:process.env,stdio:['ignore','ignore','pipe']});
 servers.push(child);let stderr='';child.stderr.on('data',d=>{stderr=(stderr+d).slice(-4000)});
 for(let i=0;i<150;i++){try{if((await fetch(`http://127.0.0.1:${port}/`,{signal:AbortSignal.timeout(2000)})).ok)return;}catch{}if(child.exitCode!==null)break;await new Promise(r=>setTimeout(r,200));}
 throw Error('Django failed to start: '+stderr);
}
function matrix(){return new Promise((resolve,reject)=>{const child=spawn(process.execPath,[path.join(__dirname,'editorial_pilot_qa.cjs')],{cwd:root,env:{...process.env,EE_QA_URL:'http://127.0.0.1:8157',EE_QA_OUTPUT:output},stdio:'inherit'});child.on('error',reject);child.on('exit',code=>code===0?resolve():reject(Error('Pilot matrix failed: '+code)));});}
(async()=>{let browser;try{
 await fs.mkdir(output,{recursive:true});
 await serve(root,8157);await matrix();
 await serve(process.env.ATLAS_BEFORE_DIR,8158);
 browser=await chromium.launch();const rows=[];
 for(let run=0;run<5;run++)for(const [name,route]of [['week3','/levels/a1/weeks/3/'],['lesson','/lessons/a1-cafe-order/']])for(const [stage,port]of [['before',8158],['after',8157]]){
 const context=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce'});
 try{await context.addInitScript(()=>{window.latestLCP=0;new PerformanceObserver(list=>{for(const e of list.getEntries())window.latestLCP=e.startTime}).observe({type:'largest-contentful-paint',buffered:true});});
 const page=await context.newPage();const response=await page.goto(`http://127.0.0.1:${port}${route}`,{waitUntil:'networkidle'});assert.equal(response.status(),200);await page.evaluate(()=>document.fonts.ready);
 const lcp=await page.evaluate(()=>window.latestLCP);assert.ok(lcp>0,'LCP observer produced no sample');rows.push({name,stage,run,lcp});
 }finally{await context.close();}
 }
 await fs.writeFile(path.join(output,'performance-comparison.json'),JSON.stringify(rows,null,2));
 const medians={};for(const name of ['week3','lesson'])for(const stage of ['before','after'])medians[name+'_'+stage]=rows.filter(x=>x.name===name&&x.stage===stage).map(x=>x.lcp).sort((a,b)=>a-b)[2];
 console.log('EDITORIAL_LCP_MEDIANS '+JSON.stringify(medians));console.log('PASS: editorial pilot matrix and paired performance samples.');
 }finally{if(browser)await browser.close();servers.forEach(s=>s.kill());}})().catch(e=>{console.error(e);process.exitCode=1});
