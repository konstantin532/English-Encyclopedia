# A1: сокращения по отчёту естественности

Дата: 2026-10-29. База `main@c55d23745a91a0b66cb9e2889e29574cb4df207f`, ветка `fix/a1-natural-contractions-20261029`.

Из 192 строк A1 типа «Сокращение по правилу курса» применены 190 в 67 файлах контента. Это число строк исходного отчёта, а не число отдельных апострофов. Формулировки, A1+, стабильные ID, словарные lemma/forms и объяснения устройства фразы сохранены.

- #112: незавершённый шаблон `Excuse me, where is…?` сохранён полностью.
- #167: `twister.target_line: I do not have a stamp.` сохранён как точная ссылка на письменный text; spoken уже содержит сокращение.
- #139: финальное `No, it does not.` сохранено, сокращено только последующее `I cannot sleep.`.
- #113: полный text первой реплики недели 8 сохранён; добавлен размеченный spoken с `Where’s`.
- Who’s this? в sound_notes сопровождается соответствующим IPA `/ˈhuz ˈðɪs/`.

Для проверяемых ответов сохранены обе формы. Четырём Exercise добавлены полные accepted; ещё четыре уже имели их. Новые API-тесты защищают все 8 изменённых ключей, 19 переводов и 2 письменные проверки, а JS-тесты — диктант, обратный перевод и четыре комбинации I’m/I am + can’t/cannot в теме 22. Два вызова JS теперь передают локальный список retrieval_alternatives; общая нормализация и A1+ не менялись. Индексы верных вариантов и отсутствие одинаково верных дублей проверены отдельно.

## Проверки

Окружение: Windows, Python 3.13, Django 5.2, test settings, отдельная SQLite; рабочая база не использовалась. `UV_NO_SYNC=1`, `PYTHONUTF8=1`, `TEST_DATABASE_URL=''`. Для полного прогона `EE_PHRASE_MEMORY_ENABLED=false` (штатное значение): локальный dotenv включал необязательный модуль и ломал два старых теста disabled; при явном false оба проходят. Код модуля не менялся.

| Команда | Результат |
|---|---|
| `uv run python manage.py test tests.test_a1_contraction_answers tests.test_grammar_answer_integrity tests.test_a1_active_studio tests.test_a1_scaffold_variants tests.test_a1_independent_understanding tests.test_audit_weeks --exclude-tag slow --parallel 4 --verbosity 1` | 86 PASS |
| `uv run python manage.py test tests.test_a1_corpus_alignment tests.test_a1_second_pass --parallel auto` | 13 PASS |
| `node --test tests/js/a1-active.test.cjs tests/js/a1-active-browser.test.cjs` | 34 PASS |
| `pnpm test:ui` | 187 PASS |
| `pnpm check:css` | 22 таблицы стилей PASS |
| `load_content` и `audit_course` через `manage.py shell`: migrate → load_content → audit_course в SQLite в памяти | PASS: 1047 единиц, 60 уроков, 11 историй, 7 стихов, 30 недель; ошибок нет |
| `uv run python manage.py test tests --parallel auto --verbosity 1`, 8 процессов | 1166 тестов, OK (skipped=8), 271.956 с |
| `git diff --check` | PASS |

До исправления: новый Python-тест воспроизвёл отклонение “That’s expensive!”; два JS-теста — отклонение сокращённого диктанта и смешанной полной/сокращённой формы ответа. После исправления целевые проверки проходят. Первый полный прогон: 1164 теста, 13 failures (10 буквальных сравнений lemma/example, 1 старый ожидаемый ключ, 2 ошибки локального флага), 8 skipped. Контракт словаря теперь распознаёт сокращения только у фраз через существующую функцию; для всех 10 добавлены контрпробы на замену слов и потерю отрицания. Обычные слова и объявленные forms проверяются как прежде; исключений по ID нет.

Браузер: реальные формы A1-22 приняли `I am tired. I feel sick.` и `I'm tired. I feel sick.` в диктанте и обратном переводе; оба варианта с `not` отклонены. На 1440×1000 и 390×844 горизонтального переполнения нет. На 390 px основное содержание начинается на первом экране. У недели 8 проверены все 6 сочетаний «без текста / с текстом / с разметкой» × «как говорят / как написано»: hidden скрывает ответ, spoken показывает Where’s, written — Where is. Соседние элементы по локальным снимкам не смещены; отдельного локального снимка до изменений нет, сравнение до/после остаётся за CI Visual review. В консоли единственная ошибка — существующий 404 favicon.ico; ошибок JS приложения нет. Прослушивание настоящего аудио и ручная проверка произношения не выполнялись.

Две независимые проверки: границы изменений/исходники и ключи/обработчики. 77 источников A1+ побайтно совпадают с baseline; все изменённые строки равнозначны после раскрытия сокращений. На реальных моделях/API/индексах выбора — 337 проверок; на JS-обработчиках серверных данных — 23. Замечаний P1/P2 не найдено. Это не заменяет рецензию Claude.

## Изменения текста озвучки

### Реплика, которую нужно переозвучить

Неделя A1-08, первая реплика Тома, только темп **natural**:

- Было: “Excuse me! I have an old key. Where is the key shop, please?”
- Стало: “Excuse me! I have an old key. Where’s the key shop, please?”
- Источник: `content/seed_weeks/a1_w08.yaml`, новое `script[0].spoken`. Полный `text` сохранён.
- Пересоздать `static/audio/weeks/a1-w08/voice_natural.mp3`, тайминги natural и `manifest.json`. Слова slow/very_slow не менялись; штатный генератор при запуске всё равно создаёт все три темпа.
- **PENDING:** аудио не перегенерировано и не прослушано. Старый файл пока говорит Where is. Текущий загрузчик недель не сравнивает script fingerprint, поэтому автоматически это несовпадение не отключит. Подпись манифеста не подменялась.

### Системная озвучка в браузере

Ещё 16 полей читаются Web Speech API при нажатии кнопки. Их текст изменится сразу из JSON; записанных MP3 для них нет, отдельная перезапись не нужна. Строки — исходные из отчёта.

| Файл:строка | Было | Стало |
|---|---|---|
| `content/active_a1/scenarios_07_12.json:10` | Who is this? | Who's this? |
| `content/active_a1/topics_01_08.json:269` | Who is this? | Who's this? |
| `content/active_a1/scenarios_13_18.json:136` | Where is the bank? | Where's the bank? |
| `content/active_a1/scenarios_13_18.json:223` | Excuse me. Where is the bank? | Excuse me. Where's the bank? |
| `content/active_a1/topics_14_18.json:60` | Where is the key shop? | Where's the key shop? |
| `content/active_a1/topics_14_18.json:108` | Excuse me. Where is the bank? | Excuse me. Where's the bank? |
| `content/active_a1/scenarios_21_22.json:89` | I am hungry. | I'm hungry. |
| `content/active_a1/scenarios_21_22.json:113` | I am tired. I can sit, but I can't sleep. | I'm tired. I can sit, but I can't sleep. |
| `content/active_a1/scenarios_21_22.json:120` | I am well. | I'm well. |
| `content/active_a1/scenarios_21_22.json:124` | I can sleep, but I am thirsty. | I can sleep, but I'm thirsty. |
| `content/active_a1/topics_21_22.json:63` | I am tired. I feel sick. | I'm tired. I feel sick. |
| `content/active_a1/topics_21_22.json:86` | I am tired and I can't sleep. | I'm tired and I can't sleep. |
| `content/active_a1/topics_23_24.json:65` | What is your last name? | What's your last name? |
| `content/active_a1/scenarios_27_28.json:18` | Excuse me, where is the train station? | Excuse me, where's the train station? |
| `content/active_a1/scenarios_27_28.json:120` | It is cloudy, but it is warm. | It's cloudy, but it's warm. |
| `content/active_a1/topics_27_28.json:68` | It is windy today. | It's windy today. |

Сценарии историй s04/s05 и текст скороговорки t012 не менялись: изменены только текстовые упражнения, phrase_hunt и warmup. Для них переозвучка не требуется.
## Ограничения и приёмка

- **PENDING:** переозвучка natural недели 8 и человеческое прослушивание. Старое аудио может расходиться с новым spoken, пока пакет не пересоздан.
- **PENDING:** независимая рецензия Claude и удалённый CI/Visual review на точном head PR.
- Существующие предупреждения курса: CEFR ещё не подтверждён, повторение A1 в A1+ 44% при цели 70%, несколько опережающих словосочетаний. Эта задача их не исправляет.
- Изменение обратимо обычным revert; модели/миграции/авторизация/production не затронуты. Контент появится после штатного load_content. PR не даёт разрешения на merge или deployment.

| Область | Статус и основание |
|---|---|
| Correctness / Integration | PASS локальных целевых проверок и полного прогона |
| Regression | PASS локальных целевых проверок и полного прогона |
| Data Integrity | PASS: ID, lemma/forms и A1+ сохранены; рабочая база не изменялась |
| UX | PASS локальных размеров/режимов/ввода; CI Visual review ожидается |
| Security | N/A: аутентификация, права и хранение данных не менялись |
| Evidence | PASS локальных журналов; Claude и CI pending |
