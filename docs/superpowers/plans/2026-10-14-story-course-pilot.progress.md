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
