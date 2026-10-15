# Журнал пилота «Курс через историю» — план: docs/superpowers/plans/2026-10-14-story-course-pilot.md

Формат: этап / решение / команда и результат / коммит / непроверенное.

## Подготовка (2026-10-15, Claude в облачной копии)
- Документы концепции и плана скопированы с компьютера автора (локальные коммиты dd53a47, 9995ea2 на GitHub не отправлены); содержимое файлов совпадает побайтно.
- `uv sync` → сбой: нет доступа к PyPI из облака (dns error). Используется существующее окружение .venv (Python 3.13, Django 5.2). uv sync успешным не объявляется.
- Исходное состояние: ветка situation-weeks e15d34d, `manage.py test tests` → OK.
- Сверка плана с кодом: WeekScene/load_week/week.html/render/audit_scene/audit_script(level, week_number)/Exercise.Stage (recognition, substitution, production, transfer) соответствуют плану; маркеры недель 3–4 совпадают с weeks_plan.yaml. Существенных расхождений нет.
- 2026-10-15: пользователь попросил остановиться до правок плана; сделанное перенесено в локальную ветку pilot-draft, situation-weeks возвращена к e15d34d. Правки плана приняты (коммит 1c9d481), разрешены начало работы и отправка на GitHub.
- Решение: этапы 1–3 берутся из pilot-draft (тесты там прошли путь RED → GREEN, см. ниже) и доводятся до новых правил плана: напоминание о spoken во всех неделях, новые формы сокращений.
## Этап 1: необязательная рамка истории
- Решение: STORY_BEAT_KEYS = intro_ru / outcome_ru / next_hook_ru в load_content; неверный тип, лишний ключ или нестроковое значение → CommandError с «story_beat». Вступление — абзац над диалогом (id story-intro), развязка и зацепка — details «Чем всё закончилось» после задания в жизнь. Пустой словарь ничего не выводит.
- Команды: `manage.py test tests.test_story_pilot` → 7 тестов сначала FAIL/ERROR, потом OK; `manage.py test tests` → 132 OK; `makemigrations --check` → No changes.
- Непроверенное: вид блока в браузере — на этапе 6.
- Этап 1, часть 2 (живая речь, правка плана): SPOKEN_REMINDER_LEVELS = A1, A1+, A2 — напоминание о spoken для всех сцен этих уровней и для всех опубликованных историй; SHORTENABLE дополнен he is, she is, here is, what is, who is, does not; исключение «be в конце короткого ответа» (FINAL_BE) распространено на эти формы.
- Команды: SpokenReminderTests сначала 2 FAIL + 1 ERROR, потом OK; manage.py test tests → 136 OK; audit_course на неделях 1–2 и истории 1 — новых предупреждений нет.
## Этап 2: неделя 3 «В кафе»
- Контент: пакет a1_w03_pilot.yaml (LX-00055…LX-00087: tea, cake, photo, or, and, sorry, thanks, числа one…twenty, 6 готовых фраз, в том числе «Sorry? Can you say it again, please?»), сцена a1_w03.yaml (10 реплик, 76 слов, маркеры D1/N1/O2), уроки a1-cafe-order (5) и a1-numbers-1-20 (6) по 7 слоёв и 4 вида упражнений, скороговорка №3 (th).
- Зацепка: на столе семейное фото, «It is a family photo» — не Анны и не Тома. Анна оставляет фото у себя.
- Решение: новая роль barista (голос af_sarah). Чтобы не нарушить правило «роли не берут голоса из общего пула», af_sarah убран из extras — закреплён за бариста.
- Решение: ожидаемые количества в tests/test_content_and_learning.py обновлены (единиц 54 → 87, уроков A1 4 → 6).
- Команды: WeekThreeTests сначала 4 ERROR, потом OK; load_content дважды → 87 единиц, 6 уроков; audit_course → «Ошибок нет», незарегистрированных слов нет; manage.py test tests → 137 OK.
- Непроверенное: настоящая речь Kokoro для недели 3 не генерировалась (в облаке нет модели).

## Этап 3: неделя 4 «Семья на фото» и развязка
- Контент: пакет a1_w04_pilot.yaml (LX-00088…LX-00106: brother, sister, grandmother, grandfather, son, daughter, baby, he, she, his, her, who, happy и 6 фраз), сцена a1_w04.yaml (10 реплик, 70 слов, маркеры T3/D1), уроки a1-family-photo (7) и a1-family-possession (8), скороговорка №4 (dh, r).
- Развязка по-английски: Mia — «It is my photo!», семья: brother (ten), mother, father; Анна возвращает фото («Here is your photo, Mia»). Rose, письма и ключ не упоминаются; история 5 (большое фото, неделя 14) не тронута. Зацепка next_hook_ru — без новых событий: Анна думает о прежних жильцах дома.
- Решение: в уроках недели 4 по три подсказки о произношении — так требует действующий тест курса.
- Решение: упражнение на 's переделано в «This is ___ photo.» → Tom's: ответ «'s» давал аудиту незарегистрированное «s».
- Команды: WeekFourTests сначала 3 ERROR + 1 FAIL, потом OK; load_content дважды → 106 единиц, 8 уроков; audit_course → «Ошибок нет», незарегистрированных слов нет; manage.py test tests → 143 OK.
- Непроверенное: настоящая речь Kokoro не генерировалась.
- Доводка недель 3–4 до правок плана: новое напоминание нашло в неделе 4 «Who is this?» без spoken — добавлен «Who's this?». Остальные пункты правок уже выполнены в черновике: голос af_sarah закреплён за barista и убран из extras, по три sound_notes, без новых имён, числа 1–20 отдельными единицами N1 (LX-00062…LX-00081), в ответах на 's — Tom's.
- Команды: load_content → 106 единиц, 8 уроков, 4 недели с диалогом; audit_course → «Ошибок нет», напоминаний о spoken нет; manage.py test tests → 147 OK.

## Этап 4: связать четыре недели
- Рамки недель 1–2 без новых событий задним числом; по одному заданию transfer в уроки 1–4 (новые комбинации: «This is my book. It is new.», «No, it is not my room.», «This room is big. That room is new.», «Do you have a cat?»). Числа упражнений в tests/test_content_and_learning.py: уроки be/determiners/have 4 → 5, nouns 3 → 4.
- guide.md: путь «услышать → разобрать → сыграть роль → независимая проба → повторение», ориентир 15–25 минут, свободный график, без аудио — не аудирование.
- Редакторская проверка: русская рамка не вводит решающих улик.

| Вопрос истории | Английская подсказка | Английский ответ |
|---|---|---|
| Чья коробка? (нед. 2) | Is this your box, Anna? | No, it is not my box. … It is not my box! |
| Чьё фото в кафе? (нед. 3) | Anna, is this your photo? | No, it is not my photo. … It is a family photo. |
| Чья это семья? (нед. 4) | Is this your family? | Yes! This is my family! It is my photo! |
| Кто на фото? (нед. 4) | Who is this? / Is this your mother? | This is my brother. He is ten. / Yes, it is. And this is my father. |
| Чем кончилось? (нед. 4) | Here is your photo, Mia. | Thank you! I am happy! |
- Команды: PilotContinuityTests сначала 6 FAIL (в черновике), потом OK; load_content, audit_course → «Ошибок нет», незарегистрированных слов и напоминаний о spoken нет; manage.py test tests → 151 OK.

## Этап 5: независимые аудирование и устный ответ
- assessment.yaml: weekly w01…w04 (max_week 1…4) и формы pre/post/delayed (max_week 4); по 3 вопроса prompt_ru/accepted_ru и oral {prompt_ru, cues_ru}; новые ситуации (Мия знакомится с Томом, Мия в гостях у Тома, заказ Мии с ошибкой бариста, семья Тома и др.), с учебными сценами совпадает не больше одной реплики. Новых имён и событий канона нет: кот Анны, брат Мии (10 лет) согласованы с неделями.
- scripts/generate_pilot_audio.py: --engine {kokoro,test}, --output обязателен и принимается только внутри static/audio/pilot-a1 (проверка после resolve до записи); вызывает существующий render, основной генератор не менялся.
- guide.md: протокол (два прослушивания, 0/1 за смысл; устно 0/1/2 по трём признакам, просьба повторить не штрафуется, помощь отмечается), 5–8 участников как удобный размер, delayed через 7 дней, данные обезличенно вне Git, вопросы о впечатлениях, статус «испытание не проведено».
- Команды: AssessmentPackageTests и PilotAudioTests сначала ERROR (нет пакета и скрипта), потом OK; test_future_word_fails подтверждает границу недели.
