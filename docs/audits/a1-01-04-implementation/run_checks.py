"""Reproduce checks with locked packages and a fresh, explicitly isolated SQLite.

Run from the full repository checkout. This never reads production DB settings.
Logs go to --output; the isolated database lives in a fresh temporary directory.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--pytest", action="store_true", help="Also run the complete CI pytest suite")
args = parser.parse_args()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=True)
fixture = Path(tempfile.mkdtemp(prefix="ee-a1-editorial-test-")) / "fixture.sqlite3"
env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "LANG", "LC_ALL", "UV_CACHE_DIR", "UV_PYTHON_INSTALL_DIR")}
env.update(DJANGO_SETTINGS_MODULE="config.settings.test", DATABASE_URL="sqlite:///" + str(fixture),
           TEST_DATABASE_URL="sqlite:///" + str(fixture), DJANGO_SECRET_KEY="isolated-editorial-tests-only",
           DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,testserver", DJANGO_TEST_PROCESSES="4", PYTHONUNBUFFERED="1")
manage = ["uv", "run", "--frozen", "python", "manage.py"]
commands = [
    ("guard", [*manage, "shell", "-c", "from django.conf import settings; d=settings.DATABASES['default']; "
               f"assert d['ENGINE']=='django.db.backends.sqlite3' and d['NAME']=={str(fixture)!r}; print(d['ENGINE'],d['NAME'])"]),
    ("sync", ["uv", "sync", "--frozen"]),
    ("node-install", ["pnpm", "install", "--frozen-lockfile", "--ignore-scripts"]),
    ("compile", ["uv", "run", "--frozen", "python", "-m", "compileall", "-q", "apps", "config", "tests"]),
    ("check", [*manage, "check"]),
    ("static", [*manage, "collectstatic", "--noinput", "--verbosity", "0"]),
    ("migration-check", [*manage, "makemigrations", "--check", "--dry-run"]),
    ("migrate", [*manage, "migrate", "--noinput", "-v0"]),
    ("load", [*manage, "load_content"]), ("audit", [*manage, "audit_course"]),
    ("targeted", [*manage, "test", "tests.test_a1_editorial_01_04", "tests.test_a1_editorial_history",
                  "tests.test_a1_translation", "tests.test_progress_safety", "tests.test_a1_microsteps", "--noinput"]),
    ("css", ["pnpm", "check:css"]), ("js", ["pnpm", "test:ui"]),
    ("audio-diagnostic", ["uv", "run", "--frozen", "python", "scripts/audio_readiness.py"]),
    ("cefr-diagnostic", ["uv", "run", "--frozen", "python", "scripts/audit_cefr_evidence.py", "--strict"]),
    ("django-full", [*manage, "test", "tests", "--parallel", "auto", "--noinput"]),
]
if args.pytest:
    commands.append(("pytest-full", ["uv", "run", "--frozen", "pytest", "-q", "-rfE"]))
rows = []
for name, cmd in commands:
    start = time.monotonic()
    with (out / (name + ".log")).open("w") as log:
        result = subprocess.run(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    rows.append({"name": name, "command": cmd, "exit_code": result.returncode,
                 "seconds": round(time.monotonic() - start, 3), "status": "PASS" if result.returncode == 0 else "FAIL"})
    (out / "RESULTS.json").write_text(json.dumps({"database": str(fixture), "checks": rows}, indent=2) + "\n")
    print(name, result.returncode, flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)
