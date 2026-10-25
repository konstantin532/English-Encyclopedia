# New checks (2026-10-25)

Interpreter P=/workspace/scratch/6babac9ddb0c/English-Encyclopedia/.venv/bin/python; existing root lockfile environment reused without version updates.
All management/test commands prefix DATABASE_URL=sqlite:////tmp/ee1720-isolated.sqlite3 TEST_DATABASE_URL=sqlite:////tmp/ee1720-isolated.sqlite3 DJANGO_SETTINGS_MODULE=config.settings.test. Baseline uses analogous /tmp/ee1720-before-isolated.sqlite3, cwd /tmp/ee1720-before. Never production DB.

- PYTHONPATH=. $P /tmp/ee1720-db-guard.py: PASS, exact SQLite local name asserted.
- $P manage.py migrate --noinput: PASS, /tmp/ee1720-migrate.log.
- $P manage.py load_content: PASS,1047units/60lessons/11stories/7poems/30dialogueweeks; /tmp/ee1720-load.log.
- $P manage.py audit_course: PASS no errors, existing global warnings (shortage5–8 readyphrases acrosslevels, storylengths, A1→A1+ recycling, best/view/york). /tmp/ee1720-audit.log.
- $P manage.py test tests.test_a1_deep_17_20 --noinput on clean base5826785: expected RED,5tests/13failing subtests, /tmp/ee1720-before-final.log. Tracked baseline clean.
- SAME frozen tests/test_a1_deep_17_20.py SHA256 26a74de9cfd8268cc17667f7263444fedb1cfb9e7cf723e30cfc59eaa1cfd2fd on both base and changed tree. Do not use older draft logs.
- $P manage.py test tests.test_a1_deep_17_20 tests.test_a1_editorial_week09_10 tests.test_a1_scaffold_variants --noinput: PASS38tests, /tmp/ee1720-after.log. Signed-in API behavior verifies actual UnitProgress recipients; accepted and wrongmeaning/owner/polarity/order answers exercised. HTML client verifies4published pages and7layers, Anna role prompt consistency.
- $P /tmp/ee1720_ledger.py: PASS YAML/JSON parse+stable lesson/exercise identities/order/kind/stage and seven layers; produces complete semantic ledger.
- git diff --check: PASS.
- $P scripts/audio_readiness.py: diagnostic runs; expected33,files_present0. Listening BLOCKED missing actualaudio; strict production readiness wouldfail. Not a pronunciation PASS.
- Full suite/Postgres/CI/browser desktop+390px: parent owns integration; BLOCKED/unrun within assigned subtask, do not claim PASS.

No historic Actions logs used as new-run evidence. No tests or expected keys weakened to green; draft test-data mistakes documented in NOTES. Full suite deliberately excluded under parent instruction.
