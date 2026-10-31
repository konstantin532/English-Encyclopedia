/* Visual review: screenshots of key pages before/after a change, pixel difference,
 * and a check that the main learning content is not pushed off the first screens.
 *
 * CI:    ATLAS_PYTHON, ATLAS_BEFORE_DIR (base checkout), ATLAS_BEFORE_DATABASE_URL and ATLAS_AFTER_DATABASE_URL.
 *        Two Django servers are started here, each with its own migrated and seeded database.
 * Local: VR_BEFORE_URL and VR_AFTER_URL — compare two servers that are already running.
 * Output: visual-review/ (index.html, summary.md, report.json, JPEG comparisons). Exit code 1 on new breakage.
 * Requires playwright on NODE_PATH. Pages and limits: scripts/visual_review_pages.json.
 */
'use strict';
const {chromium} = require('playwright');
const {spawn} = require('node:child_process');
const fs = require('node:fs/promises');
const path = require('node:path');
const lib = require('./visual_review_lib.cjs');
const {seedBrowserUser, learnerState, stateForAudience} = require('./browser_auth.cjs');

const root = path.resolve(__dirname, '..');
const output = path.resolve(process.env.VR_OUTPUT || 'visual-review');
const config = require('./visual_review_pages.json');
const requestedPages = process.env.VR_PAGES ? process.env.VR_PAGES.split(',').map(name => name.trim()) : null;
if (requestedPages && requestedPages.some(name => !config.pages.some(page => page.name === name))) {
  throw Error('VR_PAGES contains an unknown page name');
}
const pages = requestedPages ? config.pages.filter(page => requestedPages.includes(page.name)) : config.pages;
const MAX_CAPTURE_HEIGHT = 30000;
const STILL_CSS = '*,*::before,*::after{transition:none!important;animation:none!important;caret-color:transparent!important}';

async function serve(directory, port, databaseUrl) {
  const child = spawn(process.env.ATLAS_PYTHON || 'python', ['manage.py', 'runserver', `127.0.0.1:${port}`, '--noreload'],
    {cwd: directory, env: {...process.env, DATABASE_URL: databaseUrl, DJANGO_SETTINGS_MODULE: 'config.settings.local',
      EE_COURSE_LOGIN_REQUIRED: '1'}, stdio: ['ignore', 'ignore', 'pipe']});
  let error = '';
  child.stderr.on('data', d => { error += d; });
  for (let n = 0; n < 150; n++) {
    try { if ((await fetch(`http://127.0.0.1:${port}/`)).ok) return child; } catch {}
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  child.kill();
  throw Error(`Django did not start in ${directory}: ${error}`);
}

/** Load every image (lazy ones too) and wait until it is decoded, so slow CI machines
 * do not photograph half-loaded covers. Then scroll once for scroll-triggered UI and return to the top. */
async function settle(page) {
  await page.addStyleTag({content: STILL_CSS});
  await page.evaluate(async () => {
    await document.fonts.ready;
    const images = Array.from(document.images);
    images.forEach(img => { img.loading = 'eager'; });
    const step = Math.max(400, innerHeight);
    for (let y = 0; y < document.documentElement.scrollHeight; y += step) {
      window.scrollTo(0, y);
      await new Promise(resolve => setTimeout(resolve, 60));
    }
    window.scrollTo(0, 0);
    await Promise.race([
      Promise.all(images.map(img => (img.complete ? Promise.resolve() : new Promise(resolve => { img.addEventListener('load', resolve, {once: true}); img.addEventListener('error', resolve, {once: true}); }))
        .then(() => img.decode().catch(() => {})))),
      new Promise(resolve => setTimeout(resolve, 15000)),
    ]);
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  });
  await page.waitForLoadState('networkidle').catch(() => {});
}

async function capture(browser, base, route, viewport, mainSelector, storageState) {
  const context = await browser.newContext({
    storageState, viewport: {width: viewport.width, height: viewport.height},
    reducedMotion: 'reduce', isMobile: viewport.width < 700, hasTouch: viewport.width < 700,
  });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(`JS: ${error.message.split('\n')[0]}`));
  try {
    const response = await page.goto(base + route, {waitUntil: 'networkidle'});
    const status = response ? response.status() : 0;
    if (status !== 200) return {status, errors, problems: [`HTTP ${status}`]};
    if (new URL(page.url()).pathname !== new URL(base + route).pathname) return {status: 0, errors, problems: ['unexpected redirect: ' + new URL(page.url()).pathname]};
    await settle(page);
    const facts = await page.evaluate(selector => {
      const main = document.querySelector(selector);
      return {
        height: document.documentElement.scrollHeight,
        overflow: document.documentElement.scrollWidth > innerWidth + 1 ? document.documentElement.scrollWidth - innerWidth : 0,
        mainTop: main ? Math.round(main.getBoundingClientRect().top + scrollY) : null,
      };
    }, mainSelector);
    const height = Math.min(facts.height, MAX_CAPTURE_HEIGHT);
    const png = await page.screenshot({fullPage: true, clip: {x: 0, y: 0, width: viewport.width, height}});
    const problems = [...errors];
    if (facts.overflow) problems.push('горизонтальная прокрутка');
    return {status, png, height: facts.height, mainTop: facts.mainTop, problems, errors};
  } finally {
    await context.close();
  }
}

/** Decode both screenshots in the browser, diff them and draw JPEG comparisons. */
async function compare(workbench, before, after, viewport) {
  return workbench.evaluate(async ({a, b, width, viewportHeight, diffSource}) => {
    const diffPixels = new Function(`return (${diffSource})`)();
    const decode = async base64 => createImageBitmap(await (await fetch(`data:image/png;base64,${base64}`)).blob());
    const [imgA, imgB] = await Promise.all([decode(a), decode(b)]);
    const pixels = img => {
      const canvas = new OffscreenCanvas(img.width, img.height);
      const ctx = canvas.getContext('2d', {willReadFrequently: true});
      ctx.drawImage(img, 0, 0);
      return ctx.getImageData(0, 0, img.width, img.height).data;
    };
    const dataA = pixels(imgA), dataB = pixels(imgB);
    const diff = diffPixels(dataA, dataB, width, imgA.height, imgB.height);
    const toJpeg = async canvas => {
      const blob = await canvas.convertToBlob({type: 'image/jpeg', quality: 0.82});
      const bytes = new Uint8Array(await blob.arrayBuffer());
      let text = '';
      for (let i = 0; i < bytes.length; i += 0x8000) text += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
      return btoa(text);
    };
    const panels = async (sources, y0, h, maxWidth) => {
      const gap = 24, label = 28;
      const scale = Math.min(1, maxWidth / (sources.length * width + (sources.length - 1) * gap));
      const canvas = new OffscreenCanvas(Math.round((sources.length * width + (sources.length - 1) * gap) * scale), Math.round((h + label) * scale));
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.scale(scale, scale);
      sources.forEach(([title, draw], i) => {
        const x = i * (width + gap);
        ctx.fillStyle = '#222'; ctx.font = '600 18px sans-serif'; ctx.fillText(title, x + 4, 20);
        ctx.save(); ctx.beginPath(); ctx.rect(x, label, width, h); ctx.clip();
        ctx.fillStyle = '#eee'; ctx.fillRect(x, label, width, h);
        draw(ctx, x, label, y0, h);
        ctx.restore();
        ctx.strokeStyle = '#999'; ctx.strokeRect(x + 0.5, label + 0.5, width - 1, h - 1);
      });
      return toJpeg(canvas);
    };
    const blit = img => (ctx, x, top, y0, h) => ctx.drawImage(img, 0, y0, width, Math.max(0, Math.min(h, img.height - y0)), x, top, width, Math.max(0, Math.min(h, img.height - y0)));
    const firstScreen = await panels([['До', blit(imgA)], ['После', blit(imgB)]], 0, viewportHeight, 1600);
    let change = null;
    if (diff.box) {
      const y0 = Math.max(0, diff.box.y - 120);
      const h = Math.min(viewportHeight * 3, Math.max(imgA.height, imgB.height) - y0);
      const overlay = (ctx, x, top) => {
        const rows = Math.max(0, Math.min(h, imgB.height - y0));
        if (!rows) return;
        const out = new ImageData(width, rows);
        for (let y = 0; y < rows; y++) {
          for (let px = 0; px < width; px++) {
            const i = ((y0 + y) * width + px) * 4, o = (y * width + px) * 4;
            const inA = y0 + y < imgA.height;
            const changed = !inA || Math.abs(dataA[i] - dataB[i]) > 24 || Math.abs(dataA[i + 1] - dataB[i + 1]) > 24 || Math.abs(dataA[i + 2] - dataB[i + 2]) > 24;
            if (changed) { out.data[o] = 230; out.data[o + 1] = 20; out.data[o + 2] = 60; }
            else { const g = 255 - (255 - (dataB[i] + dataB[i + 1] + dataB[i + 2]) / 3) * 0.3; out.data[o] = out.data[o + 1] = out.data[o + 2] = g; }
            out.data[o + 3] = 255;
          }
        }
        const tmp = new OffscreenCanvas(width, rows);
        tmp.getContext('2d').putImageData(out, 0, 0);
        ctx.drawImage(tmp, x, top);
      };
      change = {y: y0, image: await panels([['До', blit(imgA)], ['После', blit(imgB)], ['Разница (красное)', overlay]], y0, h, 1800)};
    }
    return {diff, firstScreen, change};
  }, {a: before.png.toString('base64'), b: after.png.toString('base64'), width: viewport.width, viewportHeight: viewport.height, diffSource: lib.diffPixels.toString()});
}

function galleryHtml(results, summary) {
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const rows = results.map(r => `<section class="${r.status}"><h2>${{fail: '❌', warn: '⚠️', ok: '✅'}[r.status]} ${esc(r.title)} · ${r.width}px</h2>
<p>${esc(r.route)} · изменилось ${r.diff ? lib.percent(r.diff.ratio) : '—'} · главное: ${r.main ? `${r.main.before ?? '—'} → ${r.main.after ?? '—'} экрана` : '—'}${r.notes.length ? ' · ' + esc(r.notes.join('; ')) : ''}</p>
${r.files.firstScreen ? `<h3>Первый экран</h3><img loading="lazy" src="${r.files.firstScreen}" alt="">` : ''}
${r.files.change ? `<h3>Где изменилось (с ${r.change.y}px)</h3><img loading="lazy" src="${r.files.change}" alt="">` : ''}</section>`).join('\n');
  return `<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Визуальная проверка</title>
<style>body{font:15px/1.5 system-ui,sans-serif;margin:0 auto;max-width:1840px;padding:16px;background:#fafafa;color:#222}section{background:#fff;border:1px solid #ddd;border-left:6px solid #2e7d32;margin:16px 0;padding:8px 16px}section.fail{border-left-color:#c62828}section.warn{border-left-color:#ef8f00}img{max-width:100%;height:auto;border:1px solid #ccc}pre{white-space:pre-wrap;background:#fff;border:1px solid #ddd;padding:12px}</style>
<h1>Визуальная проверка</h1><pre>${esc(summary)}</pre>${rows}</html>`;
}

(async () => {
  await fs.rm(output, {recursive: true, force: true});
  await fs.mkdir(output, {recursive: true});
  const servers = [];
  let browser, exitCode = 0;
  const results = [];
  try {
    let beforeBase = process.env.VR_BEFORE_URL, afterBase = process.env.VR_AFTER_URL;
    if (!beforeBase || !afterBase) {
      const beforeDatabase = process.env.ATLAS_BEFORE_DATABASE_URL, afterDatabase = process.env.ATLAS_AFTER_DATABASE_URL;
      if (!beforeDatabase || !afterDatabase || beforeDatabase === afterDatabase) {
        throw Error('Set different ATLAS_BEFORE_DATABASE_URL and ATLAS_AFTER_DATABASE_URL for the two checkouts');
      }
      seedBrowserUser(process.env.ATLAS_BEFORE_DIR, beforeDatabase, {pending: true, teacher: true});
      seedBrowserUser(root, afterDatabase, {pending: true, teacher: true});
      servers.push(await serve(process.env.ATLAS_BEFORE_DIR, 8133, beforeDatabase));
      servers.push(await serve(root, 8134, afterDatabase));
      beforeBase = 'http://127.0.0.1:8133'; afterBase = 'http://127.0.0.1:8134';
    }
    browser = await chromium.launch({executablePath: process.env.ATLAS_BROWSER_EXECUTABLE || undefined});
    const states = {before: await learnerState(browser, beforeBase), after: await learnerState(browser, afterBase), beforePending: await learnerState(browser, beforeBase, {pending: true}), afterPending: await learnerState(browser, afterBase, {pending: true})};
    states.beforeTeacher = await learnerState(browser, beforeBase, {teacher: true});
    states.afterTeacher = await learnerState(browser, afterBase, {teacher: true});
    const workbench = await (await browser.newContext()).newPage();
    for (const viewport of config.viewports) {
      for (const pageSpec of pages) {
        const audience = pageSpec.audience || 'student';
        const before = await capture(browser, beforeBase, pageSpec.route, viewport, pageSpec.main, stateForAudience(states, audience, 'before'));
        const after = await capture(browser, afterBase, pageSpec.route, viewport, pageSpec.main, stateForAudience(states, audience, 'after'));
        const row = {name: pageSpec.name, title: pageSpec.title, route: pageSpec.route, width: viewport.width, status: 'ok', notes: [], files: {}};
        const fresh = lib.newProblems(before.problems || [], after.problems || []);
        const old = (after.problems || []).filter(p => !fresh.includes(p));
        if (after.status !== 200) { row.status = 'fail'; row.notes.push(`страница не открылась: HTTP ${after.status}`); }
        if (before.status !== 200 && after.status === 200) row.notes.push('новая страница');
        if (after.status === 200) {
          if (fresh.length) { row.status = 'fail'; row.notes.push(...fresh.map(p => `новое: ${p}`)); }
          if (old.length) { if (row.status === 'ok') row.status = 'warn'; row.notes.push(...old.map(p => `было и раньше: ${p}`)); }
          const verdict = lib.mainContentVerdict({before: before.status === 200 ? before.mainTop : null, after: after.mainTop, viewportHeight: viewport.height, maxScreens: viewport.maxScreens});
          if (verdict.status === 'fail') row.status = 'fail';
          else if (verdict.status === 'warn' && row.status === 'ok') row.status = 'warn';
          if (verdict.reason) row.notes.push(`главное ${verdict.reason}`);
          row.main = {before: lib.screensDown(before.mainTop, viewport.height), after: lib.screensDown(after.mainTop, viewport.height)};
          row.height = {before: before.height ?? null, after: after.height};
        }
        if (before.png && after.png) {
          const compared = await compare(workbench, before, after, viewport);
          row.diff = compared.diff;
          const stem = `${pageSpec.name}-${viewport.width}`;
          await fs.writeFile(path.join(output, `${stem}-first-screen.jpg`), Buffer.from(compared.firstScreen, 'base64'));
          row.files.firstScreen = `${stem}-first-screen.jpg`;
          if (compared.change) {
            await fs.writeFile(path.join(output, `${stem}-change.jpg`), Buffer.from(compared.change.image, 'base64'));
            row.files.change = `${stem}-change.jpg`;
            row.change = {y: compared.change.y};
          }
        }
        if (!before.png && after.png) {
          const stem = `${pageSpec.name}-${viewport.width}-after.png`;
          await fs.writeFile(path.join(output, stem), after.png);
          row.files.firstScreen = stem;
        }
        results.push(row);
        console.log(`${row.status.padEnd(4)} ${pageSpec.name} ${viewport.width}: ${row.diff ? lib.percent(row.diff.ratio) : '—'} ${row.notes.join('; ')}`);
      }
    }
    if (results.some(r => r.status === 'fail')) exitCode = 1;
  } catch (error) {
    exitCode = 1;
    results.push({name: 'review', title: 'Сама проверка', route: '', width: '—', status: 'fail', notes: [String(error && error.message || error).split('\n')[0]], files: {}});
    console.error(error);
  } finally {
    const runUrl = process.env.GITHUB_RUN_ID ? `${process.env.GITHUB_SERVER_URL}/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}` : '';
    const summary = lib.buildSummary(results, {runUrl});
    await fs.writeFile(path.join(output, 'summary.md'), summary);
    await fs.writeFile(path.join(output, 'report.json'), JSON.stringify(results.map(({files, ...r}) => ({...r, files})), null, 2));
    await fs.writeFile(path.join(output, 'index.html'), galleryHtml(results, summary));
    if (browser) await browser.close();
    servers.forEach(server => server.kill());
    process.exitCode = exitCode;
    if (exitCode) console.log('::error::Визуальная проверка: есть новые поломки — см. visual-review/summary.md');
  }
})();
