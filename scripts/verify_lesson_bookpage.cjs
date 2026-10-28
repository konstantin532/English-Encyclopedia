/* Exact first-lesson acceptance, called by the existing Atlas Chromium job.
 * Real before/after Django pages; no fixtures substituted for screenshots.
 */
const assert=require('node:assert/strict');
const path=require('node:path');

function contrastRatio(foreground,background){
  function luminance(color){
    const match=/^rgba?\(\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)(?:\s*,\s*(1(?:\.0+)?))?\s*\)$/.exec(color);
    assert.ok(match,`Expected opaque rgb color, got ${color}`);
    const channels=match.slice(1,4).map(Number);
    assert.ok(channels.every(value=>value>=0&&value<=255),'Expected opaque rgb channels in 0–255');
    const linear=channels.map(value=>{const s=value/255;return s<=.04045?s/12.92:((s+.055)/1.055)**2.4;});
    return linear[0]*.2126+linear[1]*.7152+linear[2]*.0722;
  }
  const a=luminance(foreground),b=luminance(background);
  return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
}
async function colors(locator){
  const pair=await locator.evaluate(el=>{const c=getComputedStyle(el);return {foreground:c.color,background:c.backgroundColor};});
  return {...pair,ratio:contrastRatio(pair.foreground,pair.background)};
}
function visibleLayoutBounds(display,bounds,childBounds){
  // display:contents has no own CSS box; compare the first visible panel instead.
  const visible=display==='contents'?childBounds:bounds;
  assert.ok(visible,'display:contents requires a visible child layout box');
  assert.ok(visible.width>0,'visible layout box must have positive width');
  return {x:visible.x,width:visible.width};
}
async function geometry(page){
  const boxes=await page.evaluate(()=>Object.fromEntries(['.studio-sidebar','.site-header','.page-head','.lesson-grid','.aside'].map(selector=>{
    const el=document.querySelector(selector),r=el.getBoundingClientRect();
    const display=getComputedStyle(el).display;
    const child=display==='contents'?el.firstElementChild?.getBoundingClientRect():null;
    return [selector,{display,bounds:{x:r.x,width:r.width},child:child?{x:child.x,width:child.width}:null}];
  })));
  return Object.fromEntries(Object.entries(boxes).map(([selector,box])=>[selector,visibleLayoutBounds(box.display,box.bounds,box.child)]));
}
async function verifyBeginnerLesson(page,label='lesson'){
  const card=page.locator('#beginner-steps.a1-clarity-bridge');
  assert.equal(await card.count(),1,`${label}: minute card missing`);
  assert.equal(await card.isVisible(),true,`${label}: minute card hidden`);
  assert.deepEqual(await card.locator('dl > dt').allTextContents(),['Что это?','Почему работает?','Простая схема','Типичная ошибка','Как исправить']);
  const explanations=await card.locator('dl > dd').allTextContents();
  assert.equal(explanations.length,5,`${label}: minute card incomplete`);
  assert.ok(explanations.every(text=>text.trim()),`${label}: empty explanation`);
  assert.equal(await card.locator('blockquote [lang="en"]').count(),1);
  assert.equal(await card.locator('.a1-contrast-pairs > p').count(),2);
  assert.equal(await card.locator('.a1-step-list').count(),0,'removed ladder must not duplicate the minute card');
  const flow=await page.evaluate(()=>{
    const selectors=['#beginner-steps','[data-lesson-reader]','#practice','#translate','#lesson-complete','#lesson-extra-practice'];
    const nodes=selectors.map(selector=>document.querySelector(selector));
    return {present:nodes.every(Boolean),ordered:nodes.every((node,index)=>!index||Boolean(nodes[index-1]?.compareDocumentPosition(node)&Node.DOCUMENT_POSITION_FOLLOWING)),
      completion:document.querySelector('#lesson-complete-title')?.textContent.trim(),
      optionalTag:nodes[5]?.tagName,optionalOpen:nodes[5]?.open,
      independentInside:Boolean(nodes[5]?.querySelector('a[href*="/independent/"]')),speechInside:Boolean(nodes[5]?.querySelector('#spoken-coach'))};
  });
  assert.deepEqual(flow,{present:true,ordered:true,completion:'Урок пройден ✓',optionalTag:'DETAILS',optionalOpen:false,independentInside:true,speechInside:true},`${label}: core → completion → closed optional practice`);
  assert.equal(await page.locator('#lesson-extra-practice > summary').innerText(),'Ещё практика (по желанию)');
}
async function openExtraPractice(page){
  const summary=page.locator('#lesson-extra-practice > summary');
  await summary.focus();await summary.press('Enter');
  assert.equal(await summary.evaluate(el=>el.parentElement.open),true,'optional practice must open from the keyboard');
  assert.equal(await page.locator('#spoken-coach').isVisible(),true,'speech workshop hidden after opening optional practice');
}
async function verifyLessonBookpage(browser,{output,beforeBase,afterBase,report}){
  const route='/lessons/a1-nouns-first-words/';
  report.screens=[];
  for(const [width,height] of [[1440,900],[390,844]]){
    const measurements={};
    for(const [state,base] of [['before',beforeBase],['after',afterBase]]){
      const context=await browser.newContext({viewport:{width,height},reducedMotion:'reduce',isMobile:width<700,hasTouch:width<700});
      const entry={state,width,contrasts:[]};report.screens.push(entry);
      try{
        const page=await context.newPage();
        const errors=[];page.on('pageerror',error=>errors.push(error.message));
        const response=await page.goto(base+route,{waitUntil:'networkidle'});
        assert.equal(response.status(),200);await page.evaluate(()=>document.fonts.ready);
        assert.equal(new URL(page.url()).pathname,route);
        entry.pilot=await page.locator('[data-lesson-bookpage]').count();
        if(state==='after')assert.equal(entry.pilot,1,'pilot page missing');
        assert.equal(await page.locator('html').getAttribute('data-motion'),'minimal');
        const box=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));
        entry.overflow=box;assert.ok(box.scroll<=box.width+1,`${state} noun ${width}: overflow`);
        measurements[state]=await geometry(page);
        entry.geometry=measurements[state];
        if(state==='after')await verifyBeginnerLesson(page,`noun ${width}`);
        // Record the same three regions for each checkout, before interactions.
        await page.screenshot({path:path.join(output,`noun-${width}-${state}-top.png`)});
        await page.locator('#layer-1').screenshot({path:path.join(output,`noun-${width}-${state}-explanation.png`)});
        // The workshop is now optional: prove its initial closed state, then
        // open the real details control before measuring its speech controls.
        // Since PR #137 the base branch also folds the workshop; open it in any checkout that has it.
        if(state==='after'||await page.locator('#lesson-extra-practice').count())await openExtraPractice(page);
        await page.locator('.speech-mode-grid').screenshot({path:path.join(output,`noun-${width}-${state}-speech.png`)});
        entry.activatedSpeech=await colors(page.locator('.speech-mode-grid [data-speech-mode="see"]'));
        if(state==='after'){
          assert.equal(await page.locator('[data-a1-full-lesson]').count(),1);
          assert.equal(await page.locator('[data-a1-learning-route], [data-a1-route-mode]').count(),0,'depth menu must be removed');
          assert.equal(await page.locator('[data-route-availability]').count(),0,'contents must not advertise hidden depth');
          const assertComplete=async()=>{
            for(let n=1;n<=7;n++){
              const layer=page.locator(`#layer-${n}`);
              assert.equal(await layer.count(),1,`layer ${n} duplicated or missing`);
              assert.equal(await layer.isVisible(),true,`layer ${n} hidden`);
              const link=page.locator(`.toc a[href="#layer-${n}"]`);
              assert.equal(await link.count(),1);
              assert.notEqual(await link.getAttribute('aria-disabled'),'true');
              assert.notEqual(await link.getAttribute('tabindex'),'-1');
            }
            assert.equal(await page.locator('.a1-clarity-bridge').isVisible(),true);
            assert.equal(await page.locator('#practice').isVisible(),true);
          };
          await assertComplete();
          const bridge=await page.locator('.a1-clarity-bridge').evaluate(el=>{
            const c=getComputedStyle(el);
            return {background:c.backgroundColor,topColor:c.borderTopColor,topWidth:c.borderTopWidth};
          });
          assert.deepEqual(bridge,{background:'rgb(243, 240, 230)',topColor:'rgb(145, 109, 52)',topWidth:'3px'});
          entry.clarityBridge=bridge;
          const second=page.locator('.toc a[href="#layer-2"]');
          await second.focus();
          await page.keyboard.press('Tab');
          const third=page.locator('.toc a[href="#layer-3"]');
          assert.equal(await third.evaluate(el=>el===document.activeElement),true,'contents keyboard order');
          await page.keyboard.press('Shift+Tab');
          assert.equal(await second.evaluate(el=>el===document.activeElement),true,'reverse contents keyboard order');
          const focus=await second.evaluate(el=>({style:getComputedStyle(el).outlineStyle,width:parseFloat(getComputedStyle(el).outlineWidth)}));
          assert.notEqual(focus.style,'none');assert.ok(focus.width>=2);
          await second.press('Enter');
          assert.equal(new URL(page.url()).hash,'#layer-2');
          for(const n of [6,2,3]){
            await page.locator(`.toc a[href="#layer-${n}"]`).focus();
            await page.keyboard.press('Enter');
            assert.equal(new URL(page.url()).hash,`#layer-${n}`);
            await assertComplete();
          }
          await page.reload({waitUntil:'networkidle'});
          await assertComplete();
          await verifyBeginnerLesson(page,`noun ${width} after reload`);
          await openExtraPractice(page);
          entry.keyboardContentsOrder=true;entry.completeLesson=true;
          for(const mode of ['see','echo','recall','transfer']){
            const button=page.locator(`.speech-mode-grid [data-speech-mode="${mode}"]`);
            await button.focus();await button.press('Enter');
            assert.equal(await button.getAttribute('aria-pressed'),'true');
            await button.hover();
            const pair=await colors(button);entry.contrasts.push({control:'speech',mode,...pair});
            assert.ok(pair.ratio>=4.5,`speech ${mode} contrast ${pair.ratio}`);
          }
          entry.minuteCard=true;entry.optionalPracticeKeyboard=true;
          const paragraph=page.locator('#layer-1 .annotated > p').first();
          // Use the guaranteed-minimum reader size so a stored/max size cannot mask A+.
          for(let i=0;i<12;i++)if(await page.locator('[data-reader-smaller]').isEnabled())await page.locator('[data-reader-smaller]').click();
          const readerState=()=>page.evaluate(()=>{
            const reader=document.querySelector('[data-lesson-reader]');
            const layer=document.querySelector('#layer-1');
            const paragraph=layer.querySelector('.annotated > p');
            return {reader:getComputedStyle(reader).fontSize,inline:reader.style.fontSize,layer:getComputedStyle(layer).fontSize,parent:getComputedStyle(paragraph.parentElement).fontSize,paragraph:getComputedStyle(paragraph).fontSize,output:document.querySelector('[data-reader-size]').textContent,largerDisabled:document.querySelector('[data-reader-larger]').disabled};
          });
          // Even reduced-motion's 0.01ms CSS transitions settle on a render frame.
          // Do not compare a stale child size with the next parent-size update.
          await page.waitForFunction(()=>{
            const reader=document.querySelector('[data-lesson-reader]');
            const paragraph=document.querySelector('#layer-1 .annotated > p');
            return parseFloat(getComputedStyle(paragraph).fontSize)===parseFloat(reader.style.fontSize);
          });
          entry.readerBefore=await readerState();
          const small=await paragraph.evaluate(el=>parseFloat(getComputedStyle(el).fontSize));
          await page.locator('[data-reader-larger]').focus();await page.locator('[data-reader-larger]').press('Enter');
          await page.waitForFunction(previous=>parseFloat(getComputedStyle(document.querySelector('#layer-1 .annotated > p')).fontSize)>previous,small);
          entry.readerAfter=await readerState();
          assert.ok(await paragraph.evaluate(el=>parseFloat(getComputedStyle(el).fontSize))>small,'reader scale no longer reaches paragraphs: '+JSON.stringify({before:entry.readerBefore,after:entry.readerAfter}));
          entry.keyboard=true;entry.modes=true;entry.readerScale=true;
        }
        assert.deepEqual(errors,[],'uncaught noun-page JS errors');
      }finally{await context.close();}
    }
    for(const selector of Object.keys(measurements.before))for(const key of ['x','width']){
      assert.ok(Math.abs(measurements.before[selector][key]-measurements.after[selector][key])<=1,`noun ${width}: ${selector} ${key} changed`);
    }
  }
  const nojs=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}});
  try{
    const page=await nojs.newPage();const response=await page.goto(afterBase+route,{waitUntil:'networkidle'});assert.equal(response.status(),200);
    for(let n=1;n<=7;n++)assert.equal(await page.locator(`#layer-${n}`).isVisible(),true);
    await verifyBeginnerLesson(page,'no-JS noun');
    await openExtraPractice(page);
    assert.equal(await page.locator('[data-a1-learning-route], [data-a1-route-mode]').count(),0);
    await page.screenshot({path:path.join(output,'noun-390-after-no-js.png')});report.noJavaScript=true;
  }finally{await nojs.close();}
  report.passed=true;
}
module.exports={contrastRatio,visibleLayoutBounds,verifyBeginnerLesson,openExtraPractice,verifyLessonBookpage};
