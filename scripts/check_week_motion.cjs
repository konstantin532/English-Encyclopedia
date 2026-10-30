/* Real-browser acceptance. Run with an isolated seeded server, like visual_review.cjs.
 * WEEK_MOTION_URL=http://127.0.0.1:8134 node scripts/check_week_motion.cjs
 * Requires Playwright on NODE_PATH; never changes course data. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {chromium, firefox} = require('playwright');
const base = process.env.WEEK_MOTION_URL || 'http://127.0.0.1:8134';
const route = '/levels/a1/weeks/1/';
const passed = [];
const blocked = [];
function pass(message) { passed.push(message); console.log('PASS ' + message); }

async function settled(page) {
  await page.waitForFunction(() => !document.querySelector('[data-week-flip-running]'));
}
async function exercise(browser) {
  const context = await browser.newContext({viewport: {width: 1440, height: 900}});
  context.setDefaultTimeout(15000);
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.goto(base + route);
    await page.waitForFunction(() => window.Flip && window.ScrollTrigger && window.SplitText);
    await page.waitForFunction(() => !document.querySelector('h1 [aria-hidden]'));
    assert.equal(await page.locator('h1').count(), 1);
    assert.ok(await page.evaluate(() => ScrollTrigger.getAll().length > 0));
    const card = page.locator('[data-week-flip]').first();
    const summary = card.locator('summary');
    const link = card.getByRole('link', {name: /Открыть урок/});
    assert.ok(await link.isVisible());
    await summary.focus();
    await summary.press('Enter');
    const timing = await card.evaluate(el => window.Flip.getByTarget(el)?.duration());
    assert.ok(timing >= 0.18 && timing <= 0.45, `Flip duration ${timing}`);
    await settled(page);
    assert.equal(await card.getAttribute('open'), null);
    assert.ok(await summary.evaluate(el => el === document.activeElement));
    await summary.press('Space');
    await settled(page);
    assert.ok(await link.isVisible());
    for (let i = 0; i < 5; i++) await summary.press('Enter');
    await settled(page);
    assert.equal(await card.getAttribute('open'), null);
    await summary.press('Space');
    await settled(page);
    assert.ok(await link.isVisible());
    assert.equal(await card.evaluate(el => el.style.height), '');
    pass('Flip: real timeline 180–450ms, Enter/Space, repeated interruption, focus and clean geometry');

    await summary.press('Enter');
    await page.emulateMedia({reducedMotion: 'reduce'});
    await page.waitForFunction(() => document.documentElement.dataset.motion === 'minimal');
    await settled(page);
    assert.equal(await page.evaluate(() => ScrollTrigger.getAll().length), 0);
    assert.equal(await card.evaluate(el => el.style.height), '');
    await summary.press('Space');
    assert.ok(await link.isVisible());
    assert.equal(await page.locator('[data-week-flip-running]').count(), 0);
    pass('System reduced motion: interruption settles layout, triggers removed, native disclosure works');

    await page.emulateMedia({reducedMotion: 'no-preference'});
    await page.locator('[data-motion-control]:visible').first().selectOption('balanced');
    await page.waitForFunction(() => ScrollTrigger.getAll().length > 0);
    await page.locator('[data-motion-control]:visible').first().selectOption('minimal');
    await page.waitForFunction(() => ScrollTrigger.getAll().length === 0);
    pass('Manual Minimal: follows the existing motion control');
    assert.deepEqual(errors, []);
  } finally { await context.close(); }

  for (const dependency of ['gsap', 'Flip', 'ScrollTrigger', 'SplitText']) {
    const fallback = await browser.newContext();
    fallback.setDefaultTimeout(15000);
    const p = await fallback.newPage();
    const failures = [];
    p.on('pageerror', e => failures.push(e.message));
    await p.route(`**/static/vendor/gsap/${dependency}.min.js`, request => request.abort());
    try {
      await p.goto(base + route);
      const card = p.locator('[data-week-flip]').first();
      await card.locator('summary').click();
      await settled(p);
      await card.locator('summary').click();
      await settled(p);
      assert.ok(await card.getByRole('link', {name: /Открыть урок/}).isVisible());
      assert.deepEqual(failures, []);
      pass(`Missing ${dependency}: readable title, usable cards, no JS exception`);
    } finally { await fallback.close(); }
  }

  const noJS = await browser.newContext({javaScriptEnabled: false, viewport: {width: 390, height: 844}});
  try {
    const p = await noJS.newPage();
    await p.goto(base + route);
    const cards = p.locator('[data-week-flip]');
    assert.ok(await cards.count() > 0);
    for (const card of await cards.all()) {
      assert.ok(await card.getByRole('link', {name: /Открыть урок/}).isVisible());
      assert.notEqual(await card.getAttribute('open'), null);
    }
    assert.equal(await p.locator('#dialogue').count(), 1);
    assert.ok(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    pass('No JavaScript at 390px: all lesson summaries and navigation visible');
  } finally { await noJS.close(); }
}

async function navigation(browser, expected) {
  const context = await browser.newContext();
  context.setDefaultTimeout(15000);
  const page = await context.newPage();
  try {
    await page.addInitScript(() => window.addEventListener('pagereveal', event => {
      window.motionTransition = event.viewTransition ? 'pending' : 'none';
      if (event.viewTransition) event.viewTransition.ready.then(() => { window.motionTransition = 'ready'; })
        .catch(error => { window.motionTransition = error.message; });
    }));
    await page.goto(base + '/levels/a1/');
    const names = await page.locator('[style*="view-transition-name"]').evaluateAll(nodes => nodes.map(n => getComputedStyle(n).viewTransitionName));
    assert.equal(names.length, new Set(names).size);
    await page.locator(`.atlas-week-card[href="${route}"]`).click();
    await page.waitForURL('**' + route);
    if (expected) await page.waitForFunction(() => window.motionTransition && window.motionTransition !== 'pending');
    assert.equal(await page.locator('h1').textContent(), 'Знакомство с соседом');
    if (expected) assert.equal(await page.evaluate(() => window.motionTransition), 'ready');
    else assert.ok(await page.evaluate(() => !window.motionTransition || window.motionTransition === 'none'));
    await page.goBack();
    await page.waitForURL('**/levels/a1/');
    await page.locator(`.atlas-week-card[href="${route}"]`).click();
    await page.waitForURL('**' + route);
    if (expected) {
      await page.waitForFunction(() => window.motionTransition && window.motionTransition !== 'pending');
      assert.equal(await page.evaluate(() => window.motionTransition), 'ready');
    }
    await page.waitForFunction(() => !document.querySelector('h1 [aria-hidden]'));
    pass(`${expected ? 'Chromium shared-element' : 'Firefox normal'} navigation and history restore`);
  } finally { await context.close(); }
}

(async () => {
  const browser = await chromium.launch();
  try { await exercise(browser); await navigation(browser, true); }
  finally { await browser.close(); }
  if (fs.existsSync(firefox.executablePath())) {
    const browser = await firefox.launch();
    try { await navigation(browser, false); } finally { await browser.close(); }
  } else blocked.push('Firefox binary is unavailable');
  blocked.forEach(line => console.log('BLOCKED ' + line));
  console.log(`Week motion: ${passed.length} checks PASS, ${blocked.length} BLOCKED`);
})().catch(error => { console.error(error); process.exitCode = 1; });
