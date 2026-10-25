# EX113 incremental correction

Current source before correction: EX113.units=[LX-00203 music], accepted music AND guitar replies. `apps/learning/services.py:record_attempt` updates every statically attached unit for any accepted answer; it does not inspect which alternative matched. Therefore canonical-only lexical targets are unsafe when alternate replies omit them.

Minimal correction: EX113.units=[LX-00034 like]. Each accepted answer contains that verb in its existing “enjoy/find pleasant” meaning, introduced week2. All existing canonical/accepted answers preserved; no global logic, normalization, UID, schema, or other lessons changed. No new sense/word introduced.

Frozen test test_hobby_alternatives_credit_only_their_shared_skill submits all eight stored answer variants through the real signed-in exercise API and inspects actual UnitProgress target set. It separately rejects missing preference, wrong agreement, negative preference and wrong speaker. Before correction: /tmp/ee1720-ex113-before.log (8 subtest failures). After correction: /tmp/ee1720-ex113-after.log. Full frozen module SHA256 9222aafefadb94feeaf7d41d5b39189289b92046cb724e94979a3147b3f984f1 unchanged between these runs.

Command prefix: DATABASE_URL=sqlite:////tmp/ee1720-isolated.sqlite3 TEST_DATABASE_URL=sqlite:////tmp/ee1720-isolated.sqlite3 DJANGO_SETTINGS_MODULE=config.settings.test. Interpreter /workspace/scratch/6babac9ddb0c/English-Encyclopedia/.venv/bin/python, cwd /tmp/ee-a1-17-20. BEFORE manage.py test tests.test_a1_deep_17_20.A1DeepSeventeenTwentyTests.test_hobby_alternatives_credit_only_their_shared_skill --noinput; AFTER manage.py test tests.test_a1_deep_17_20 --noinput. Same explicit guarded test SQLite setup as original packet.

Apply only /tmp/ee1720-ex113-incremental.patch on top of original /tmp/ee1720.patch. Original packet ledger remains a snapshot of the first delivered patch; this note records the subsequent source change.
