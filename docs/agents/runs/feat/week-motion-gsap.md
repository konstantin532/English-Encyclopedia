# Анимация страницы недели на GSAP

База: `origin/main 46afcdabc4292a900763f19ba37c18e616282ade`; ветка `feat/week-motion-gsap`.

Цель: требования автора от 2026-10-30: локальные Flip, ScrollTrigger, SplitText 3.15.0; нативный переход каталог ↔ неделя; раскрытие карточек уроков, проявление заголовка и ориентирование по разделам. React не используется.

Готово, когда: проверки затронутой части, полный набор один раз, ui-acceptance, независимый ui_reviewer и Visual review выполнены; недоступные проверки обозначены BLOCKED; открыт PR без слияния.

## План и UI-чеклист

- [ ] Этап 1: плагины и межстраничный переход. `static/vendor/gsap/{Flip,ScrollTrigger,SplitText}.min.js` той же версии, что ядро; `week-motion.scss`; уникальная пара title/cover по slug уровня и номеру в карточке каталога и трёх вариантах обложки недели. Ссылки остаются обычными; CSS подключается только к каталогу и неделе. Проверка: версии, уникальные имена, браузерный переход и Firefox.
- [ ] Этап 2: `static/js/week-motion.js` и шаблон недели. Нативные `details open` показывают существующее `lesson.summary` и отдельную ссылку «Открыть урок»; Flip объясняет изменение размера, без масштабирования текста. SplitText делит только слова, сохраняет доступное имя, возвращает исходный DOM после появления. ScrollTrigger проявляет только заголовки разделов, не скрывает учебный текст. Исключить новые цели из старой системы. Проверка: реальные плагины, клавиатура, быстрые повторы, отказ каждой зависимости, ручной Minimal, системный reduced motion, BFCache.
- [ ] Этап 3: сборка CSS, проверки Django и UI, полный набор один раз с `--settings=config.settings.test`, независимая ui-acceptance, HTML/CSV отчёт и PR с Visual review. Скриншоты и SQLite остаются вне репозитория.

Существующие решения: `DESIGN.md` §7 определяет 180–450 мс и мягкую кривую. Переиспользуем `--motion-duration-standard`, `--motion-ease-enter`, `--font-read` (Literata), `--font-ui` (Golos Text), `--space-*`, существующие три обложки и `studio-lesson-card`. Новый именованный токен — длительность изменения раскладки 360 мс. Никаких новых цветов или учебных текстов.

Проверяемые риски: отсутствие GSAP/плагина оставляет контент и навигацию; смена reduced motion в середине эффекта очищает стили; повторные нажатия не портят высоту и фокус; общие элементы не дублируют имена; возврат из BFCache не оставляет SplitText или старые трансформации. Без JS все карточки изначально открыты. Новая подпись интерфейса: «Открыть урок».

## Исходное состояние

Рабочая копия содержит посторонние untracked `audio-human-review.csv`, `git`, `update_after_pr147.bat`; их не меняем. PR #157 с описаниями агентов открыт отдельно; ветка анимации от main и не содержит его изменений. Определение `ui_reviewer` прочитано до переключения; независимый проверяющий получит его инструкции явно.

Context7: BLOCKED (Monthly quota exceeded); API сверены по официальным GSAP и MDN. Исходные файлы плагинов: `https://raw.githubusercontent.com/greensock/GSAP/3.15.0/dist/`. Заголовки лицензии сохраняются.

Исторический открытый PR #157 сообщает о двух предсуществующих сбоях phrase_memory и необходимости явных тестовых настроек на Windows; для этой ветки это пока гипотеза, подтвердить командами.

## Этап 1

Добавлены три оригинальных плагина 3.15.0, уникальные имена `week-<level>-<number>-title/cover` и ограниченный каталогом/неделей CSS View Transitions. Исходные шаблоны/статика и две отдельные SQLite-базы для браузера находятся в scratch вне проекта. Baseline на 375/390/768/1440 px: диалог недели 1 начинается с 1132/1104/1109/1017 px; горизонтального переполнения нет. Новые тесты до реализации подтвердили отсутствие плагинов, имён, карточек и скриптов (6 failures).

`pnpm build:css` → Stylesheets verified: 23. Проверка версий/имён и существующей обложки (`tests.test_week_motion` два метода + `tests.test_week_one_cover`) → Ran 7 tests; OK.

## Этап 2

Добавлены открытые по умолчанию нативные карточки уроков с существующим описанием и ссылкой. Flip меняет размер без масштабирования текста; SplitText проявляет слова заголовка и возвращает исходный DOM; ScrollTrigger меняет только прозрачность заголовка раздела. Временные стили очищаются при прерывании, reduced motion и pagehide. Старая система не анимирует те же цели. Реальные ссылки не перехватываются.

- `uv run python manage.py test tests.test_week_motion tests.test_motion_system tests.test_week_one_cover tests.test_planned_week_cards --settings=config.settings.test` → Ran 16 tests; OK.
- `node --test tests/js/motion-system.test.cjs tests/js/intro-policy.test.cjs` → 7 pass, 0 fail.
- `pnpm check:css` → Stylesheets verified: 23; `pnpm test:ui` → 201 pass, 0 fail. Первый UI-прогон столкнулся с нашими серверами на fixture-портах 8133/8134; серверы перенесены на 8243/8244 без изменения тестов, повтор зелёный.
- `WEEK_MOTION_URL=http://127.0.0.1:8244 node scripts/check_week_motion.cjs` с Playwright на NODE_PATH → 10 checks PASS, 0 BLOCKED: настоящие Flip/ScrollTrigger/SplitText, повторные клавиатурные действия, смена режима во время Flip, отсутствие ядра/каждого плагина, отсутствие JS, Chromium View Transition и обычная навигация Firefox 153.0.
- `impeccable detect --json <изменённые UI-файлы>` → `[]`, exit 0. Ограничение: детектор не понимает Django `{% static %}`, поэтому автоматическая проверка связей CSS/токенов неполна; в браузере подключённые стили проверены.
- `uv run python manage.py check` → System check identified no issues; `makemigrations --check --dry-run` → No changes detected.

Независимый `ui_reviewer`: 4 URL, 14 состояний ширины/базы, 0 новых P0–P2. Найденный P3 (inline strong внутри новой обёртки) исправлен в общем исходном `static/css/living-atlas.css`; файл написан вручную и не входит в SCSS-сборку. Повторная независимая проверка двух карточек каталога и главной на 390/1440 подтвердила нулевые изменения размеров. Шесть сочетаний переключателей диалога совпали с baseline, без JS обе карточки открыты. Отдельный API-review не нашёл ошибок runtime; скрипт приёмки явно добавлен через `git add -f` из-за Windows-правила `/Scripts/`.

Полный набор запущен один раз: `uv run python manage.py test tests --parallel auto --settings=config.settings.test` → Ran 1264 tests in 331.746s; FAILED (failures=2, skipped=8). Сбои: `PhraseEntryLinkTests.test_link_hidden_when_disabled`, `RegisterHookTests.test_disabled_flag_writes_nothing`. Оба повторены на snapshot шаблонов main 46afcdab с неизменённым backend → Ran 2 tests; FAILED (failures=2). **BLOCKED:** полный набор остаётся красным из-за этих предсуществующих проблем, они не исправляются в задаче анимации.

Следующий шаг: завершить итоговую Visual review после правки общей карточки, оформить HTML/CSV и PR. Физические устройства, Safari, Lighthouse и полная ручная проверка контраста пока не проверялись; калибровка UI-checker не выполнялась (независимый фактический проход выполнен).
