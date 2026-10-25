# A1 9–12 — локальный WIP checkpoint

author: Codex
reviewed_by: целевые автоматические проверки; содержательная приёмка ожидается
verification_status: technical_review
date: 2026-10-25
source_notes: реальные исходники на 5826785, независимое чтение, два набора регрессий, первичные справочники из SOURCES.md

Это реальное внедрение следующей группы, сохранённое до полного прогона. Оно не опубликовано и не означает приёмку курса. Baseline `5826785ee3f665fac765783ba9a95a5dd3b52655`, ветка `editorial/a1-09-12-deep-review-20261025`. Уроки 5–8 в эту ветку не перенесены. Программной зависимости от их новых UID или механизмов нет: используются существующие API и только строки 9–12 общих JSON. При дальнейшем переносе нужно сохранить параллельные правки других строк.

**Текущий результат: 86 целевых/связанных тестов PASS; полный Django, полный pytest, браузер и реальное аудио ещё не проверены на этом пакете.**

- [STATUS.json](STATUS.json), [CHECKS.md](CHECKS.md) — точные результаты и следующий запуск.
- [LESSON_NOTES.md](LESSON_NOTES.md), [SHARED_NOTES.md](SHARED_NOTES.md) — полные авторские решения и ограничения двух исполнителей; исходные `/tmp` пути внутри исторических записей сопоставляются с локальными копиями в `evidence/`.
- [LESSON_CHANGES.json](LESSON_CHANGES.json), [SHARED_CHANGES.json](SHARED_CHANGES.json) — полные before/after, не пересказ исходников.
- [READTHROUGH_FINDINGS.json](READTHROUGH_FINDINGS.json), [READTHROUGH_REPORT.md](READTHROUGH_REPORT.md) — первоначальный пакет чтения. Это исходный снимок предложений, а не итоговый статус; применённые решения находятся в notes/ledger.
- [TESTED_SOURCE_SHA256.json](evidence/TESTED_SOURCE_SHA256.json) — конечные хеши 19 исходников и тестов. `verify_checkpoint.py` проверяет их, стабильные ID, границы и неизменность озвучиваемого текста.

Новые определения тестов заморожены до сравнения на исходном снимке: 13 owned-тестов дали 25 failures до правок, девять shared-тестов — 25 failures. После исправлений оба набора проходят. Число падений включает подслучаи и не является числом независимых языковых ошибок или оценкой качества.

Один старый тест требовал буквальное `any water`, хотя any не введено к этой неделе и обычный вопрос `Is there water?` допустим. Исходный integrated FAIL сохранён отдельно. Исправлена ошибочная проверка обязательного слова, сохранена проверка обычного вопроса и просьбы; добавлен реальный vocabulary/API контракт. Тесты и CI не отключались, нормализация и whitelist не расширялись. Подробности в CHECKS.md и [OLD_TEST_CONTRACT.patch](OLD_TEST_CONTRACT.patch).

Полные окончательные уроки, задания, ключи и словарные записи находятся в изменённых файлах `content/`. Английские озвучиваемые тексты историй, диалогов, скороговорок и стихотворения, IPA и пять решений пропусков не менялись. Это не подтверждение прослушанной озвучки.


Checkpoint publication: the working sources are preserved in branch `editorial/a1-09-12-deep-review-20261025`. This is WIP, not a claim that full Django/pytest or human acceptance has passed. No PR/merge/deploy is performed by this checkpoint.
