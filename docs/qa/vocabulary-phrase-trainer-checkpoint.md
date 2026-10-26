# Точка продолжения: тренажёр слов и фраз

Состояние на 2026-10-26 после явного «Продолжай»: реализация и независимое ревью завершены. Проверенный код: `dc9a282b516cbf11dd9d89ec2d6547a5d12954bb`; локальная ветка `feat/vocabulary-phrase-pilot` от согласованного main `fbec5724b67b9caf7045fa3a4da386607eedb759`. PR129 проверен как merged; переключатель глубины не возвращён. Флаг выключен. Рабочие и production базы не открывались и не мигрировались; merge, auto-merge и deploy не выполнялись.

Рабочая область: `/workspace/scratch/9aa7896d9057/English-Encyclopedia/.worktrees/vocabulary-phrase-pilot`. Исследовательский checkout сохранён без reset/clean. CLI push не имел credentials; подключённый GitHub сохранил эквивалентные trees с проверкой expectedSHA, без force. Локальному dc9a282 соответствует удалённый `1980fc7b8c38152f5419149047ac9f941e95edad`, tree `e0e7341eac65dbc814e181fd361bf90343f8f13a`. Следующий документационный коммит добавляет итог QA. Фактические latest SHA, CI и PR нужно сверять через GitHub, а не угадывать по историческому checkpoint.

## Подтверждённые результаты

- Ровно три единицы после `a1-cafe-order` (урок5, неделя3): LX-00055 tea; LX-00285 I would like a coffee, please.; LX-00084 Sorry? Can you say it again, please? Уроки, порядок и UID сохранены; все четыре метода связаны вокруг каждой единицы.
- Единый `UnitProgress` и журнал `IndependentAttempt`; additive migration0013 добавляет enrollment, session и private mnemonic. Версии, история, idempotency, ownership, export/delete сохранены.
- Обычный POST и vanillaJS: скрытие ответа, ограниченные повторы, uncertain feedback, честная устная самооценка, новая ситуация, личная ассоциация и восстановление после сбоя. Расписание определяет сервер. Выбранные показы старых материалов отмечаются как помощь; прежний MistakeReview через48h сохранён.
- Ревью всей ветки и одна финальная волна закрыли1Important и1Minor. Повторное scoped review: SpecPASS / QualityApproved; открытых материальных замечаний нет.
- Свежий полный Django-прогон dc9a282:1038тестов за327.355s, OK (два PostgreSQL-only RLS пропущены в SQLite), exit0. Node152/152; CSS21; check, migrationcheck, compile, diff, strictCEFR, disposable load/audit — PASS.
- Реальный Chromium153:40/40 проверок;320/390/1280px при100% и фактически удвоенном тексте; клавиатура, reduced motion, lost accepted response/retry, noJS и owner404. Отдельное повторение с контролируемым сдвигом26h и проверкой БД: PASS, stage0→1, другая family и новая application. Это не доказательство памяти или реальной речи человека.
- PNG просмотрены отдельно: desktop100%, mobile/desktop200%, шапка, текст и controls, корректное объяснение помощи после recall. Screen reader, Firefox/Safari и human trial не проводились.
- PostgreSQL локально недоступен. Настоящий job `postgres` должен быть проверен в CI. При создании этого checkpoint публикация draftPR и чтение actualCI ещё являются следующей внешней операцией; финальные факты будут в описании PR и ответе.

## Документы и продолжение

- Дизайн: `docs/superpowers/specs/2026-10-26-vocabulary-phrase-trainer-design.md`.
- План: `docs/superpowers/plans/2026-10-26-vocabulary-phrase-trainer.md`.
- Проверки, все изменённые файлы, решения, безопасный disposable preview, rollout/backup/restore, версии/retention и human protocol: `docs/qa/vocabulary-phrase-trainer.md`.
- Локальные ignored ledger, reports, logs и PNG: `.superpowers/sdd/vocabulary-phrase-trainer/`. Сохранить их и worktree для продолжения.

При продолжении сначала проверить main/feature HEAD, незакоммиченные изменения, **существующий PR этой ветки** и CI. Не создавать второй PR или ветку и не повторять завершённые Task1–3. Если draftPR уже опубликован, продолжать в нём. Не сливать и не мигрировать рабочую/production БД без отдельного разрешения. Новая реализация требует согласованного scope. Preview — только с отдельными явными settings/SQLite из QA-документа.
