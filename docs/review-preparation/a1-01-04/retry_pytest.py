"""A separate bounded full-pytest invocation after a host process disappeared.

Preserves the interrupted log and unknown exit status. Reuses ONLY the explicitly
isolated SQLite fixture recorded by run_baseline.py. No source edits.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / 'evidence/local'
report_path = OUT / 'RESULTS.json'
report = json.loads(report_path.read_text())
db = Path(report['database']['path']).resolve(strict=True)
assert db.parent.name.startswith('ee-preparation-test-') and db.name == 'baseline.sqlite3'
assert (db.parent / 'REVIEW_DATABASE_ONLY').read_text().strip() == report['source_commit']
prior = report['checks'][-1]
assert prior['name'] == 'pytest-full' and prior['status'] == 'RUNNING'
prior['status'] = 'BLOCKED'
prior['exit_code'] = None
prior['reason'] = 'Process disappeared before an exit result or final pytest summary; cause not established. Partial log preserved, not PASS and not a demonstrated test failure.'
prior['last_log_modified_utc'] = datetime.fromtimestamp((OUT / 'pytest-full.log').stat().st_mtime, timezone.utc).isoformat()
env = {k:v for k,v in os.environ.items() if k in {'PATH','HOME','LANG','TMPDIR','UV_CACHE_DIR','UV_PYTHON_INSTALL_DIR'}}
env.update(DJANGO_SETTINGS_MODULE='config.settings.test', DATABASE_URL='sqlite:///' + str(db), TEST_DATABASE_URL='sqlite:///' + str(db), DJANGO_ALLOWED_HOSTS='localhost,127.0.0.1,testserver', PYTHONUNBUFFERED='1')
cmd = ['uv', 'run', '--frozen', 'pytest', '-q', '-rfE']
entry = {'name':'pytest-full-retry','argv':cmd,'started_at_utc':datetime.now(timezone.utc).isoformat(),
         'log':'evidence/local/pytest-full-retry.log','status':'RUNNING','reason_for_retry':prior['reason']}
report['checks'].append(entry)
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print('Separate full pytest retry started; original interrupted log preserved', flush=True)
start = time.monotonic()
try:
    with (OUT / 'pytest-full-retry.log').open('w') as stream:
        result = subprocess.run(cmd,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=1800)
    entry.update(exit_code=result.returncode,status='PASS' if result.returncode==0 else 'FAIL')
except (OSError, subprocess.TimeoutExpired) as error:
    entry.update(exit_code=None,status='BLOCKED',reason=str(error))
entry['duration_seconds'] = round(time.monotonic()-start,3)
report['lockfiles_after'] = {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in report['lockfiles_before']}
report['lockfiles_unchanged'] = report['lockfiles_before'] == report['lockfiles_after']
report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print(entry['status'],entry.get('exit_code'),entry['duration_seconds'],flush=True)
