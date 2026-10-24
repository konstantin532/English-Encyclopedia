"""Preparation-only checks. Never inherits a site database configuration.

Run from the repository root: .venv/bin/python docs/review-preparation/a1-01-04/run_baseline.py
All database commands explicitly use config.settings.test and a newly created
SQLite file outside the checkout. No production credentials are required.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "evidence" / "local"
OUT.mkdir(parents=True, exist_ok=True)
SANDBOX = Path(tempfile.mkdtemp(prefix="ee-preparation-test-"))
DB = SANDBOX / "baseline.sqlite3"
ENV = {k: v for k, v in os.environ.items() if k in {
    "PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "UV_CACHE_DIR", "UV_PYTHON_INSTALL_DIR",
}}
ENV.update({
    "DJANGO_SETTINGS_MODULE": "config.settings.test",
    "DATABASE_URL": "sqlite:///" + str(DB),
    "TEST_DATABASE_URL": "sqlite:///" + str(DB),
    "DJANGO_SECRET_KEY": "isolated-preparation-only-not-a-production-secret",
    "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1,testserver",
    "DJANGO_TEST_PROCESSES": "4",
    "PYTHONUNBUFFERED": "1",
})
REPORT = {
    "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "started_at_utc": datetime.now(timezone.utc).isoformat(),
    "database": {"engine": "sqlite", "path": str(DB), "fresh_directory": str(SANDBOX)},
    "environment_overrides": {k: v for k, v in ENV.items() if k.startswith("DJANGO_") and k != "DJANGO_SECRET_KEY"},
    "lockfiles_before": {}, "checks": [],
}
for path in ("uv.lock", "pnpm-lock.yaml"):
    REPORT["lockfiles_before"][path] = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def save():
    (OUT / "RESULTS.json").write_text(json.dumps(REPORT, ensure_ascii=False, indent=2) + "\n")


def run(name, args, timeout=1800):
    log = OUT / (name + ".log")
    entry = {"name": name, "argv": args, "started_at_utc": datetime.now(timezone.utc).isoformat(),
             "log": str(log.relative_to(OUT.parent.parent)), "status": "RUNNING"}
    REPORT["checks"].append(entry)
    save()
    start = time.monotonic()
    print("START", name, flush=True)
    try:
        with log.open("w") as stream:
            result = subprocess.run(args, cwd=ROOT, env=ENV, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
        entry.update(exit_code=result.returncode, status="PASS" if result.returncode == 0 else "FAIL")
    except (OSError, subprocess.TimeoutExpired) as error:
        entry.update(exit_code=None, status="BLOCKED", reason=str(error))
    entry["duration_seconds"] = round(time.monotonic() - start, 3)
    save()
    print("DONE", name, entry["status"], entry["duration_seconds"], flush=True)
    return entry["status"] == "PASS"


if __name__ == "__main__":
    save()
    run("uv-sync-frozen", ["uv", "sync", "--frozen"])
    run("pnpm-install-frozen", ["pnpm", "install", "--frozen-lockfile", "--ignore-scripts"])
    guard = "from django.conf import settings; import json; d=settings.DATABASES['default']; assert d['ENGINE']=='django.db.backends.sqlite3'; assert str(d['NAME'])==" + repr(str(DB)) + "; print(json.dumps(d)); print('ISOLATED SQLITE VERIFIED')"
    if not run("database-isolation", ["uv", "run", "--frozen", "python", "manage.py", "shell", "-c", guard]):
        raise SystemExit("Database isolation guard failed; no database commands executed")
    checks = [
        ("compileall", ["python", "-m", "compileall", "-q", "apps", "config", "tests"]),
        ("django-check", ["python", "manage.py", "check"]),
        ("collectstatic", ["python", "manage.py", "collectstatic", "--noinput", "--verbosity", "0"]),
        ("audio-readiness", ["python", "scripts/audio_readiness.py"]),
        ("cefr-evidence", ["python", "scripts/audit_cefr_evidence.py", "--strict"]),
        ("migration-drift", ["python", "manage.py", "makemigrations", "--check", "--dry-run"]),
        ("review-structure", ["python", "manage.py", "shell", "-c", "from apps.learning.mistake_review import question_bank,COUNT; from apps.drills.retry_guidance import PILOT_SLUGS; b=question_bank(); assert set(b)==set(PILOT_SLUGS); assert all(exercises and all(len(cards)==COUNT for cards in exercises.values()) for exercises in b.values()); print('A1 review structure OK:',len(b),'lessons')"]),
        ("understanding-structure", ["python", "manage.py", "shell", "-c", "from apps.learning.understanding import understanding_bank,SKILLS; from apps.drills.retry_guidance import PILOT_SLUGS; b=understanding_bank(); assert set(b)==set(PILOT_SLUGS); assert all(set(guide['tasks'])==set(SKILLS) for guide in b.values()); print('A1 understanding structure OK:',len(b),'guides')"]),
        ("migrate-isolated", ["python", "manage.py", "migrate", "--noinput", "-v", "1"]),
        ("load-content-isolated", ["python", "manage.py", "load_content"]),
        ("audit-course-isolated", ["python", "manage.py", "audit_course"]),
    ]
    for name, args in checks:
        run(name, ["uv", "run", "--frozen", *args])
    run("css", ["pnpm", "check:css"])
    run("javascript", ["pnpm", "test:ui"])
    run("django-full", ["uv", "run", "--frozen", "python", "manage.py", "test", "tests", "--parallel", "auto", "--noinput"])
    run("pytest-full", ["uv", "run", "--frozen", "pytest", "-q", "-rfE"])
    REPORT["lockfiles_after"] = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in REPORT["lockfiles_before"]}
    REPORT["lockfiles_unchanged"] = REPORT["lockfiles_before"] == REPORT["lockfiles_after"]
    REPORT["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    save()
