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

Task 7: Ruling: из-за запрета записи .git в F: работа идёт в независимой копии репозитория в папке Codex, на situation-weeks; main остаётся на 13333ef — цена: основная папка ещё не содержит новую ветку.
Task 7: Ruling: генератор и build_lines уже поддерживают spoken; генератор не менялся по прямому указанию автора — цена: нет.
Task 7: Ruling: uv sync не смог опросить интерпретатор в песочнице; окружение скопировано из установленного Python 3.13, numpy 2.5.4 взят из готового локального кэша; TEMP/TMP направлены в рабочую папку — цена: uv sync пока не подтверждён.
Task 7: Ruling: проверка браузера перенесена к общей проверке контента: отдельный сервер пока недоступен браузеру (тайм-аут соединения) — цена: визуальная проверка пока не выполнена.
Task 7: complete (tests: Python 3.13 manage.py test tests → 110/110, OK; test_spoken → RED 6 failures before implementation; миграция применена).
Task 8: Ruling: добавлен небольшой JS для трёх темпов скороговорки и выбор роли вынесен в свой раздел недели; это требуется интерфейсом, хотя JS не перечислен в Files этапа — цена: изменения общего плеера, покрыты общей проверкой.
Task 8: complete (tests: manage.py test tests → 117/117, OK; 7 новых проверок страницы и цели сначала RED; проверка браузера ожидает доступный сервер).
Task 9: Ruling: unit_words/known_vocabulary учитывают слова внутри phrase с недели её введения — спецификация разрешает вводить лексику внутри готовой фразы, а старый аудит знал только всю строку; проверка границы недель RED→GREEN — цена: слова фразы можно использовать отдельно с этой недели.
Task 9: Ruling: старые тестовые сцены и скороговорки изолированы от появившихся seed_weeks; ожидание поиска home изменено с 1 на 2 (новая фраза This is my home); исходные проверки сохранены — цена: нет изменения поведения сайта.
Task 9: complete (tests: manage.py test tests → 120/120, OK; количества и 3 проверки контента сначала RED; load_content → 54 единицы, 2 недели; audit_course → «Ошибок нет», нет предупреждений о неделях 1–2 и spoken; --all --engine test → 5 манифестов, тестовые файлы вынесены из static/audio в отчёт).
Task 10: Ruling: добавлен тест наличия обязательных инструкций в трёх документах, хотя этап плана не предусматривал тест для документации — прямое требование автора начинать каждый этап с падающей проверки — цена: названия терминов стали частью проверки.
Task 10: Ruling: вместо push в main из плана отправляется только situation-weeks; start.bat не предлагается как способ получить эту ветку — прямой запрет автора менять main — цена: ветку нужно открыть отдельно.
Task 10: implementation complete (tests: manage.py test tests → 121/121, OK; документация сначала RED 11 подстрок; load_content и audit_course → OK, «Ошибок нет»; makemigrations --check --dry-run → нет изменений; node --check audio-player.js → OK). Браузер и push пока не подтверждены; итоговая проверка продолжается.

Final: Ruling: замечание о неверных CSS-токенах повышено с Minor до Important: пояснение «полностью» не становилось мелким, нарушая интерфейс; замечание о Yes, I am. тоже Important: неверная подсказка провоцировала грамматическую ошибку — цена решения: 2 дополнительные регрессионные проверки.
Final: fixed русская транскрипция скороговорки — test_twister_has_russian_transcription_and_manual_override RED→GREEN; используется ru_ipa с ipa/ru вместо ru_tr, который читает ipa_us/ipa_ru у моделей.
Final: fixed урок без недели — test_level_accepts_lesson_without_week RED→GREEN; ссылка строится только при lesson.week.
Final: fixed конечный утвердительный be и CSS-токены — test_short_affirmative_answer_does_not_request_contraction и SpeechStyleTests RED→GREEN.
Final: Ruling: тест загрузчика изолирует BASE_DIR вместе с CONTENT_DIR, чтобы наличие реальной озвучки не ломало проверку отсутствующего манифеста — воспроизведённый FAIL после генерации, затем GREEN — цена: фикстура проверяет только свою папку.
Final: Ruling: на 390 px таблица «Как сокращают» показана парами с полноширинной заметкой; переключатели плеера переносятся — браузер выявил дробление слов и обрезанную подпись, после правки стало читаемо — цена: на телефоне иной вид таблицы, данные те же.
Final: review fixes verified — manage.py test tests → 125/125, OK; final load_content → 54 единицы, 2 сцены; audit_course → «Ошибок нет»; 13 CEFR unverified и старые опережающие сочетания остаются допустимыми предупреждениями.
Final: browser verified — пользователь запустил отдельный сервер 8003; главная, A1, недели 1/2/5, история 1 и урок be на компьютере (1280) и 390 px, без горизонтальной прокрутки; spoken сохраняется после reload, режимы слушания, выбор роли, natural, музыка/сохранение громкости работают; ошибок JS нет. Скриншоты и browser-checks.json сохранены вне репозитория.
Final: review declined-to-judge rulings — адаптивность проверена исполнителем в браузере; звучание Kokoro остаётся на прослушивание автором (TestEngine — тоны); старый генератор не менялся по указанию; полный набор 125/125 проверен исполнителем, повтор от ревьюера не нужен; uv sync остаётся неподтверждённым из-за запрета опроса Python в песочнице — цена: обычный запуск uv sync нужен вне песочницы.
Final: Ruling: обычный git push не проходит (DNS из node; в shell вход GitHub не может запустить credential-manager). Ветка публикуется через подключение GitHub отдельными коммитами с тем же содержимым и сообщениями, без main и без force — цена: SHA/авторство опубликованных коммитов отличаются от локальных.

2026-10-15: adversarial check поверх Claude d206c72 — 42 новых теста (214/214 OK), исправлены границы API/регистрации/redirect/повторения, аудит разметки и валидация YAML с откатом; load_content 106/8/1/1/4, audit_course «Ошибок нет». Проверены недели 1–5, история 1, A1, урок be: desktop и 390 px, без ошибок JS/переполнения. uv sync блокируется доступом к Python; используется установленный .venv. main/реестры не менялись. Подробности: docs/qa/2026-10-15-adversarial-check.md.

2026-10-15: audio recovery — обнаружены недокачанная ONNX-модель (135567440 вместо 325532387 байт) и тестовые тоны на сайте. generate_audio.bat проверяет размер/SHA256 и скачивает через .part; load_content исключает test-tone. Новые 8 тестов, всего 222/222 OK; audit_course «Ошибок нет». Настоящая генерация ожидает запуска пользователем: среда исполнителя не скачивает GitHub; сервер 8004 выключен. Подробности docs/qa/2026-10-15-audio-recovery.md.

2026-10-15: audio recovery confirmed — пользователь запустил восстановление; модель 325532387 байт, SHA256 совпал. 9 комплектов Kokoro (27 голосовых дорожек) созданы. В свежей вкладке 8004 воспроизведение недели 1 до конца (0:22), недели 3 до 0:15 и пауза; ошибок JS нет. verified=false до человеческой оценки произношения.

## 16.10 — ревизия дизайна

- Сверены файлы дизайна из рабочей копии Codex на компьютере: все совпадают с main (da29797), новых правок нет.
- Исправлено: на компьютере перевод реплики стоял в узкой колонке имени и растягивал строки — теперь под английской репликой; длинная подпись «Анна · рассказ · тревожно» наезжала на текст истории — теперь переносится.
- Перевод в примерах уроков всегда с новой строки (раньше тире оставалось в конце строки).
- Телефон 390 px: меню в одну строку с прокруткой, повторная «хлебная крошка» в шапке скрыта, «Шаги недели/урока» — строка кнопок вместо списка на весь экран.
- Выбор роли — поле 44 px. Ученику больше не показывается «generate_audio.bat»: вместо этого понятная подсказка.
- Проверено: audit_course без ошибок, 248 тестов, скриншоты 1280 и 390 px, горизонтальной прокрутки нет на 8 страницах.

## 16.10 — возвращён дизайн Codex «кинематографичная студия»

- Дизайн Codex (коммиты 394d91b и f24c346 в рабочей копии на компьютере) не попал на GitHub: копия была сброшена к origin/main («reset: moving to origin/main»). Коммиты восстановлены из pack-файла .git и перенесены поверх текущей ветки без конфликтов.
- Доработано: повторяющаяся обложка недели вынесена в components/week_hero.html; мобильное меню в одну строку согласовано с cinematic-studio.css; кнопки шагов из ревизии 16.10 не применяются к «Вашему маршруту»; JS-тест плеера добавлен в CI.
- Проверено: audit_course без ошибок, Django-тесты, JS 2/2, 9 страниц на 1280 и 390 px без горизонтальной прокрутки.

## 16.10 — неделя 5 A1 «Магазин у дома»

- Наполнена неделя 5: 10 реплик (76 слов), маркеры D1 и N6 (three dollars, two dollars), spoken у трёх реплик (That's, there's, It's), story_beat ведёт к истории 2 (кот Box пропадает).
- Новые единицы LX-00107…00123 (11 слов + 6 готовых фраз), cefr: unverified. there — T9 (пустое начало оборота), dollar — N6.
- Новая роль clerk «Продавщица», голос af_jessica убран из запасных.
- Уроки 9 «there is, there are и some» и 10 «How much is it? и цены в долларах»: 7 слоёв, 3 звуковые заметки, сокращения, 4 задания от узнавания до переноса.
- Скороговорка 5: There are three apples and three eggs (ð и θ).
- Проверено: load_content, audit_course без ошибок, 253 теста, неделя и уроки на 1280 и 390 px без горизонтальной прокрутки.

## 16.10 — неделя 6 A1 «Мой обычный день» и история 2

- Неделя 6: 10 реплик (77 слов) в кафе Мии на углу; маркеры D2 (work, have, drink) и N3 (at five/six/seven/ten); фразовый глагол get up размечен [D9]get[/] [X3]up[/]. Цепочка: неделя 5 «где Box?» → неделя 6 «в кафе каждое утро в семь бывает большой кот» → история 2.
- История 2 «The Café on the Corner»: 75 слов, знакомых 99%, одно новое слово corner (LX-00141). Box находится в кафе у Мии, пропадает и сам возвращается домой — локальная развязка без страшилок.
- Новые единицы LX-00124…00140 (11 слов + 6 фраз), cefr: unverified. cafe пишется без акцента: токенизатор аудита не принимает é.
- Уроки 11 «I get up, you work — настоящее простое» (do-вопросы, don't, фразовый глагол) и 12 «at seven, seven o'clock, What time…?».
- Скороговорка 6: I work, you work, every day (w и r).
- Проверено: audit_course без ошибок и без предупреждений по новым материалам, 257 тестов, страницы недели 6, истории 2 и уроков на 1280 и 390 px без горизонтальной прокрутки.
