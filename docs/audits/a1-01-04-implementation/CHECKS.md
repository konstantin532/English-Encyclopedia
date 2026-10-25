# Проверки внедрения A1 1–4

Все строки ниже — новые локальные запуски этого этапа. Старые журналы GitHub Actions не использованы как результат внедрения. Автоматические проверки PR оцениваются отдельно после публикации.

Изолированная SQLite: `/tmp/ee-a1-implementation-h0dye9tl/fixture.sqlite3`. Окружение очищено; принудительно заданы `DJANGO_SETTINGS_MODULE=config.settings.test`, `DATABASE_URL` и `TEST_DATABASE_URL` на временный SQLite, `DJANGO_TEST_PROCESSES=4`. Перед миграциями фактические ENGINE/NAME проверены assert. Django/pytest создают собственные тестовые БД. Рабочая база сайта не подключалась.

| Проверка | Точная команда | Exit | Результат |
|---|---|---|---|
| database-guard | `uv run --frozen python manage.py shell -c from django.conf import settings; d=settings.DATABASES['default']; assert d['ENGINE']=='django.db.backends.sqlite3'; assert d['NAME']=='/tmp/ee-a1-implementation-h0dye9tl/fixture.sqlite3'; print(d['ENGINE'], d['NAME'])` | 0 | PASS; 0.444 s |
| compileall | `uv run --frozen python -m compileall -q apps config tests` | 0 | PASS; 0.077 s |
| check | `uv run --frozen python manage.py check` | 0 | PASS; 0.441 s |
| collectstatic | `uv run --frozen python manage.py collectstatic --noinput --verbosity 0` | 0 | PASS; 0.421 s |
| makemigrations | `uv run --frozen python manage.py makemigrations --check --dry-run` | 0 | PASS; 0.486 s |
| migrate | `uv run --frozen python manage.py migrate --noinput -v0` | 0 | PASS; 3.302 s |
| review-contracts | `uv run --frozen python manage.py shell -c from apps.learning.mistake_review import question_bank,COUNT; from apps.learning.understanding import understanding_bank,SKILLS; from apps.drills.retry_guidance import PILOT_SLUGS; b=question_bank(); assert set(b)==set(PILOT_SLUGS); assert all(all(len(c)==COUNT for c in e.values()) for e in b.values()); u=understanding_bank(); assert set(u)==set(PILOT_SLUGS); assert all(set(g['tasks'])==set(SKILLS) for g in u.values()); print(len(b),len(u))` | 0 | PASS; 0.511 s |
| css | `pnpm check:css` | 0 | PASS; 1.283 s |
| js | `pnpm test:ui` | 0 | PASS; 2.415 s |
| audio-readiness | `uv run --frozen python scripts/audio_readiness.py` | 0 | PASS; 0.057 s |
| cefr | `uv run --frozen python scripts/audit_cefr_evidence.py --strict` | 0 | PASS; 0.880 s |
| load-content-final | `uv run --frozen python manage.py load_content` | 0 | PASS; 7.171 s |
| audit-course-final | `uv run --frozen python manage.py audit_course` | 0 | PASS; 8.258 s |
| targeted-final | `uv run --frozen python manage.py test tests.test_a1_editorial_01_04 tests.test_a1_editorial_history tests.test_a1_translation tests.test_progress_safety tests.test_a1_microsteps --noinput` | 0 | PASS; 41.487 s |
| django-full-final | `uv run --frozen python manage.py test tests --parallel auto --noinput` | 0 | PASS; 441.317 s |
| pytest-full-final | `uv run --frozen pytest -q -rfE` | 0 | PASS; 1369.706 s |
| uv-sync | `uv sync --frozen` | 0 | PASS; 0.027 s |
| pnpm-install | `pnpm install --frozen-lockfile --ignore-scripts` | 0 | PASS; 0.855 s |
| fuzz | `uv run --frozen python scripts/qa_evolution.py fuzz --run-number 0 --seed 20261025` | 0 | PASS; 0.673 s |
| mutation | `uv run --frozen python scripts/qa_mutation_probe.py --report docs/audits/a1-01-04-implementation/evidence/mutation-report.md` | 0 | PASS; 3.958 s |

Итог Django:

```text
Ran 818 tests in 431.135s

OK (skipped=2)
```

Итог pytest:

```text
820 passed, 2 skipped, 5015 subtests passed in 1368.33s (0:22:48)
```

Дополнительно выполнены `python docs/audits/a1-01-04-implementation/verify_integrity.py`, синтаксическая компиляция двух воспроизводящих скриптов и `git diff --check` для собственных изменений. Полные входные документы и сырые журналы не форматировались ради lint. HTTP smoke: 4 урока + неделя 2 + история 1 — HTTP 200; диагностические скрытые разборы присутствуют. HTTP не является визуальной проверкой.

## До и после

- Одинаковые SHA256 обоих финальных тестовых модулей сверены. На source8d3a:14tests,18failures,10.988s,exit1. На исправленном дереве:14tests,OK,12.711s (обёртка28.781s),exit0. Файлы targeted-comparable-before/after содержат полные журналы и метаданные. В baseline происходят несовпадения ключей, неверная связь room и отсутствие контекстных карточечных пояснений; R21 отдельно выявляет старую неподготовленную модель.
- Промежуточный полный Django:815tests,FAIL(3),361.927s. Причины: some в раннем accepted, stress_note244>120 и потеря точного термина R01. Все три причины учтены без изменения существующих тестов. Этот прогон предшествует окончательному дереву и не подменяет успешный повтор.
- Промежуточный pytest намеренно остановлен как superseded после обнаруженного сбоя; код завершения обёртки130, полной сводки нет. Он помечен INTERRUPTED_SUPERSEDED, никогда PASS. Полный финальный pytest приведён отдельно.
- Ранние targeted-before(21failures), history-before и диагностические выборки сохранены как промежуточные доказательства. Сравнение итоговой тестовой версии опирается только на identical-SHA comparable logs.

## BLOCKED и ограничения

| Проверка | Статус | Причина |
|---|---|---|
| PostgreSQL | BLOCKED | Нет PostgreSQL server/Docker; SQLite-only результат не выдан за PostgreSQL. |
| Desktop/390px, клавиатура, reduced motion | BLOCKED | Playwright доступен, Chromium отсутствует; штатный install chromium завершился exit1 из-за повреждённого/пустого ZIP. Повторный launch тоже exit1. Полные логи сохранены. CSS/JS/геометрия не менялись. |
| Настоящая озвучка | BLOCKED | 0/33 ожидаемых аудиоманифестов в checkout; записи не прослушаны. Тестовые генерации/фикстуры не являются акустической приёмкой. Это не доказательство отсутствия записей на production. |
| Coverage ratchet | BLOCKED | pytest-cov не входит в lockfile/locked env. Непривязанная дополнительная зависимость uv --with не устанавливалась. Fuzz и4mutation sentinels выполнены отдельно. |
| Повторная содержательная приёмка/реальные ученики | BLOCKED | Здесь внедрение и независимая проверка diff; новой внешней содержательной приёмки и измерения усвоения не было. |

Аудит: ошибок нет, предупреждения сохранены: A1+547/550; повторение A1 в A1+44% против цели70%;1004CEFR-unverified; превышение длины историй1–5 и опережающие слова в старых сочетаниях. Никакие предупреждения/тесты/CI не отключались.
