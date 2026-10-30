/* Browser acceptance for Stage 0. Install Playwright in a separate tooling folder. */
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.EE_PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.EE_QA_URL || 'http://127.0.0.1:8017';
const output = process.env.EE_QA_OUTPUT || path.resolve('artifacts/editorial-pilot');
const {learnerState} = require('./browser_auth.cjs');
const routes = { week3: '/levels/a1/weeks/3/', lesson: '/lessons/a1-cafe-order/' };
(async () => {
  await fs.mkdir(output, { recursive: true });
  const browser = await chromium.launch({ headless: true,
    ...(process.env.EE_CHROMIUM_PATH ? { executablePath: process.env.EE_CHROMIUM_PATH } : {}) });
  const storageState = await learnerState(browser, base);
  const context = await browser.newContext({storageState});
  const page = await context.newPage();
  page.setDefaultTimeout(5000);
  page.setDefaultNavigationTimeout(30000);
  const errors = [], rows = [];
  page.on('pageerror', e => errors.push(e.message));
  try {
    for (const width of [1440, 1280, 390, 360]) {
      await page.setViewportSize({ width, height: width < 700 ? 844 : 900 });
      for (const theme of ['light', 'dark']) {
        await page.emulateMedia({ colorScheme: theme, reducedMotion: 'reduce' });
        for (const [name, route] of Object.entries(routes)) {
          const response = await page.goto(base + route, { waitUntil: 'networkidle' });
          assert.equal(response.status(), 200);
          assert.equal(new URL(page.url()).pathname, route, 'unexpected learner redirect');
          await page.evaluate(() => document.fonts.ready);
          const state = await page.evaluate(({ width, theme, name }) => ({
            name, width, theme,
            overflow: document.documentElement.scrollWidth > innerWidth,
            notesMatch: [...document.querySelectorAll('[data-editorial-note]')].every(e => e.open === (width >= 1100)),
            themeAttribute: document.documentElement.dataset.theme,
            motion: document.documentElement.dataset.motion,
            font: getComputedStyle(document.querySelector('.editorial-specimen')).fontFamily,
            firstContentTop: name === 'lesson' ? document.querySelector('#layer-1 .annotated p').getBoundingClientRect().top : null,
            contentLineHeight: name === 'lesson' ? parseFloat(getComputedStyle(document.querySelector('#layer-1 .annotated p')).lineHeight) : null,
            viewportHeight: innerHeight,
            guideOpen: name === 'lesson' ? document.querySelector('[data-editorial-guide]').open : null,
          }), { width, theme, name });
          if (state.overflow) {
            state.overflowElements = await page.evaluate(() => [...document.querySelectorAll('body *')].map(e => ({tag:e.tagName,cls:e.className,x:e.getBoundingClientRect().x,right:e.getBoundingClientRect().right,width:e.getBoundingClientRect().width})).filter(e => e.width && (e.x < -1 || e.right > innerWidth+1)).slice(0,30));
            await page.screenshot({path:path.join(output, 'overflow-' + name + '-' + width + '-' + theme + '.png')});
          }
          console.log('EDITORIAL_STATE '+JSON.stringify(state));
          assert.equal(state.overflow, false, JSON.stringify(state));
          if (name === 'lesson' && width <= 390) {
            assert.ok(state.firstContentTop + 2 * state.contentLineHeight <= state.viewportHeight, 'The lesson must start on the first screen: ' + JSON.stringify(state));
          }
          assert.equal(state.notesMatch, true);
          if (name === 'lesson') assert.equal(state.guideOpen, width >= 1100);
          assert.equal(state.motion, 'minimal');
          assert.match(state.font, /Literata/);
          rows.push(state);
          await page.screenshot({ path: path.join(output, name + '-' + width + '-' + theme + '.png') });
          if (name === 'week3') {
            await page.locator('label').filter({ has: page.locator('input[name=listen][value=hidden]') }).click();
            await page.waitForFunction(() => getComputedStyle(document.querySelector('.line-text')).visibility === 'hidden');
            assert.equal(await page.locator('.line-full:visible').count(), 0);
            await page.locator('label').filter({ has: page.locator('input[name=listen][value=text]') }).click();
            await page.waitForFunction(() => getComputedStyle(document.querySelector('.line-text')).visibility === 'visible');
            await page.locator('label').filter({ has: page.locator('input[name=speech][value=written]') }).click();
            assert.equal(await page.locator('.editorial-full-note:visible').count(), 0);
            await page.locator('label').filter({ has: page.locator('input[name=speech][value=spoken]') }).click();
            await page.locator('.story-script').evaluate(e => e.scrollIntoView({ block: 'start' }));
            await page.screenshot({ path: path.join(output, 'dialogue-' + width + '-' + theme + '.png') });
          }
          if (name === 'lesson') {
            await page.locator('[data-lesson-reader]').evaluate(e => e.scrollIntoView({ block: 'start' }));
            await page.screenshot({ path: path.join(output, 'lesson-reading-' + width + '-' + theme + '.png') });
          }
          if (width < 1100) {
            if (name === 'lesson') {
              const guide = page.locator('[data-editorial-guide]');
              const summary = guide.locator(':scope > summary');
              await summary.focus();
              await page.keyboard.press('Enter');
              assert.equal(await guide.evaluate(e => e.open), true);
              await page.keyboard.press('Space');
              assert.equal(await guide.evaluate(e => e.open), false);
              await page.keyboard.press('Enter');
            }
            const note = page.locator('[data-editorial-note]').first();
            await note.locator('summary').focus();
            await page.keyboard.press('Enter');
            assert.equal(await note.evaluate(e => e.open), true);
            await page.keyboard.press('Enter');
            assert.equal(await note.evaluate(e => e.open), false);
          }
        }
      }
    }
    await page.setViewportSize({ width: 360, height: 844 });
    await page.emulateMedia({ forcedColors: 'active' });
    for (const route of Object.values(routes)) {
      await page.goto(base + route, { waitUntil: 'networkidle' });
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    }
    await page.emulateMedia({ forcedColors: 'none' });
    await page.goto(base + routes.lesson, { waitUntil: 'networkidle' });
    const initial = await page.locator('[data-lesson-reader]').evaluate(e => parseFloat(getComputedStyle(e).fontSize));
    await page.locator('[data-reader-larger]').click();
    await page.waitForFunction(initial => parseFloat(getComputedStyle(document.querySelector('[data-lesson-reader]')).fontSize) > initial, initial);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    const nojs = await browser.newContext({ storageState, javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
    const fallback = await nojs.newPage();
    for (const route of Object.values(routes)) {
      await fallback.goto(base + route, { waitUntil: 'networkidle' });
      assert.equal(await fallback.locator('[data-editorial-note]').evaluateAll(es => es.length > 0 && es.every(e => e.open)), true);
      if (route === routes.lesson) {
        await fallback.evaluate(() => document.fonts.ready);
        const visibleStart = await fallback.locator('#layer-1 .annotated p').first().evaluate(e => e.getBoundingClientRect().top + 2 * parseFloat(getComputedStyle(e).lineHeight) <= innerHeight);
        assert.equal(visibleStart, true, 'The lesson must also start on the first screen without JavaScript');
        const guide = fallback.locator('[data-editorial-guide]');
        assert.equal(await guide.evaluate(e => e.open), false);
        await guide.locator(':scope > summary').focus();
        await fallback.keyboard.press('Enter');
        assert.equal(await guide.evaluate(e => e.open), true);
        assert.ok(await fallback.locator('[data-editorial-note]:visible').count() > 0);
      }
    }
    await nojs.close();
    assert.deepEqual(errors, []);
    await fs.writeFile(path.join(output, 'checks.json'), JSON.stringify({ rows, errors, keyboard: 'PASS', noJS: 'PASS', forcedColors: 'PASS', readerScale: 'PASS' }, null, 2));
    console.log('PASS: 16 viewport/theme combinations; dialogue modes, keyboard, no-JS, forced-colors, reader size.');
    console.log('Known baseline limitation: system dark preference still leaves data-theme=light.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
