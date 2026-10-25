"""Locked verification in a new SQLite fixture; never uses the site's database."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--full-pytest', action='store_true')
args = parser.parse_args()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=True)
fixture = Path(tempfile.mkdtemp(prefix='ee-a1-05-08-verification-')) / 'fixture.sqlite3'
env = {k: v for k, v in os.environ.items() if k in ('PATH', 'HOME', 'LANG', 'LC_ALL', 'UV_CACHE_DIR', 'UV_PYTHON_INSTALL_DIR')}
env.update(DJANGO_SETTINGS_MODULE='config.settings.test', DATABASE_URL='sqlite:///' + str(fixture),
           TEST_DATABASE_URL='sqlite:///' + str(fixture), DJANGO_SECRET_KEY='isolated-a1-05-08-checks-only',
           DJANGO_ALLOWED_HOSTS='localhost,127.0.0.1,testserver', DJANGO_TEST_PROCESSES='4', PYTHONUNBUFFERED='1')
(out / 'DATABASE.json').write_text(json.dumps({'database': str(fixture), 'settings': env['DJANGO_SETTINGS_MODULE']}, indent=2) + '\n')
manage = ['uv', 'run', '--frozen', 'python', 'manage.py']
commands = [
    ('database-guard', [*manage, 'shell', '-c', "from django.conf import settings; d=settings.DATABASES['default']; "
                       f"assert d['ENGINE']=='django.db.backends.sqlite3' and d['NAME']=={str(fixture)!r}; print(d['ENGINE'],d['NAME'])"]),
    ('uv-sync', ['uv', 'sync', '--frozen']),
    ('pnpm-install', ['pnpm', 'install', '--frozen-lockfile', '--ignore-scripts']),
    ('compileall', ['uv', 'run', '--frozen', 'python', '-m', 'compileall', '-q', 'apps', 'config', 'tests']),
    ('check', [*manage, 'check']),
    ('collectstatic', [*manage, 'collectstatic', '--noinput', '--verbosity', '0']),
    ('makemigrations', [*manage, 'makemigrations', '--check', '--dry-run']),
    ('migrate', [*manage, 'migrate', '--noinput', '-v0']),
    ('load-content', [*manage, 'load_content']),
    ('audit-course', [*manage, 'audit_course']),
    ('targeted', [*manage, 'test', 'tests.test_a1_editorial_deep_05_08', 'tests.test_a1_deep_05_08_support', '--noinput']),
    ('review-contracts', [*manage, 'shell', '-c', "from apps.learning.mistake_review import question_bank,COUNT; from apps.learning.understanding import understanding_bank,SKILLS; from apps.drills.retry_guidance import PILOT_SLUGS; b=question_bank(); assert set(b)==set(PILOT_SLUGS); assert all(all(len(c)==COUNT for c in e.values()) for e in b.values()); u=understanding_bank(); assert set(u)==set(PILOT_SLUGS); assert all(set(g['tasks'])==set(SKILLS) for g in u.values()); print(len(b),len(u))"]),
    ('css', ['pnpm', 'check:css']), ('js', ['pnpm', 'test:ui']),
    ('audio-readiness', ['uv', 'run', '--frozen', 'python', 'scripts/audio_readiness.py']),
    ('cefr', ['uv', 'run', '--frozen', 'python', 'scripts/audit_cefr_evidence.py', '--strict']),
    ('fuzz', ['uv', 'run', '--frozen', 'python', 'scripts/qa_evolution.py', 'fuzz', '--run-number', '0', '--seed', '20261025']),
    ('mutation', ['uv', 'run', '--frozen', 'python', 'scripts/qa_mutation_probe.py', '--report', str(out / 'mutation-report.md')]),
    ('django-full', [*manage, 'test', 'tests', '--parallel', 'auto', '--noinput']),
]
if args.full_pytest:
    commands.append(('pytest-full', ['uv', 'run', '--frozen', 'pytest', '-q', '-rfE']))
results = []
for name, cmd in commands:
    print('START', name, flush=True)
    start = time.monotonic()
    with (out / (name + '.log')).open('w') as log:
        result = subprocess.run(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    row = {'name': name, 'command': cmd, 'exit_code': result.returncode,
           'seconds': round(time.monotonic() - start, 3), 'status': 'PASS' if result.returncode == 0 else 'FAIL'}
    results.append(row)
    (out / 'RESULTS.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    print(name, result.returncode, flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)
