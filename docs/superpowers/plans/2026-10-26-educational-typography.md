# Educational Typography Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Распространить согласованную типографику на реальные учебные поверхности, сохранив содержание и поведение.

**Architecture:** Одна система переменных с тремя ролями оформления, подключаемая только внутри учебного контента. Общие истории и диалоги используют существующий script_player; стихотворения получают отдельные правила строк и строф. Пилот двух уроков сохраняется как проверенная основа, его поведение глубины не переносится автоматически на остальные58.

**Tech Stack:** Django templates, SCSS/CSS variables, существующая Node-сборка, Django/Node tests, поддерживаемый браузер пользователя.

**Spec:** ../specs/2026-10-26-educational-typography-design.md

## Global Constraints

- Все точные палитры и роли гарнитур из спецификации обязательны; Gentium Plus для IPA.
- Не менять учебный текст, маркеры, accounts, данные, миграции, сервер8000 и внешнюю геометрию.
- Сначала безопасный перенос на свежий main; только затем расширение и повторная проверка.
- Сначала история1, стихотворение1, диалог недели1; затем общий охват. Итог — отдельная ветка и draft PR, без merge.

## Review Focus

1. Длинное имя/эмоция и длинный перевод при390/320px не выталкивают текст — задача3.
2. Длинная стихотворная строка при200% переносится визуально внутри одной строки DOM, строфа не исчезает — задача3.
3. Hidden, «Без текста», spoken/written и active audio line не раскрываются общим CSS — задачи2/3.
4. A−/A+ масштабирует перевод и ответы, IPA не заменяется другим шрифтом — задача4.
5. Общий стиль не затрагивает каталог/sidebar/accounts и не возвращает устаревший main — задачи1/4/5.

## Реальные файлы и границы

- `static/scss/system/_typography.scss`, `static/scss/system/_tokens.scss`: существующая система. Новые переменные адаптируются к существующим --ee-*; не заводить второй глобальный body-стиль.
- Создать `static/scss/educational-reading.scss` → `static/css/educational-reading.css`: единый scoped слой учебного чтения; сборщик `scripts/build_styles.mjs` уже автоматически обрабатывает entrypoints, это перепроверить на свежей базе.
- `templates/lessons/detail.html`, `templates/stories/detail.html`, `templates/poems/detail.html`, `templates/curriculum/week.html`: подключение роли на корневой обёртке учебной поверхности и page_styles.
- `templates/components/script_player.html`: единая композиция реплик историй/диалогов; сохранить data-line, data-speaker, line-spoken/written/full/ru и языки.
- `templates/stories/map.html`: внутренняя иерархия названия/описания/метаданных существующих карточек; внешняя сетка без изменений.
- `templates/learning/independent_check.html`, `mistake_review.html`, `review.html`, `speech_review.html`, `transfer_pilot.html`, `cafe_mission.html`: минимальная роль тренировки. Dashboard/accounts исключены.
- `tests/test_educational_typography.py` и `tests/js/educational-typography.test.cjs`: сохранность контента, scoped подключения и критические состояния; повторно использовать существующие тесты плеера и маркеров.

### Task1: Зафиксировать текущую правку и перенести основу

**Files:** текущие восемь файлов пилота; новых продуктовых файлов на этом шаге нет.

**Interfaces:** consumes branch codex/lesson-design-pilot на6e96df2; produces та же ветка с сохранённым пилотом поверх фактически свежего origin/main.

- [ ] Дождаться и записать финальный статус текущих700 Django-тестов,123 Node-тестов,4 профильных,17 stylesheet, browser desktop/mobile. Не выдавать незавершённый запуск за pass.
- [ ] Сохранить только принадлежащие задаче tracked/new product files локальным коммитом. Исключить pilot.sqlite3, graphify-out, node_modules, логи, Library helpers.
- [ ] Прочитать инструкции свежего main; fetch origin main без checkout/reset основного репозитория. Сравнить SHA, git log и diff по каждому пересекающемуся файлу.
- [ ] Перенести коммит пилота на свежую основу в этой изолированной ветке; разрешать конфликты по конечному поведению, сохраняя слитые изменения. При содержательном противоречии предъявить конкретный diff.
- [ ] Прогнать тесты пилота/глубины и Node suite; открыть оба урока на8001 после штатного перезапуска только этого сервера.

### Task2: Создать общий слой с тремя ролями

**Files:** create educational-reading.scss/css, tests/js/educational-typography.test.cjs; modify подключение в трёх контрольных шаблонах.

**Interfaces:** root `[data-educational-reading]`; `data-reading-theme="friendly|academic|minimal"`; consumed variables `--font-ui`, `--font-read`, `--font-ipa`, `--reader-scale`; produces scoped `--edu-*` roles for palette/font/body/example/translation/UI/measure/leading/gaps/focus.

- [ ] Написать тест, который падает на отсутствии scoped entrypoint и трёх точных палитр; запретить глобальные body/sidebar/accounts selectors и переопределение .mk.
- [ ] Запустить новый Node-тест и убедиться в ожидаемом FAIL.
- [ ] Реализовать переменные и правила роли: friendly основной19px/1.75, mobile18px; academic длинное чтение20px/1.8, mobile18px; minimal18px/1.65. Это стартовые решения исполнителя, проверяемые глазами. Перевод минимум17px/1.65 desktop и mobile, масштабируется с reader scale. Кнопки минимум44px; золотой декоративный акцент не используется как мелкий основной текст.
- [ ] Проверить CSS cascade на свежей базе: новый scoped слой не перебивает hidden и режимы плеера, маркеры остаются выше декоративного слоя. Запустить Node-тест и build/check.
- [ ] Зафиксировать самостоятельный рабочий шаг локальным коммитом после проверки.

### Task3: История, стихотворение и диалог как контрольные поверхности

**Files:** stories/detail, poems/detail, curriculum/week, components/script_player; scoped stylesheet; tests/test_educational_typography.py.

**Interfaces:** consumes Task2 theme roles; existing script DOM/data attributes, poem rows/stanza-start and pronunciation untouched; produces три реально проверенные страницы.

- [ ] Добавить Django-тесты сохранности всех script lines, speakers, ru, spoken/written вариантов, количества poem rows/stanza-start, IPA и исходного текста до/после оформления. Проверить ожидаемый FAIL на отсутствии темы.
- [ ] Подключить friendly объяснения/academic чтение/minimal тренировку без добавления настроек пользователя. Реплики отделять ритмом/тонкой линией, не самостоятельной тяжёлой карточкой; имя и аватар остаются явными. На mobile имя выше текста, перевод после своей реплики; полная форма — читаемая вторичная строка.
- [ ] Оформить стих как строфы: нулевой межабзацный отступ внутри строфы, отдельный интервал у stanza-start. Не балансировать строки и не менять пунктуацию/капитализацию.
- [ ] В браузере осмотреть /stories/1/, /stories/poems/1/, /levels/a1/weeks/1/ на1280/390 и320/200%. Проверить длинные реальные имена/переводы на существующем материале; при отсутствии такого контента использовать изолированную тестовую fixture, не изменять seed.
- [ ] Проверить «Без текста/С текстом/С разметкой», «Как говорят/Как написано», disabled/hover/focus/active-line, отсутствие аудио и доступную озвучку без mic/login. Сохранить точный реестр просмотров и реальные снимки поддерживаемым способом; не обещать файлы, если экспорт недоступен.
- [ ] Прогнать профильные Django/JS, сборку стилей; локальный коммит.

### Task4: Распространить систему внутри существующего контента

**Files:** lessons/detail, stories/map, перечисленные learning templates; scoped stylesheet; static/js/studio-reader.js; tests/test_educational_typography.py и tests/js/studio-reader.test.cjs (создать, если отсутствует).

**Interfaces:** uses Task2 themes and verified Task3 reading components; no new content entities, migrations or grading APIs.

- [ ] Добавить тест подключения для всех60 опубликованных уроков, всех11 опубликованных историй,7 стихов и реальных недель с диалогом; количество сверить заново на свежем main. Добавить отрицательные проверки для каталога/sidebar/accounts и отсутствующих уровней.
- [ ] Убедиться в FAIL, затем подключить роли к содержимому и внутренним элементам карточек. Не переносить пилотный data-lesson-design-pilot на остальные уроки: логика глубины остаётся отдельной.
- [ ] Сначала добавить падающий регрессионный тест studio-reader: A−/A+ обновляет общий scoped масштаб для reader, practice и соседнего translate; изменение одной страницы не влияет на другой reader. Сейчас --reader-scale записывается только в practice, поэтому CSS недостаточно. Обновить static/js/studio-reader.js: масштаб на общем data-educational-reading контейнере с совместимым прежним practice fallback, не трогая сохранение размера. Убедиться в PASS.
- [ ] Проверить A−/A+ на минимальном/максимальном размере: объяснение, пример, перевод, input/choices/feedback. Gentium Plus computed font у IPA; обычные буквы и кириллица без обрезки; markers color/mono режимы сохранены.
- [ ] Пройти реальные контрольные длинные/короткие уроки A1 иA1+, вторую историю, стих с длинной строкой, диалог с длинным переводом, тренировку с неверным/верным ответом. Разделить «визуально», «поведением», «не проверено»; не приравнивать массовые HTML-тесты к полному визуальному аудиту.
- [ ] Прогнать Node suite, CSS build/check, полный Django suite с config.settings.test и UTF8, diff check; независимый обзор scoping/содержимого. Локальный коммит.

### Task5: Проверить конечную ветку и опубликовать draft PR

**Files:** docs проверки/покрытия, итоговый branch diff; продуктовые файлы только при обнаруженном дефекте.

**Interfaces:** consumes checked branch based on fresh main; produces draft PR URL, remote head SHA and CI state for that SHA.

- [ ] Сверить свежий origin/main ещё раз и полный diff; убедиться, что чужие изменения основного checkout/8000 не затронуты, DB/helpers/logs исключены.
- [ ] Проверить реальные итоговые страницы8001 и записать результаты, ограничения и способ перезапуска независимого процесса.
- [ ] Push только тематической ветки, создать draft PR в konstantin532/English-Encyclopedia, attach_artifact с его URL. Описание: проблема/результат/границы/проверки/визуальное покрытие.
- [ ] Проверить remote head SHA == локальному HEAD; читать CI только этого SHA, исправить собственные failures без ослабления тестов. При внешнем pending/error указать точное состояние.
- [ ] Передать URL для просмотра, PR, краткие результаты и ограничения. Не делать merge.

## Оценка этапов

Перенос старой основы — отдельный риск, его длительность определяется реальными конфликтами. Ближайший полезный результат — три контрольных интерьера, а не обещание всего охвата за фиксированное время. Затем общая адаптация/проверки, потом PR и CI. Три часа могут быть ориентиром для реализации, но не гарантией полного визуального покрытия и внешнего CI.

## Самопроверка плана

Три палитры/гарнитуры — задача2; контент/стих/говорящие/IPA — задача3; все страницы и масштабирование — задача4; свежий main/изоляция/публикация — задачи1/5. Новые функции данных/оценки не вводятся. Реальные пути сверены со старой базой; задача1 обязана перепроверить их на свежей.

Builder check выполнен независимым read-only reviewer: учтён конкретный пробел масштаба translate в studio-reader.js; остальных блокирующих противоречий не найдено.
