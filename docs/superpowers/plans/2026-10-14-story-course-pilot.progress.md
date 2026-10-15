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
