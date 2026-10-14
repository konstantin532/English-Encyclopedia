# SDD ledger — plan: docs/plans/2026-10-14-situation-weeks.md
Spec: docs/specs/2026-10-14-situation-weeks.md
Branch: situation-weeks (from 13333ef)
Pre-flight:
- T1→T2: SPHERES used as Week.sphere choices; global_week used by Week.global_number — consistent.
- T2→T3: loader uses WeekScene/TongueTwister fields — consistent.
- T3→T4: audit uses voices.yaml emotions/music_moods (T1) and roles — consistent.
- T3→T6: build_lines keys {i,speaker,kind,text,ru,name,emotion,emotion_ru}; T7 adds spoken — consistent.
- T5→T6: manifest per tempo keys music, music_gain_db → data-music-<tempo>, data-music-db-<tempo> — consistent.
- T5→T7: build_track gains spoken: bool param — T7 modifies T5 signature; ruling: add param with default False.
- T4→T9: story s01 music added in T4; T9 extends it — consistent.
Task 1: complete (commits 13333ef..0777ffa, tests: .venv/bin/python manage.py test tests → Destroying test database for alias 'default'...)
Task 2: complete (commits 0777ffa..a9d8eea, tests: .venv/bin/python manage.py test tests → Destroying test database for alias 'default'...)
Task 3: complete (commits a9d8eea..e7d828c, tests: .venv/bin/python manage.py test tests → Destroying test database for alias 'default'...)
Task 4: Ruling: пример урока совпадает с репликой целиком или с одним её предложением — в реплике бывает 2 предложения, а пример урока — одно — цена ошибки: правило чуть мягче спецификации
Task 4: complete (commits e7d828c..af840f5, tests: .venv/bin/python manage.py test tests → Destroying test database for alias 'default'...)
Task 5: Ruling: numpy добавлен в dev-группу pyproject без пересборки uv.lock (PyPI из облака недоступен); uv sync на компьютере автора и в CI пересоберёт lock сам — цена: lock в репозитории отстаёт до первого uv sync
Task 5: Ruling: файл музыки music_<темп>.mp3 вместо <темп>.music.mp3 из спецификации — with_suffix съедал «.music»; имя в духе voice_<темп> — цена: только имя файла
Task 5: complete (commits af840f5..32c11ac, tests: .venv/bin/python manage.py test tests → Destroying test database for alias 'default'...)
Task 6: note: заметил старое поведение — при переключении на «как в жизни» во время игры фон сцены включает громкость 100, но сам не запускается до следующего «Слушать»; в задачу не входит
Task 6: complete (commits 32c11ac..585dd1c, tests: .venv/bin/python manage.py test tests → Destroying test database for alias 'default'...)
Task 7: IN PROGRESS — tests/test_spoken.py написан, 6 тестов красные (ожидаемо). Дальше: Lesson.contractions + миграция, загрузчик, компонент (переключатель speech, line-spoken/line-full), JS ee-speech-mode, правила spoken в audit_weeks, contractions.html в уроке. Остановлено по просьбе автора (лимиты).
