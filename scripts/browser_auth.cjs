/* Real form login for isolated browser fixtures. Never disable the course wall. */
'use strict';
const assert = require('node:assert/strict');
const {spawnSync} = require('node:child_process');
const {randomUUID} = require('node:crypto');

function credentials() {
  const email = process.env.EE_BROWSER_USER_EMAIL || 'browser-student@example.test';
  const password = process.env.EE_BROWSER_USER_PASSWORD;
  assert.ok(password, 'Set EE_BROWSER_USER_PASSWORD for an existing local browser fixture');
  return {email, password};
}

/** Automatic harnesses already own migrated disposable SQLite databases.
 * Only an explicitly supplied SQLite URL may be seeded; remote databases are rejected.
 * No staff/superuser or real accounts are created or changed. */
function seedBrowserUser(directory, databaseUrl, {pending = false} = {}) {
  assert.ok(databaseUrl && databaseUrl.startsWith('sqlite:///'), 'Browser fixtures require an explicit disposable SQLite DATABASE_URL');
  process.env.EE_BROWSER_USER_PASSWORD ||= randomUUID();
  const {email, password} = credentials();
  const code = [
    'import os',
    'from django.contrib.auth import get_user_model',
    'User = get_user_model()',
    'email = os.environ["EE_BROWSER_USER_EMAIL"]',
    'assert email.endswith("@example.test"), "Browser fixtures must use a reserved example.test address"',
    'user, created = User.objects.get_or_create(email=email)',
    'assert not (user.is_staff or user.is_superuser or user.is_teacher), "Refusing to change a privileged account"',
    'user.display_name = "Ученик"',
    'user.markers_enabled = False',
    'user.set_password(os.environ["EE_BROWSER_USER_PASSWORD"])',
    'user.save()',
    ...(pending ? [
      'pending, created = User.objects.get_or_create(email="browser-pending@example.test")',
      'assert not (pending.is_staff or pending.is_superuser or pending.is_teacher)',
      'pending.teacher_access_requested = True',
      'pending.set_password(os.environ["EE_BROWSER_USER_PASSWORD"])',
      'pending.save()',
    ] : []),
  ].join('\n');
  const result = spawnSync(process.env.ATLAS_PYTHON || 'python', ['manage.py', 'shell', '--command', code],
    {cwd: directory, env: {...process.env, DATABASE_URL: databaseUrl, DJANGO_SETTINGS_MODULE: 'config.settings.local',
      EE_BROWSER_USER_EMAIL: email, EE_BROWSER_USER_PASSWORD: password, PYTHONUTF8: '1'}, encoding: 'utf8'});
  assert.equal(result.status, 0, 'Could not seed disposable browser user: ' + (result.stderr || result.error || ''));
}

async function learnerState(browser, base, {pending = false} = {}) {
  const {email, password} = credentials();
  const context = await browser.newContext({reducedMotion: 'reduce'});
  try {
    const page = await context.newPage();
    await page.goto(base + '/accounts/login/?next=/learning/', {waitUntil: 'networkidle'});
    await page.locator('[name="username"]').fill(pending ? 'browser-pending@example.test' : email);
    await page.locator('[name="password"]').fill(password);
    await Promise.all([
      page.waitForURL(url => url.pathname === '/learning/'),
      page.locator('form button[type="submit"]').filter({hasText: 'Войти'}).click(),
    ]);
    assert.equal(new URL(page.url()).pathname, '/learning/', 'Browser fixture was redirected away from its course');
    assert.equal(await page.locator('form[action="/accounts/logout/"]').count(), 1, 'Browser fixture is not logged in');
    return await context.storageState();
  } finally { await context.close(); }
}
function stateForAudience(states, audience, side) {
  assert.ok(side === 'before' || side === 'after', 'Unknown visual-review side');
  if (audience === 'guest') return undefined;
  assert.ok(audience === 'student' || audience === 'pending', 'Unknown visual-review audience');
  const state = states[side + (audience === 'pending' ? 'Pending' : '')];
  assert.ok(state, 'Missing role session for ' + side + '/' + audience);
  return state;
}
module.exports = {seedBrowserUser, learnerState, stateForAudience};
