# Runtime-связи A1 1–4 — подготовка, не редакторское заключение

Источник: `konstantin532/English-Encyclopedia`, commit `8d3a41d9aa61cbf074caff602d53b22920ca3efa`.
Пути и номера строк ниже относятся именно к этому снимку. Полные оригиналы исходников находятся в `snapshot/` и сверяются по `SOURCE_MANIFEST.json`; извлечённые записи не заменяют оригиналы.
Статус содержательной рецензии всех четырёх уроков: **NOT_REVIEWED**. Наличие связи, полных исходников или рабочего API не доказывает правильность грамматики.

## 1. Какие материалы действительно показываются в уроке

`config/urls.py` включает `apps.lessons.urls` с префиксом `lessons/`; `apps/lessons/urls.py` задаёт `<slug:slug>/`.
`apps/lessons/views.py:11–32` (`lesson_detail`) выбирает только `is_published=True`, передаёт `lesson.layers`, `lesson.units`, `lesson.exercises`, `lesson.practice_items`, `get_guide(slug)` и шесть дополнительных миссий из `active_topics()[lesson.order]`, если совпадает slug.

| A1 order | Slug и фактический маршрут из URLconf | Слои в YAML | Основные упражнения | Переводы |
|---|---|---:|---|---:|
| 1 | `a1-nouns-first-words` → `/lessons/a1-nouns-first-words/` | 7 | 4, `EX-00001`–`EX-00004` | 4 |
| 2 | `a1-verb-be` → `/lessons/a1-verb-be/` | 7 | 5, `EX-00005`–`EX-00009` | 4 |
| 3 | `a1-determiners-a-the-this-my` → `/lessons/a1-determiners-a-the-this-my/` | 7 | 6, `EX-00010`–`EX-00015` | 4 |
| 4 | `a1-have-like-can-do` → `/lessons/a1-have-like-can-do/` | 7 | 6, `EX-00016`–`EX-00021` | 4 |

Это **21 основное упражнение и 16 переводов**, а не «по шесть упражнений в каждом уроке». Некоторые комментарии в моделях используют прежнее общее описание; фактическое число задают записи и queryset.

`templates/lessons/detail.html` показывает сначала краткий мостик ясности (`plain`, `why`, `pattern`, `mistake`, `fix`, пример/перевод, contrast, три scaffold-шага), затем семь слоёв. После слоя 5 появляются `sound_notes` и `contractions`, если они есть. Затем идут основные упражнения, переводы, ссылка на независимую проверку, речевая мастерская и активная лаборатория. Боковая колонка берёт слова из `lesson.units`.

`static/js/a1-learning-route.js` переключает глубину чтения; это меняет видимость частей, но не изменяет источники. Режим «полностью» и HTML без JS нужно проверять отдельно от режима «суть».

Основные задания рендерит `templates/components/drill.html`, переводы — `templates/components/translate_drill.html`. В HTML до проверки находятся условия, варианты выбора/конструктора и скрытая подсказка, но нет списка серверных `accepted`. Кнопка показа ответа включается клиентским кодом после двух неуспешных попыток; серверный `reveal` — отдельная ветка API и не является проверкой знания. См. `static/js/learning-player.js:19–151`.

## 2. Загрузка, ID и отличие исходника от runtime

`apps/core/management/commands/load_content.py:78–100` загружает словарь → план недель → уроки → карту историй/стихов → истории → стихи → недели в транзакции.

`Command.load_lesson:198–263` (точный диапазон также доступен в полном файле) проверяет YAML, `practice.review_of` и поля. Привязывает урок по `slug`; слой по номеру; упражнение `_load_exercises:102–151` сопоставляет по стабильному `uid`, сохраняет/архивирует исторические упражнения и переносит номера безопасно. `PracticeItem` сопоставляется по `(lesson, order)` и отдельного стабильного EX UID не имеет. Связи `units` назначаются `_set_units`, неизвестные LX не игнорируются.

Числовой `pk` используется в HTTP API, **но не является переносимым ID задания**. Его нельзя угадать по EX-номеру или перенести из старой базы. `runtime_smoke.py` получает `pk` из загруженной изолированной базы и вызывает `reverse()`. Эти pk в журнале помечены `fixture_only`.

**Автоматически создаваемых `listen`/`dictation` PracticeItem на этом SHA нет.** В `apps/drills/models.py:107–108` есть только kind `translate`, а `load_content.py:219–220` отклоняет иной kind практики. Не следует добавлять в карту вымышленные три аудиозадания на урок. Диктант и обратный перевод существуют в отдельной клиентской лаборатории — см. раздел 5.

## 3. Реальная проверка ответов

| Вид | Источник нормализации и проверки | Что означает совпадение / несовпадение |
|---|---|---|
| Основное упражнение | `apps/drills/models.py:60–66`, `Exercise.normalize/is_correct` | Точное равенство нормализованному `answer` или `accepted`. Регистр, пробелы, запятые, правый типографский апостроф и крайние `. ! ?` нормализуются. Сокращения автоматически **не раскрываются**. |
| Перевод PracticeItem | `apps/drills/models.py:69–96,129–132`, `loose_normalize/is_correct` | Регистр, пунктуация и оба типографских апострофа нормализуются; поддерживаемые сокращения раскрываются таблицей `CONTRACTION_FORMS`. Это конечная таблица и список образцов, не семантический анализатор. |
| Узкие независимые meaning/writing | `apps/learning/understanding.py:145–152`, `model_agreement` | Используется `Exercise.normalize` и поле accepted задания. Совпадение лишь с известным образцом. |
| Независимые transfer/explain | `apps/learning/independent_views.py:189–222` | Свободные ответы сохраняются как `self_reported`; машина не выдаёт грамматическую оценку. |
| Активная лаборатория | `static/js/a1-active.js:5–17`, `normalizeAnswer/compareModelAnswer` | Отдельная браузерная нормализация: убирает кавычки/апострофы, регистр, часть пунктуации; не раскрывает `I'm` в `I am`. Образец/alternatives не являются исчерпывающим списком правильных форм. |

API маршруты определены `apps/api/urls.py`:

* `POST /api/exercises/<pk>/check/` → `check_exercise`, `apps/api/views.py:18–60`.
* `POST /api/practice/<pk>/check/` → `check_practice`, `apps/api/views.py:98–120`.
* `POST /api/units/<uid>/recall/` → `recall_unit`, `apps/api/views.py:64–78`.
* `POST /api/poems/1/gaps/<index>/` → `check_poem_gap`, `apps/api/views.py:82–94`; `index` берётся из реального `poem.gaps`, не из номера строки.

`apps/api/validation.py:5–34` принимает JSON-объект; `answer` должен быть непустой строкой до 200 символов; envelope до 16384 байт; `reveal` только bool. Некорректный payload получает 400, неправильный HTTP-метод — 405, неопубликованный/отсутствующий объект — 404. Браузер посылает CSRF cookie заголовком в `learning-player.js:4–16`.

В `check_exercise` обычное несовпадение фиксированного задания считается неверным. Для A1 `fill + transfer` действует `is_open_pilot_response` (`apps/drills/retry_guidance.py:55–61`): несовпадение означает `assessment=needs_review`, `saved=false`, без штрафа за недоказанную ошибку. Это относится к `EX-00004`, `EX-00009` и другим соответствующим записям, определяется полями, а не названием темы.

Для всех PracticeItem несовпадение всегда `needs_review`, а не подтверждённая ошибка; автоматическое сохранение верного перевода идёт через `record_practice`. При совпадении перевод получает `model_match`.

`apps/learning/services.py:15–42` сохраняет ответы/UnitProgress только аутентифицированному пользователю. Аноним может проверить ответ, но прогресс не сохраняется. Тест в Django Client, даже с CSRF, не измеряет качество обратной связи для реального новичка.

## 4. Подсказки и повторение

`apps/drills/retry_guidance.py:43–78` читает `content/manifests/a1_retry_guidance.json`. Для choice ищет конкретный неправильный вариант; иначе отдаёт focus/hint. Эти дополнительные объяснения нужно рецензировать вместе с уроком, а не считать их уже исправленными по тексту YAML.

`apps/learning/mistake_review.py:23–79` собирает банк A1 из восьми ранних пакетов, поздних topic-пакетов и micro-overrides. Для рассматриваемых уроков действуют **индивидуальные ранние карточки**: `a1_delayed_review_01.json` для урока 1, `a1_delayed_review_02.json` для урока 2, `a1_delayed_review_03.json` для урока 3 и `a1_delayed_review_04.json` для урока 4. В каждом из 21 упражнений — пять новых вопросов, итого **105 карточек**. Формат карточки: `[prompt_ru, prompt_en, options, correct_index, optional_reason]`; индекс правильного варианта нулевой.

`schedule_review:115–133` назначает +48 часов после фиксированной ошибки; повторная ошибка до срока не отодвигает дату. В `apps/api/views.py` это выполняется с записью попытки в одной транзакции. Свободный ответ, не совпавший с образцом, не получает автоматического штрафного повторения.

Ученик может добровольно попросить повторение: `apps/learning/delayed_review_views.py:98–123` — по открытому упражнению либо через `PracticeItem.review_of` к основному заданию. Маршруты в `apps/learning/urls.py`; вся очередь требует login. Страница `mistake_review` отдаёт только текущую карточку после due-date и по собственному правильному индексу, использует её собственное объяснение (строки 35–65), а не объяснение исходного упражнения.

Обычные карточки словаря строятся динамически `apps/learning/services.py:46–110`: после известных UnitProgress могут показываться нерешённое упражнение или `RecallItem` «Как по-английски…?». Для Recall принимаются lemma и `forms` единицы с нормализацией Exercise. Это не ещё один статический пакет готовых фраз.

## 5. Активные и устные задания

`apps/core/a1_active.py:29–79` соединяет три набора по номеру `n`:

* `content/active_a1/topics_01_08.json`: основной supplemental topic, собственный dialogue, варианты и model;
* `content/active_a1/error_repairs_01_18.json`: wrong/correct/hint/reason/alternatives;
* `content/active_a1/scenarios_01_06.json`: шесть миссий и два twists.

`/lab/a1/1/` … `/lab/a1/4/` → `active_a1_topic`, `apps/core/a1_active.py:87–110`. Проверяется, что соответствующий канонический урок опубликован. Template `templates/core/a1_active_topic.html:218–219` передаёт собранный topic через `json_script` в `static/js/a1-active.js`.

Здесь собственный дополнительный диалог, он **не тождественен диалогу недели**. Нельзя подменять один другим в рецензии.

`static/js/a1-active.js:18–24,189–239` выбирает ровно одну реплику `dialogue[(n-1) % dialogue.length]` для локального диктанта и обратного перевода. Это две клиентские активности на странице lab; нет новых EX UID, серверного PracticeItem или записи formal listening score. `runtime_smoke.py` выводит фактическую выбранную реплику для каждого урока.

Звук lab использует `speechSynthesis`, `SpeechSynthesisUtterance` и доступный голос **en-US** (`a1-active.js:72–75,100–171`). Если системного голоса нет, отображается объяснение ограничения. Это не профессионально записанное и проверенное актёрское аудио. Браузерные голоса/произношение не подтверждены HTTP-тестом.

В каноническом уроке те же шесть scenario missions становятся речевой мастерской (`templates/lessons/detail.html`, `#spoken-coach`). Ключ сохранения метаданных `lesson:<slug>`, маршрут `/learning/speech-practice/`. `apps/learning/speech_practice.py:25–99` валидирует публикацию, ключ, индекс 0–5 и самооценку; **голос не записывается и автоматически не оценивается**. Повторение голоса — отдельная очередь `/learning/speech-review/`.

## 6. Независимая проверка и дополнительный пилот

`/learning/independent/<slug>/` → login-required `apps/learning/independent_views.py:31` для опубликованного A1. `understanding_bank` соединяет по slug:

* `content/manifests/a1_understanding_checks.json`: краткие объяснения, контрасты и четыре задачи (`meaning`, `writing`, `transfer`, `explain`);
* `content/manifests/a1_scaffold_transfer.json`: три поясняющих шага и два дополнительных варианта transfer.

На GET показаны четыре условия без моделей. Для современного batch POST нужен одноразовый session token, четыре непустых ответа, вариант transfer и самоотчёт об использовании помощи; свободное объяснение от 10 символов. Модели открываются после всех четырёх ответов. `IndependentAttempt` хранит снимок исходного условия/образца и тип свидетельства; модели автоматически не считаются преподавательской верификацией. Template: `templates/learning/independent_check.html`, JS `static/js/independent-check.js`.

Отдельно существует opt-in retention pilot `apps/learning/transfer_pilot.py:23–88,120`, исходные задания заданы **в Python**, не только в YAML. В первой группе участвуют `a1-verb-be` и `a1-have-like-can-do`; маршруты `/learning/transfer-pilot/<slug>/`. Ссылки на оба пилота присутствуют в `templates/learning/dashboard.html:41–46`; прямой ссылки из шаблона независимой проверки нет. Его стадии initial/day_7/day_30 имеют варианты 100–102 и отдельную временную логику, поэтому полные Python-исходники и template включены в snapshot. Это экспериментальная дополнительная связь, а не обязательный экзамен урока.

На исходном main есть открытый PR #115, меняющий изоляцию экспериментальных записей в обычной самооценке. Пакет фиксирует текущий main, не применяет этот PR и не выдаёт его исправления за уже действующие. Проверять конкретную семантику следует на SHA пакета.

## 7. Недели, история, стих и звук

Первая группа охватывает две недели: `/levels/a1/weeks/1/` и `/levels/a1/weeks/2/`. Маршрут и состав контекста — `apps/curriculum/urls.py`, `apps/curriculum/views.py:week_detail`. `content/seed_weeks/a1_w01.yaml` и `a1_w02.yaml` содержат text/spoken/ru, story_beat, chunk UID, twister и mission_ru. `apps/stories/script.py:18` обрабатывает каждую реплику и роли из `voices.yaml`; имена/характеры из metadata нельзя подменять догадками.

`templates/curriculum/week.html:22–51` показывает диалог, уроки, фразы, скороговорку, mission и роль. Проигрывание роли отключено без audio. Проигрыватель — `templates/components/script_player.html` и `static/js/audio-player.js`; скороговорка — `templates/components/twister_trainer.html` плюс speech studio/shadowing/review.

`content/manifests/course_map.yaml` действительно связывает **историю 1 Not My Box и стих 1 со второй неделей A1**, а не с уроком 1 как прямым FK. Маршруты: `/stories/1/`, `/stories/poems/1/`; `apps/stories/views.py:story_detail/poem_detail`, templates `templates/stories/detail.html`, `templates/poems/detail.html`. `Story.new_units`, `Poem.target_units`, gaps, pronunciation, вопросы истории и задания пересказа должны проверяться из полных snapshot-источников.

Загрузчик ищет аудио по `static/audio/weeks/a1-w01/manifest.json`, `a1-w02/manifest.json`, `stories/s01/manifest.json`, `twisters/t001/manifest.json`, `t002/manifest.json`; валидирует `scripts.audio_readiness.validate_manifest`. Сам факт существования пути в коде не означает наличия файла. Наличие/валидность фиксирует отдельный новый журнал root; отсутствие этих файлов в checkout не доказывает отсутствие на рабочем сайте. Искусственные test-тоны и сам формат IPA не подтверждают произношение.

## 8. Словарь и учебная разметка

`/words/<uid>/` → `apps/lexicon/views.py:unit_detail`; template `templates/lexicon/detail.html` показывает перевод, meaning, примеры, collocations, chunks, формы, usage_note, typical_error, grammar_features, lexical class и обратные ссылки `unit.lessons`. Связь по `lesson.units` и упражнениям — явная, а присутствие слова в body — другая связь; не следует считать любой список units порядком первого знакомства со словом.

Источники классификации — `apps/taxonomy/registry.py` и `apps/curriculum/registry.py`. `apps/taxonomy/markup.py:find_issues/render_inline/render_block` проверяет/рендерит `[S2]...[/]`; template filters — `apps/taxonomy/templatetags/markers.py`. Легенда доступна `/markers/` через `apps/taxonomy/views.py:legend`; для проверки определений нужен также `templates/taxonomy/legend.html`.

Русская учебная транскрипция создаётся из IPA функциями `apps/lexicon/phonetics.py`; фильтр `ru_tr` в **`apps/core/templatetags/ru.py`** читает `ipa`/`ru` для словаря dict либо `ipa_us`/`ipa_ru` для модели. Справочник трудных звуков — `templates/components/sound_legend.html`. Цвет семантического класса не показывает правильность/неправильность глагола: смысл написан и в шаблоне словарной страницы.

## 9. Доступная runtime-проверка и границы

`runtime_smoke.py` — дополнительный воспроизводимый preparation script, не изменение приложения. Он требует `config.settings.test`, точный `--database`, SQLite не в корне checkout и отдельный marker `REVIEW_DATABASE_ONLY` со SHA. Сам не мигрирует/загружает; все временные пользователи, сессии и ответы откатываются транзакцией. Production не используется.

Проверяет Django Client с CSRF: четыре урока, число форм/слоёв, все записанные canonical/accepted через фактический API, mismatch/reveal, неверный тип payload, словарные страницы явных lesson.units, lab/выбранную retrieval-реплику, login-gate, четыре независимых задачи/сохранённые типы результатов, шесть speech targets, пилоты, +48h review и связанные week/story/poem/legend URLs.

Новый запуск выполнен root в явно изолированной SQLite: **PASS, 448 assertions, temporary_rows_rolled_back=true**. Полные результаты: `evidence/local/runtime-smoke.json`; stderr/команда/exit code находятся в общем журнале запусков. Проверены именно перечисленные узкие runtime-инварианты, не «вся грамматика уроков». Фактические выбранные реплики лаборатории:

| Урок | Индекс dialogue с нуля | Реплика |
|---|---:|---|
| 1 | 0 | Tom: `This is my phone.` / «Это мой телефон.» |
| 2 | 1 | Mia: `Yes, Tom is home.` / «Да, Том дома.» |
| 3 | 2 | Tom: `It's my book.` / «Это моя книга.» |
| 4 | 0 | Mia: `Do you have my phone?` / «У тебя мой телефон?» |

Это не визуальная проверка desktop/390 px, keyboard, reduced motion или реальное прослушивание. `scripts/verify_atlas.cjs` — отдельная браузерная проверка сравнения двух checkout; её штатные экраны home/collection/week13 не заменяют приёмку уроков1–4. Запуск штатного скрипта использует `config.settings.local` и два сервера; нельзя запускать его с неявной/рабочей базой. Для данной подготовки браузерный gate должен использовать только явно изолированное окружение.

Достоверно отсутствует автоматическая полная семантическая оценка свободной речи; это граница реализации. Редакторская оценка ясности, естественности американского английского и достаточности prerequisites остаётся задачей следующего рецензента. Автоматические 15 `quality_gates` в `understanding.py` — структурные контракты, а не 15 независимых педагогических экспертиз.
