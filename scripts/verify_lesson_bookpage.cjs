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
async function geometry(page){
  return page.evaluate(()=>Object.fromEntries(['.studio-sidebar','.site-header','.page-head','.lesson-grid','.aside'].map(selector=>{
    const r=document.querySelector(selector).getBoundingClientRect();
    // Reading length changes intentionally; column position/width must not.
    return [selector,{x:r.x,width:r.width}];
  })));
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
        // Record the same three regions for each checkout, before interactions.
        await page.screenshot({path:path.join(output,`noun-${width}-${state}-top.png`)});
        await page.locator('#layer-1').screenshot({path:path.join(output,`noun-${width}-${state}-explanation.png`)});
        await page.locator('.speech-mode-grid').screenshot({path:path.join(output,`noun-${width}-${state}-speech.png`)});
        entry.activatedSpeech=await colors(page.locator('.speech-mode-grid [data-speech-mode="see"]'));
        if(state==='after'){
          await page.locator('[data-a1-route-mode="essentials"]').focus();
          for(const mode of ['reasons','full']){
            await page.keyboard.press('Tab');
            assert.equal(await page.locator(`[data-a1-route-mode="${mode}"]`).evaluate(el=>el===document.activeElement),true,'depth keyboard order');
          }
          await page.keyboard.press('Shift+Tab');
          assert.equal(await page.locator('[data-a1-route-mode="reasons"]').evaluate(el=>el===document.activeElement),true,'reverse depth keyboard order');
          entry.keyboardControlOrder=true;
          const expected={essentials:[2,4,6],reasons:[6],full:[]};
          for(const mode of ['essentials','reasons','full','essentials','full']){
            const button=page.locator(`[data-a1-route-mode="${mode}"]`);
            await button.focus();await button.press('Enter');
            assert.equal(await button.getAttribute('aria-pressed'),'true');
            const hidden=[];
            for(let n=1;n<=7;n++)if(!await page.locator(`#layer-${n}`).isVisible())hidden.push(n);
            assert.deepEqual(hidden,expected[mode]);
            assert.match(await page.locator('[data-a1-route-status]').innerText(),new RegExp(`${7-hidden.length} из 7`));
            assert.equal(await page.locator('.a1-clarity-bridge').isVisible(),true);
            assert.equal(await page.locator('#practice').isVisible(),true);
            const pair=await colors(button);entry.contrasts.push({control:'depth',mode,...pair});
            assert.ok(pair.ratio>=4.5,`depth ${mode} contrast ${pair.ratio}`);
            const focus=await button.evaluate(el=>({active:el===document.activeElement,style:getComputedStyle(el).outlineStyle,width:parseFloat(getComputedStyle(el).outlineWidth)}));
            assert.equal(focus.active,true);assert.notEqual(focus.style,'none');assert.ok(focus.width>=2);
          }
          await page.locator('[data-a1-route-mode="essentials"]').click();
          await page.locator('.toc a[href="#layer-2"]').click();
          // The browser dispatches hashchange asynchronously after the click.
          // Wait for its real outcome; a broken handler still fails this gate.
          await page.locator('#layer-2').waitFor({state:'visible'});
          assert.equal(await page.locator('#layer-2').isVisible(),true);
          assert.equal(await page.locator('[data-a1-route-mode="full"]').getAttribute('aria-pressed'),'true');
          for(const mode of ['see','echo','recall','transfer']){
            const button=page.locator(`.speech-mode-grid [data-speech-mode="${mode}"]`);
            await button.focus();await button.press('Enter');
            assert.equal(await button.getAttribute('aria-pressed'),'true');
            await button.hover();
            const pair=await colors(button);entry.contrasts.push({control:'speech',mode,...pair});
            assert.ok(pair.ratio>=4.5,`speech ${mode} contrast ${pair.ratio}`);
          }
          const summary=page.locator('#beginner-steps > summary');
          await summary.focus();await summary.press('Enter');
          assert.equal(await summary.evaluate(el=>el.parentElement.open),true);
          const paragraph=page.locator('#layer-1 .annotated > p').first();
          // Use the guaranteed-minimum reader size so a stored/max size cannot mask A+.
          for(let i=0;i<12;i++)if(await page.locator('[data-reader-smaller]').isEnabled())await page.locator('[data-reader-smaller]').click();
          const small=await paragraph.evaluate(el=>parseFloat(getComputedStyle(el).fontSize));
          await page.locator('[data-reader-larger]').focus();await page.locator('[data-reader-larger]').press('Enter');
          assert.ok(await paragraph.evaluate(el=>parseFloat(getComputedStyle(el).fontSize))>small,'reader scale no longer reaches paragraphs');
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
    assert.equal(await page.locator('[data-a1-learning-route]').isVisible(),false);
    await page.screenshot({path:path.join(output,'noun-390-after-no-js.png')});report.noJavaScript=true;
  }finally{await nojs.close();}
  report.passed=true;
}
module.exports={contrastRatio,verifyLessonBookpage};
