/* Real Chromium flow on a fresh disposable SQLite DB. Never uses the working DB.
 * ATLAS_PYTHON points to Python with project dependencies; Playwright is on NODE_PATH.
 * Evidence: atlas-browser-evidence/assignments-<unique id>/ (not committed).
 */
'use strict';
const assert = require('node:assert/strict');
const {spawn, spawnSync} = require('node:child_process');
const {randomUUID} = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');
const {chromium} = require('playwright');
const {seedBrowserUser, learnerState} = require('./browser_auth.cjs');
const root = path.resolve(__dirname, '..');
const output = path.join(root, 'atlas-browser-evidence', 'assignments-' + randomUUID());
const database = 'sqlite:///' + path.join(output, 'test.sqlite3').replaceAll('\\', '/');
const base = 'http://127.0.0.1:8144';
const env = {...process.env, DATABASE_URL: database, DJANGO_SETTINGS_MODULE: 'config.settings.local',
  EE_COURSE_LOGIN_REQUIRED: '1', PYTHONUTF8: '1'};
const python = process.env.ATLAS_PYTHON || 'python';
const report = {checks: [], screens: [], errors: []};

function manage(...args) {
  const result = spawnSync(python, ['manage.py', ...args], {cwd: root, env, encoding: 'utf8'});
  assert.equal(result.status, 0, result.stderr || result.error || 'Django command failed');
  return result.stdout;
}
async function ready(page, route) {
  const response = await page.goto(base + route, {waitUntil: 'networkidle'});
  assert.equal(response.status(), 200, route);
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  });
}
async function screenshot(page, name) {
  const facts = await page.evaluate(() => ({
    width: innerWidth, scrollWidth: document.documentElement.scrollWidth,
    headingTop: document.querySelector('h1').getBoundingClientRect().top + scrollY,
  }));
  await page.screenshot({path: path.join(output, name + '.png'), fullPage: false});
  report.screens.push({name, ...facts});
  assert.ok(facts.scrollWidth <= facts.width + 1, name + ': horizontal overflow');
}
async function submit(page, locator) {
  await locator.focus();
  await Promise.all([page.waitForNavigation({waitUntil: 'networkidle'}), page.keyboard.press('Enter')]);
}

(async () => {
  await fs.mkdir(output, {recursive: true});
  let server, browser;
  try {
    manage('migrate', '--noinput');
    manage('load_content');
    seedBrowserUser(root, database, {teacher: true});
    const fixture = manage('shell', '--command', [
      'import json',
      'from apps.accounts.models import User',
      'from apps.lessons.models import Lesson',
      'from apps.teaching.models import StudyGroup, GroupMembership',
      'teacher = User.objects.get(email="browser-teacher@example.test")',
      'student = User.objects.get(email="browser-student@example.test")',
      'group = StudyGroup.objects.create(teacher=teacher, name="Пробная группа")',
      'GroupMembership.objects.create(student=student, group=group)',
      'lesson = Lesson.objects.get(slug="a1-nouns-first-words")',
      'print("FIXTURE:" + json.dumps({"group": group.pk, "lesson": lesson.pk}))',
    ].join('\n'));
    const ids = JSON.parse(fixture.match(/FIXTURE:(.+)/)[1]);
    server = spawn(python, ['manage.py', 'runserver', '127.0.0.1:8144', '--noreload'],
      {cwd: root, env, stdio: ['ignore', 'ignore', 'pipe']});
    let serverError = '';
    server.stderr.on('data', chunk => { serverError += chunk; });
    const deadline = Date.now() + 45000;
    let available = false;
    while (Date.now() < deadline) {
      try {
        available = (await fetch(base, {signal: AbortSignal.timeout(1000)})).ok;
        if (available) break;
      } catch {}
      if (server.exitCode !== null) break;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    assert.ok(available, 'Disposable server did not start: ' + serverError);
    browser = await chromium.launch({executablePath: process.env.ATLAS_BROWSER_EXECUTABLE || undefined});
    const studentState = await learnerState(browser, base);
    const teacherState = await learnerState(browser, base, {teacher: true});
    const teacherContext = await browser.newContext({storageState: teacherState, viewport: {width: 390, height: 844}, reducedMotion: 'reduce'});
    const teacher = await teacherContext.newPage();
    const studentContext = await browser.newContext({storageState: studentState, viewport: {width: 390, height: 844}, reducedMotion: 'reduce'});
    const student = await studentContext.newPage();
    for (const page of [teacher, student]) page.on('pageerror', error => report.errors.push(error.message));
    const assignmentIds = [];
    for (const due of [new Date(Date.now() - 86400000).toLocaleDateString('en-CA', {timeZone: 'Europe/Moscow'}), '']) {
      await ready(teacher, '/teacher/assignments/new/');
      await teacher.locator('[name="group"]').selectOption(String(ids.group));
      await teacher.locator('[name="lesson"]').selectOption(String(ids.lesson));
      await teacher.locator('[name="due_date"]').fill(due);
      await submit(teacher, teacher.getByRole('button', {name: 'Назначить урок', exact: true}));
      assignmentIds.push(Number(new URL(teacher.url()).pathname.match(/assignments\/(\d+)/)[1]));
    }
    report.checks.push('Teacher assigns the same lesson twice, with and without a due date, using keyboard submission');
    await ready(student, '/learning/');
    assert.equal(await student.locator('[data-assignment]').count(), 2);
    const progressIds = await student.locator('[data-assignment]').evaluateAll(nodes => nodes.map(n => Number(n.dataset.assignment)));
    const newest = progressIds[0], oldest = progressIds[1];
    const cardsTop = await student.locator('#assignments-title').evaluate(el => el.getBoundingClientRect().top);
    assert.ok(cardsTop < 844 * 2, 'Assignments are below the second mobile screen');
    for (const width of [375, 390, 768, 1440]) {
      await student.setViewportSize({width, height: 844});
      await teacher.setViewportSize({width, height: 844});
      await ready(student, '/learning/');
      await screenshot(student, `student-${width}`);
      for (const [name, route] of [
        ['teacher', '/teacher/'], ['form', '/teacher/assignments/new/'],
        ['detail', `/teacher/assignments/${assignmentIds[0]}/`],
      ]) {
        await ready(teacher, route);
        await screenshot(teacher, `${name}-${width}`);
      }
    }
    await student.setViewportSize({width: 390, height: 844});
    await ready(student, '/learning/');
    assert.equal(await student.locator('html').getAttribute('data-motion'), 'minimal');
    const start = student.locator(`[data-assignment="${oldest}"]`).getByRole('button', {name: 'Начать', exact: true});
    await start.focus();
    await student.keyboard.press('Tab');
    assert.equal(await student.evaluate(() => document.activeElement.textContent.trim()), 'Я уже проходил этот урок');
    report.checks.push('Keyboard Tab reaches assignment actions and reduced motion remains minimal');
    await submit(student, start);
    assert.equal(new URL(student.url()).searchParams.get('assignment'), String(oldest));
    await student.locator('#lesson-extra-practice > summary').click();
    await student.getByRole('link', {name: 'Проверить себя самостоятельно →', exact: true}).click();
    await student.waitForLoadState('networkidle');
    for (const skill of ['meaning', 'writing', 'transfer', 'explain']) {
      await student.locator(`[name="answer_${skill}"]`).fill(skill === 'explain' ? 'Перед одним предметом ставлю артикль.' : 'This is my room.');
    }
    await student.locator('[name="assistance"][value="no_help"]').check();
    await submit(student, student.getByRole('button', {name: 'Отправить четыре ответа и открыть разбор'}));
    assert.equal(await student.locator('#batch-results-title').count(), 1);
    await ready(teacher, '/teacher/');
    await teacher.getByRole('link', {name: /Проверить эту работу: Применение|Проверить эту работу: Перенос/}).first().click();
    await teacher.waitForLoadState('networkidle');
    await teacher.locator('[name="teacher_verdict"]').selectOption('meets_task');
    for (const axis of ['meaning', 'form', 'context']) await teacher.locator(`[name="rubric_${axis}"]`).selectOption('yes');
    await teacher.locator('[name="teacher_note"]').fill('Вы хорошо передали смысл этой ситуации.');
    await submit(teacher, teacher.getByRole('button', {name: /Сохранить/}));
    await ready(student, `/lessons/a1-nouns-first-words/?assignment=${oldest}`);
    await student.locator('#lesson-complete').scrollIntoViewIfNeeded();
    await screenshot(student, 'lesson-completion-390');
    await submit(student, student.getByRole('button', {name: 'Отметить урок пройденным'}));
    await submit(student, student.locator(`[data-assignment="${newest}"]`).getByRole('button', {name: 'Я уже проходил этот урок'}));
    await ready(student, '/group/');
    await submit(student, student.locator('form[action="/group/leave/"] button'));
    await ready(student, `/assignments/${oldest}/history/`);
    assert.ok((await student.locator('main').innerText()).includes('Вы хорошо передали смысл этой ситуации.'));
    await screenshot(student, 'history-after-exit-390');
    await ready(teacher, '/teacher/');
    assert.equal(await teacher.locator('main a[href^="/teacher/review/"]').filter({hasText: 'Проверить эту работу'}).count(), 0);
    report.checks.push('Assigned batch, exact teacher review, both completion sources, exit, and preserved read-only feedback');
    assert.deepEqual(report.errors, []);
    console.log('Assignment browser acceptance: PASS; evidence: ' + output);
  } catch (error) {
    report.failure = error.stack;
    console.error(error.message);
    process.exitCode = 1;
  } finally {
    await fs.writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
    if (browser) await browser.close();
    if (server) server.kill();
  }
})();
