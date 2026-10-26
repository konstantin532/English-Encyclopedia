/* Call with an already authenticated, disposable Playwright BrowserContext.
 * Never creates users, starts a server, migrates, or touches a working database.
 * const {verify}=require('./scripts/verify_vocabulary_trainer.cjs');
 * await verify(context,{baseURL:'http://127.0.0.1:8765',outputDir:'/tmp/trainer-qa',otherContext});
 */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const UIDS = ['LX-00055', 'LX-00285', 'LX-00084'];
async function verify(context, { baseURL, outputDir, otherContext, noJS = true } = {}) {
  assert.ok(baseURL, 'Explicit disposable preview baseURL is required');
  const checks = [], screenshots = [], errors = [];
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  const root = () => page.locator('[data-vocabulary-trainer]');
  async function phase(expected) {
    await page.waitForFunction(value => document.querySelector('[data-vocabulary-trainer]')?.dataset.phase === value, expected);
    checks.push({ check: `phase:${expected}`, status: 'PASS' });
  }
  async function shot(name) {
    if (!outputDir) return;
    await fs.mkdir(outputDir, { recursive: true });
    const filename = path.join(outputDir, name + '.png');
    await page.screenshot({ path: filename, fullPage: true }); screenshots.push(filename);
  }
  async function layout(width, textScale, name) {
    await page.setViewportSize({ width, height: 900 });
    await page.evaluate(scale => { document.documentElement.style.fontSize = scale + '%'; }, textScale);
    const result = await page.evaluate(() => {
      const scope = document.querySelector('[data-vocabulary-trainer]');
      const controls = [...scope.querySelectorAll('button, textarea, input:not([type=hidden]):not([type=radio]):not([type=checkbox])')]
        .filter(el => el.getClientRects().length);
      return { viewport: innerWidth, fullWidth: document.documentElement.scrollWidth,
        controls: controls.map(el => ({ text: el.textContent.slice(0, 30), height: el.getBoundingClientRect().height,
          left: el.getBoundingClientRect().left, right: el.getBoundingClientRect().right })) };
    });
    assert.ok(result.fullWidth <= result.viewport + 1, `overflow ${name}: ${JSON.stringify(result)}`);
    assert.ok(result.controls.every(c => c.height >= 47 && c.left >= 0 && c.right <= width + 1), `controls ${name}: ${JSON.stringify(result)}`);
    checks.push({ check: `layout:${width}px:${textScale}%`, status: 'PASS' });
    await shot(name);
  }
  async function action(value) {
    const before = await root().getAttribute('data-revision');
    await root().locator(`button[name="action"][value="${value}"]`).click();
    await page.waitForFunction(previous => document.querySelector('[data-vocabulary-trainer]')?.dataset.revision !== previous, before);
  }
  try {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(new URL('/learning/vocabulary/', baseURL).href);
    assert.equal(await root().count(), 1, 'Authenticated trainer entry must render');
    const optin = root().locator('input[name="prerequisites"]');
    if (await optin.count()) {
      await optin.check();
      await root().locator('input[name="timezone_name"]').fill('UTC');
      await root().getByRole('button', { name: 'Включить тренажёр', exact: true }).click();
      await root().locator('input[name="uid"]').first().waitFor();
    }
    let privateSessionURL;
    for (let index = 0; index < UIDS.length; index++) {
      await page.goto(new URL('/learning/vocabulary/', baseURL).href);
      const start = root().locator(`form:has(input[name="uid"][value="${UIDS[index]}"]) button`);
      assert.equal(await start.count(), 1, 'Use a fresh disposable user with no open encounters');
      await start.click(); await phase('intro');
      assert.match(await root().innerText(), /AI-рецензию/);
      await root().locator('textarea[name="mnemonic"]').fill('Моя связь <script>window.trainerInjected=true</script>');
      const previousMnemonic = await root().locator('#trainer-mnemonic').elementHandle();
      await root().getByRole('button', { name: 'Сохранить мнемонику', exact: true }).click();
      await page.waitForFunction(element => !element.isConnected, previousMnemonic);
      await action('begin'); await phase('recall');
      privateSessionURL = page.url();
      assert.equal(await root().locator('.trainer-model, .trainer-memory, #trainer-mnemonic, [data-model]').count(), 0);
      assert.equal(await page.evaluate(() => !!window.trainerInjected), false);
      assert.doesNotMatch(await page.title(), /tea|I'd like|repeat that/i);
      checks.push({ check: `withheld-target:${UIDS[index]}`, status: 'PASS' });
      if (index === 0) {
        await root().locator('#trainer-answer').fill('My private typed idea');
        const posts = []; let first = true;
        await page.route('**/learning/vocabulary/*/', async route => {
          if (route.request().method() !== 'POST') return route.continue();
          posts.push(route.request().postData());
          if (first) { first = false; await route.fetch(); return route.abort('failed'); }
          return route.continue();
        });
        await root().locator('button[value="hint"]').evaluate(button => { button.click(); button.click(); });
        await root().locator('[data-trainer-network]').waitFor({ state: 'visible' });
        assert.equal(await root().locator('#trainer-answer').inputValue(), 'My private typed idea');
        assert.equal(posts.length, 1, 'Rapid double activation must send once');
        checks.push({ check: 'double-submit-lock', status: 'PASS' });
        await root().locator('[data-trainer-retry]').click();
        await root().locator('.trainer-memory').waitFor();
        assert.equal(posts[0], posts[1], 'Ambiguous accepted POST must replay the exact operation token/payload');
        await page.unroute('**/learning/vocabulary/*/');
        checks.push({ check: 'accepted-response-loss:same-token-retry', status: 'PASS' });
        await action('reveal');
        await root().getByRole('link', { name: 'Урок 5', exact: true }).click();
        await page.goBack(); await phase('recall');
        assert.match(await root().innerText(), /Зарегистрирована помощь/);
        await action('dont_know'); await phase('feedback');
        checks.push({ check: 'back:sticky-assistance:canonical', status: 'PASS' });
      } else if (index === 1) {
        await root().locator('#trainer-answer').fill('A thoughtful unlisted answer.');
        await action('recall'); await phase('feedback');
      } else {
        await root().locator('input[name="mode"][value="spoken"]').check();
        await action('recall'); await phase('spoken_compare');
        assert.equal(await root().locator('audio, input[type="file"]').count(), 0);
        await root().locator('input[name="self_rating"][value="hard"]').check();
        await action('rate_spoken'); await phase('feedback');
      }
      await action('continue'); await phase('application');
      assert.equal(await root().locator('button[value="apply"]').count(), 0, 'Self-assessment follows comparison');
      await root().locator('#trainer-answer').fill('My own useful response.');
      await action('reveal_application');
      assert.equal(await root().locator('#trainer-answer').inputValue(), 'My own useful response.');
      assert.ok(await root().locator('li[lang="en"]').count() >= 2);
      if (index === 0) {
        await layout(390, 100, 'application-390');
        await layout(320, 100, 'application-320');
        await layout(1280, 100, 'application-desktop');
        await layout(1280, 200, 'application-desktop-text200');
        await layout(390, 200, 'application-390-text200');
        await layout(320, 200, 'application-320-text200');
        await page.evaluate(() => { document.documentElement.style.fontSize = '100%'; });
        await page.setViewportSize({ width: 390, height: 844 });
        await root().locator('#trainer-answer').focus(); await page.keyboard.press('Tab');
        const focus = await page.evaluate(() => ({ tag: document.activeElement.tagName,
          outline: getComputedStyle(document.activeElement).outlineStyle }));
        assert.notEqual(focus.outline, 'none');
        checks.push({ check: 'keyboard:tab-visible-focus', status: 'PASS' });
      }
      if (index === 0) {
        await root().locator('input[name="self_rating"][value="good"]').focus();
        await page.keyboard.press('Space');
        await root().locator('button[value="apply"]').focus();
        await page.keyboard.press('Enter');
        checks.push({ check: 'keyboard:space-radio-enter-submit', status: 'PASS' });
      } else {
        await root().locator('input[name="self_rating"][value="good"]').check();
        await action('apply');
      }
      await phase('complete');
      assert.match(await root().innerText(), /Следующая встреча/);
      checks.push({ check: `complete:${UIDS[index]}`, status: 'PASS' });
    }
    if (otherContext) {
      const otherPage = await otherContext.newPage();
      const result = await otherPage.goto(privateSessionURL);
      assert.equal(result.status(), 404); await otherPage.close();
      checks.push({ check: 'other-owner:404', status: 'PASS' });
    } else checks.push({ check: 'other-owner:404', status: 'NOT_RUN', reason: 'Supply otherContext; HTTP tests cover ownership.' });
    if (noJS) {
      const browser = context.browser();
      assert.ok(browser, 'noJS check needs a browser-backed context');
      const plain = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
      await plain.addCookies(await context.cookies());
      const plainPage = await plain.newPage();
      await plainPage.goto(new URL('/learning/vocabulary/', baseURL).href);
      await plainPage.locator(`form:has(input[name="uid"][value="${UIDS[0]}"]) button`).click();
      await plainPage.locator('#trainer-answer').fill('Saved with normal HTML POST.');
      await plainPage.locator('button[value="save_draft"]').click();
      assert.equal(await plainPage.locator('#trainer-answer').inputValue(), 'Saved with normal HTML POST.');
      await plainPage.locator('button[value="abandon"]').click();
      assert.equal(await plainPage.locator('[data-vocabulary-trainer]').getAttribute('data-phase'), 'abandoned');
      await plain.close(); checks.push({ check: 'no-JS:POST-CSRF-PRG-draft', status: 'PASS' });
    }
    assert.deepEqual(errors, [], 'No page errors');
    checks.push({ check: 'pageerrors', status: 'PASS' });
    return { checks, screenshots, manualVisual: 'NOT_RUN — inspect screenshots separately', scope: 'Disposable fresh authenticated pilot user; no simulated browser clock.' };
  } finally { await page.close(); }
}
module.exports = { verify, UIDS };
