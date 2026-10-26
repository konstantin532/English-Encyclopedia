# Пилот практики слов и фраз: проверка и безопасный запуск

Путь: `/learning/vocabulary/`, только после входа. Scope: LX-00055, LX-00285, LX-00084 после урока 5 (`a1-cafe-order`), без изменения порядка уроков и UID. Флаг `EE_VOCABULARY_TRAINER_ENABLED` по умолчанию false. При выключенном флаге ссылки скрыты, прямые trainer endpoints отвечают 404, новые таблицы не читаются. После включения каждый ученик отдельно подтверждает знакомство с уроком и добровольно включает пилот. Это exposure, не проверка усвоения урока.

Мнемоники получили AI-рецензию, но ещё не валидацию преподавателем/носителем или испытание эффективности. Устная часть — «сказал сам → открыл образец → сравнил → самооценка»; запись и автоматическая проверка речи отсутствуют. Письменная альтернатива доступна. Открытая новая ситуация допускает разные полезные ответы и не проверяется на точное совпадение. Исторический статус, новая встреча и показ образца не означают mastery или CEFR.

## Воспроизводимый локальный preview

Зависимости уже должны быть установлены по frozen lockfiles; новые зависимости для пилота не нужны. Команды ниже создают **отдельную disposable SQLite**, не используют `.env` DATABASE_URL для своей БД и не мигрируют пользовательскую базу. Выполнять из корня checkout. Не запускать обычный `manage.py migrate` без явного preview settings.

```bash
export TRAINER_PREVIEW_DIR="$(mktemp -d /tmp/ee-trainer-preview.XXXXXX)"
cat > "$TRAINER_PREVIEW_DIR/vocabulary_preview_settings.py" <<'PY'
from config.settings.test import *
import os
from pathlib import Path
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(Path(os.environ["TRAINER_PREVIEW_DIR"]) / "preview.sqlite3")}}
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
EE_VOCABULARY_TRAINER_ENABLED = True
PY
export PYTHONPATH="$TRAINER_PREVIEW_DIR:$PWD"
uv run python manage.py migrate --settings=vocabulary_preview_settings --noinput
uv run python manage.py load_content --settings=vocabulary_preview_settings
uv run python manage.py shell --settings=vocabulary_preview_settings <<'PY'
from apps.accounts.models import User
from django.test import Client
import json, os
from pathlib import Path
cookies = []
for number in (1, 2):
    user = User.objects.create_user(email=f'trainer-preview-{number}@example.test', password='preview-only-local')
    client = Client(); client.force_login(user)
    cookies.append({'user_id': user.pk, 'cookie': client.cookies['sessionid'].value})
Path(os.environ['TRAINER_PREVIEW_DIR'], 'preview_users.json').write_text(json.dumps(cookies))
PY
pnpm build:css
uv run python manage.py runserver 127.0.0.1:8765 --noreload --settings=vocabulary_preview_settings
```

Открыть `http://127.0.0.1:8765/learning/vocabulary/`, войти preview email/password выше. Локальные cookies используются только для изолированной QA-учётки; не коммитить их или БД. Для flag-off preview заменить значение на False в отдельном preview settings и перезапустить сервер. Сайт не публикуется. После проверки остановить сервер и удалить временный preview каталог; перед удалением проверить путь.

## Автоматизация браузера

`scripts/verify_vocabulary_trainer.cjs` не создаёт БД, пользователей или сервер. Он экспортирует `verify(context, {baseURL, outputDir, otherContext, noJS: true})`. `context` — уже авторизованный Playwright BrowserContext **нового** disposable пользователя, `otherContext` — контекст другого preview пользователя. Обеим учёткам нужны разные cookies. Для проверок повторного запуска создать новые disposable учётки: сценарий расходует встречи/попытки, второй запуск не является reset истории.

Минимальная точка запуска после подготовки сервера (Playwright из существующего runtime, браузер/root fixture предоставляет проверяющий):

```js
const { verify } = require('./scripts/verify_vocabulary_trainer.cjs');
const result = await verify(context, {
  baseURL: 'http://127.0.0.1:8765',
  outputDir: '/tmp/ee-trainer-browser',
  otherContext,
});
console.log(JSON.stringify(result, null, 2));
```

Скрипт возвращает `checks`, пути `screenshots`, отдельный `manualVisual: NOT_RUN`. Исключение означает FAIL; оно не превращается в PASS. При отсутствии otherContext ownership помечается NOT_RUN (его отдельно проверяет HTTP suite). Скрипт закрывает собственные pages и дополнительный no-JS context, но не контексты caller. Для ручного осмотра открыть отдельную page caller.

Селекторы: `[data-vocabulary-trainer]` — текущая безопасная server projection; `data-phase`, `data-session`, `data-revision`, `data-status-url` — только transport/state metadata. `#trainer-answer`, `#trainer-mnemonic` (только `[data-note-editor]`), `button[name=action][value=…]`, `input[name=self_rating]`, `[data-trainer-status]`, `[data-trainer-network]`, `[data-trainer-retry]`, `[data-trainer-reconcile]`; guarded входы помечены `[data-trainer-entry]`. Action/session POST проходят CSRF и PRG; status — `/learning/vocabulary/<id>/status/`, только owner, no-store. Модель, title с ответом, mnemonic и примеры не кладутся в скрытые поля/JSON до разрешённой серверной фазы.

Реальный browser scenario: три полных начальных встречи; открытие/исчезновение материала; мнемоника с HTML-подобным текстом; потеря ответа **после принятого POST** и точный retry token/payload; back после урока со sticky assistance; неизвестный письменный ответ; устная самооценка; application с несколькими примерами и сохранением своего текста; 320/390/desktop, 200% text, 48px controls, overflow, Tab/focus/reduced-motion; другой owner; дополнительная обычная форма без JS. Смена времени для due/DST/24h остаётся в серверных тестах, не через browser clock. Double-submit lock/timeout/stale revalidation дополнительно проверяются Node VM; это не доказательство layout.

## Команды и границы доказательств

```bash
uv run python manage.py test tests.test_vocabulary_trainer_views tests.test_vocabulary_trainer_service --settings=config.settings.test --noinput
pnpm check:css
pnpm test:ui
```

Завершённые проверки и их границы перечислены в итоговом разделе ниже. Full suite выполнялся только в disposable test DB; на существующей пользовательской БД не выполнять migrations/load_content ради QA.

Ручная проверка: читаемость текста и опор, клавиатура Tab/Shift+Tab/Enter/Space, видимость фокуса, скринридерные labels/live state, 320/390/desktop и 200% текста без потери кнопок, reduced motion, обновление/back/два окна/повтор отправки, отключённый JS. Автоматические bounding boxes не заменяют оценку удобства человеком. При потере подтверждения письменный текст остаётся на странице, повтор отправляет прежний token/revision/payload, «Проверить состояние» запрашивает owner canonical state. Конфликт показывает актуальную фазу и отдельно неподтверждённый текст; он не считается ошибкой ученика. Браузерное закрытие/перезагрузка до подтверждённого save может потерять только несохранённый локальный ввод: долговременного клиентского хранилища текста нет. Для паузы использовать «Сохранить черновик» и дождаться подтверждения. Для очистки уже сохранённого текста использовать явный пустой save_draft; старые callers помощи без answer не стирают существующий draft. «Моя ассоциация» редактируется отдельно: кнопка в форме задания сначала явно сохраняет текущий черновик (включая очистку), затем открывает единственное поле заметки. Само открытие или сохранение заметки не оценивает ответ. До запроса мнемоники на unaided recall этот редактор и личный текст недоступны; зарегистрированная помощь остаётся sticky. При восстановлении сохраняются отредактированные поля, включая пустую заметку, без автоматической отправки; при смене серверной фазы текст остаётся отдельным полем для копирования.

## Rollout, backup, restore и rollback

1. Зафиксировать код/lockfiles/content version и schema head, выключить флаг. До любой миграции сделать защищённую согласованную копию **всей** БД, включая accounts, UnitProgress, IndependentAttempt, trainer enrollment/session/mnemonics и migration history, плюс соответствующий manifest JSON/код. Не собирать backup только новых таблиц: ссылки и lexical schedule общие. PostgreSQL — согласованный `pg_dump` существующим проверенным deploy-процессом; SQLite — штатный backup API или остановленные writers, не копия живого файла с открытым WAL. Не публиковать backups/приватные snapshots.
2. Восстановить копию в отдельное disposable окружение, проверить версии/schema, counts/связи/историю и account A/B isolation, пройти migration 0012→0013, export/delete и concurrent writes на целевой СУБД. Сохранить результат restore drill до допуска. SQLite green не доказывает PostgreSQL locking. Не использовать обратную data-dropping migration как обычный rollback.
3. После отдельного разрешения ответственного оператора развернуть additive schema `learning.0013_vocabulary_trainer` и совместимый код с флагом false. В этой задаче working/production migrations не выполняются. Проверить, что flag-off не трогает новые таблицы, обычные уроки/повторение/экспорт работают.
4. Включить флаг на ограниченном добровольном пилоте; каждый включает enrollment сам. Следить за 4xx/409/429/5xx без логирования answer/mnemonic/token; конфликт не считать ученической ошибкой. Проверить ежедневный бюджет, timezone и 24h elapsed threshold, совместную ownership расписания при legacy check. Изначально 24h, далее 1/3/7/14 суток, максимум две recall попытки. Не обещать немедленного роста навыка.
5. Быстрый rollback: выключить флаг и перезапустить workers. Свежие ссылки исчезнут; уже открытая форма получит unavailable без перезаписи истории/расписания. Оставить новые таблицы/данные и использовать совместимый код. Для возврата старой версии использовать только commit, совместимый с additive schema; не откатывать произвольно модельные поля, которые уже сохранены. Повторное enrollment возобновляет сохранённую историю.
6. Disaster restore — отдельная операция после остановки writers, согласования точки восстановления и проверки копии в изолированном окружении. Восстановить всю БД и соответствующий код/content, флаг false, проверить IDs/FK/attempts/status/due/private data, затем отдельно разрешить доступ. Восстановление старой копии теряет подтверждённые записи после snapshot: это должно быть явно согласовано, не скрыто под feature rollback. Сохранять совместимость с ещё активными копиями/политику удаления при restore.

## Версии контента и приватные данные

`content/manifests/a1_vocabulary_trainer.json`: `content_version`, `assessment_revision`, `compatibility[version]`, `compatible_with`, `task_mapping`, `history_policy: preserve`. Cosmetic правка сохраняет assessment_revision и task/family identity, явно описывает совместимость; проверяется frozen snapshot незавершённых встреч. Смысл/accepted/ошибка/ситуация/rubric/family меняется — новая assessment_revision и явная mapping старых task_id к новым либо null при отсутствии соответствия. Даже ненулевая mapping не даёт перенести учебное свидетельство в новую revision: требуется новое знакомство/baseline; historical attempts не переклассифицируются, stage и будущий срок не сбрасываются. Перед rollout проверить отличие family для delayed credit и новую baseline встречу; не менять старые receipts/snapshots. Описать причины в reviewer-visible change log и повторить content/service tests.

Черновик: максимум 400 символов, 30 дней с последнего сохранения. Private mnemonic: максимум 300 символов, обычный escaped plain text, только owner. Команда `expire_trainer_drafts` удаляет лишь старые неподтверждённые drafts; расписание задания cron здесь не создаётся. Оператор отдельно добавляет ежедневный запуск в существующий scheduler с правильными settings и проверяет число удалённых; нужен контроль сбоев и темпа очистки. Confirmed attempts/history и mnemonics команда не удаляет. Backup retention задаётся существующей операторской политикой, отдельно от live 30-day draft expiry; не обещать моментальное физическое удаление всех резервных копий.

«Скачать мои данные» ведёт в `/accounts/my-data/`: собственные submissions/draft/state/mnemonics экспортируются; скрытые модели незавершённых assessment, frozen snapshot и transport receipts не выдаются как обход проверки. Удаление аккаунта `/accounts/delete/` удаляет owner trainer-данные каскадно, не чужие. Export/delete требуют существующих auth/CSRF flows. Opt-out сохраняет историю и отличается от удаления аккаунта. Помощь через зарегистрированные legacy model API, выбранные word pages, week3, lesson GET и реально показанные selected progress units dashboard sticky; legacy review не показывает будущий pilot model. Материалы на других маршрутах, внешние страницы/переводчик/incognito не доказываются отсутствующими и могут повлиять на результат.

## Добровольное испытание с людьми: заранее заданный протокол

До набора показать понятное согласие, возможность прекратить без штрафа, отсутствие записи речи и границы приватности. Отдельно привлечь преподавателя/носителя для естественности AmE, соответствия смысла, рисков мнемоник и приемлемых альтернатив. AI-рецензия этот этап не заменяет. Для первичной UX-проверки пригласить небольшую добровольную группу (например 6–10), включив keyboard/крупный текст; это exploratory sample, не efficacy trial.

До старта зафиксировать исходные задания, рубрику и окно 48h/7d в протоколе; не менять их после просмотра результатов. День 0: знакомство с уроком 5 и тремя единицами, самостоятельный initial recall, перенос и spoken self-report отдельно; записать только согласованные данные, модель/подсказку пометить как помощь. Через **48 часов** и **7 дней** после знакомства предложить ещё не показанные семантически соответствующие ситуации (семейства/тексты пробы утвердить заранее, не копировать немедленный recall). Если последний показ материала был менее 24h назад, пробу пометить assisted/recent exposure и перенести либо анализировать отдельно. Сам schedule ladder не заменяет 48h/7d исследовательские встречи. Две authored recall families пилота не обеспечивают бесконечную новизну: внешняя человеческая проба на 7d должна иметь заранее утверждённую новую ситуацию и не мигрировать automatic grading/rubric без новой revision.

Предзаданные наблюдения: смог ли участник найти продолжение; не потерялся ли свой ответ при помощи/сбое/back; смог ли исправить неизвестный ответ без ложного «неверно»; достиг ли смысловой цели в новой ситуации; использовал ли target самостоятельно; сумел ли объяснить различие self-report и машинной проверки; частота запросов помощи и корректный интервал с последнего материала. Успех смысловой цели и target usage оценивать раздельно двумя согласованными людьми по rubric, разногласия фиксировать; речь оценивать человеком только с отдельным согласием и без незаявленной записи. Предварительные критерии продолжения: 0 воспроизведённых потерь подтверждённых ответов/чужих данных; все критические контролы доступны keyboard/200%; отсутствие систематических ложных exact-error для valid alternatives; большинство участников проходят маршрут без помощи исследователя. При нарушении остановить расширение и исправить причину.

Отчёт разделяет HTTP/Node/browser/manual/людей; numerator/denominator, assistance/recent exposure и пропуски приводятся явно. Малый добровольный sample, отсутствие рандомизации/контроля и self-report не позволяют приписать рост тренажёру, доказать долговременное владение, CEFR или пользу каждой мнемоники. Для причинного вывода понадобится отдельное заранее спланированное сравнительное исследование.

## Итог проверки реализации, 2026-10-26

Проверен код `dc9a282b516cbf11dd9d89ec2d6547a5d12954bb` от согласованного main `fbec5724b67b9caf7045fa3a4da386607eedb759`. Ветка `feat/vocabulary-phrase-pilot`, отдельный worktree. PR129 проверен как merged; удалённый переключатель глубины не возвращён. Рабочая копия основного checkout и чужие изменения сохранены. Python3.13.16, Django5.2.18, Node24.22.1; lockfiles не менялись. Флаг остаётся выключенным, production/рабочие БД не открывались и не мигрировались.

| Проверка | Фактический результат |
|---|---|
| `DJANGO_TEST_PROCESSES=4 uv run python manage.py test tests --parallel auto --settings=config.settings.test --noinput` | **PASS**: 1038 тестов, 327.355s, 0 ошибок, 2 пропуска PostgreSQL-only RLS в SQLite; exit0 |
| Scoped final service/HTTP/content | **PASS**: 73; 4 новые регрессии сначала RED, затем GREEN |
| `pnpm test:ui` | **PASS**: 152/152, 0 пропусков |
| `pnpm check:css` | **PASS**: 21 stylesheet; generated CSS соответствует SCSS |
| `manage.py check`; `makemigrations --check --dry-run`; compileall; `git diff --check` | **PASS**; несохранённых migrations нет |
| Disposable in-memory migrate→load_content→audit_course | **PASS**, «Ошибок нет»; 1047 LX, 60 уроков, 11 историй, 7 стихов, 30 недель |
| `scripts/audit_cefr_evidence.py --strict` | **PASS**; unresolved evidence items 0, не новая сертификация CEFR |
| Реальные отдельные DB connections / threaded SQLite races и0012→0013 preservation | **PASS** в полном suite: duplicate, reveal/submit, budget/start, legacyHTTP/trainer, cleanup/writer; old attempt/progress сохранены |
| Official Playwright + Chromium153.0.8010.0 | **PASS**: 40/40 проверок на финальном коде; три полных начальных встречи, private escaping, скрытые targets, lost accepted response + точный retry, back/sticky help, unknown, spoken self-report, changed application, другой owner404, no-JSPOST/PRG/draft/note/clear, keyboard, reduced-motion |
| Layout/text resize | **PASS**: 320/390/1280 px при 100%/200%; computed шрифт действительно удвоен; fullpage overflow и границы всех controls проверены, без скрытия overflow |
| Controlled delayed browser + DB readback | **PASS**: отдельный fakeuser, initial service fixture 26h назад→due browser recall в другой family→новая application→complete; stage 0→1, `schedule_eligible=true`, `delayed_correct`, assistance после recall не отменяет evidence |
| Ручной визуальный осмотр | **PASS** в Chromium: desktop 100%, 320/390/1280 text 200%, шапка, читаемость задания/примеров, переносы и controls, сообщение о ранее подтверждённом recall; PNG просмотрены отдельно от автоматического verifier |
| Контраст основных новых цветов | Расчёт относительной яркости: white/green 7.54:1, green/cream 7.42:1, input text/white 13.08:1, focus/cream 5.96:1; это не полный WCAG-аудит сайта |
| PostgreSQL16 | Локально **BLOCKED**: сервера нет. Реальный итог job `postgres` проверяется в CI draftPR; SQLite не подменяет этот результат |

Actual CI и окончательный remote SHA фиксируются в описании draftPR и финальном сообщении после публикации. Коммит с этим отчётом добавляет документацию к проверенному коду; CI проверяет итоговую удалённую ревизию. До зелёного PostgreSQL job не считать DB gate завершённым. Ничего не слито, auto-merge не включён, сайт не развёрнут.

Полный suite на83089a0 до finalfix также прошёл 1034 теста за 342.525s, skip 2. Более ранние broad runs, прерванные или завершившиеся с ошибкой при изменении исходников, **не** являются PASS и не используются вместо финального 1038-run. Последние прогоны выполнялись с неизменяемыми исходниками; проверки не ослаблялись.

### Исправления после независимого ревью

Per-task review и whole-branch review выполнены разными агентами. Материальные замечания закрыты, scoped re-review: Spec PASS / Quality Approved, остаточных Critical/Important нет. Исправлены утечки скрытых моделей через незавершённый export, sticky помощь из истории, ложный recognition после ошибки/самооценки, потеря черновика/ассоциации при обычном POST и400/409 recovery, DOM `form.action` clobber, mobile flex overflow и шапка при200%. Финальная волна отдельно исправила противоречивое объяснение поздней application-помощи и отображение срока в IANA timezone (Moscow, обе стороны spring DST и оба fall hours). Исходная recall evidence и весь UnitProgress проверены неизменными после application help/completion.

### Quality gates и границы

| Gate | Статус и основание |
|---|---|
| Correctness | **PASS**:finalservice/HTTP/fullsuite + реальный полный путь |
| Regression | **PASS** локально: 1038 Django / 152 Node; legacy SRS/48hMistakeReview/auth/data-rights в suite; окончательный CI см.PR |
| Security | **PASS** в testedscope:owner/CSRF/escaping/export/delete/privileged server state; нет голоса/внешних API |
| Data Integrity | **PASS SQLite**, включая настоящие races/rollback/migration; PostgreSQL требует отдельного CI PASS |
| UX | **PASS** в Chromium/normalPOST/keyboard/text200/manual PNG; human usability test ещё не проводился |
| Integration | **PASS**:один UnitProgress/journal, guardedexistinglinks, flagoff, история/версии сохранены |
| Evidence | **PASS** отчётности:help/self-report/uncertain не названы verified retention; реальные границы указаны |

Существующие общекурсовые audit warnings сохранены: 1004 unverified CEFR, A1→A1+recycling 221/500 (44%) при цели 70%, 3 forward collocations. Это отдельный долг курса, не новый результат пилота. Firefox/Safari, ручной screen reader, production restore rehearsal и добровольное исследование48h/7d **не выполнены**. AI-рецензия содержания не заменяет преподавателя/носителя. Simulated 26h и scripted spoken choice не доказывают память или реальное произношение человека. Аудио нет; text alternative и self-directed speaking работают без него.

### Принятые решения и цена компромисса

В порядке решений журнала:

1. Продолжить утверждённую разработку без повторного запроса того же разрешения; merge/productionmigration остаются отдельными. Цена ошибки — выход за согласованный scope; scope здесь не расширен.
2. Использовать существующие frozen Python/Node зависимости в изолированном окружении. Цена — локальное место и время установки; manifests не изменены.
3. Перенести повтор broad Task1 на неизменяемый финальный integrationrun после уточнения manifest. Цена — более позднее обнаружение регрессии; окончательный 1038-run выполнен и заменяет ранние неполные доказательства.
4. Сохранить локальную историю/worktree и передавать точные trees через GitHub connector с expectedSHA, потому что CLIpush не имел credentials. Цена — локальные/remote commitSHA различаются; каждый tree сравнен, force/перезапись истории не использованы. Для новой работы безопаснее свежий checkout удалённой ветки; старый worktree сохранён.
5. Разрешить узкую редакцию server-private полей export. Цена — будущие модели незавершённой assessment не выдаются до завершения; свои ответы/evidence/история остаются.
6. Обернуть legacyAPI целиком в общий atomic/serialized retry. Цена — сериализация операций одного пользователя; зато attempt/progress/48hqueue не расходятся при SQLite retry.
7. При новой assessmentrevision даже с mapping требовать новую baseline-встречу, сохраняя историю/stage/futuredue. Цена — одна дополнительная практика; cosmetic same-revision continuity сохраняется.
8. Ранняя добровольная ошибка сохраняет stage/due, но записывается честно. Цена — без немедленного штрафа за необязательную раннюю практику; due encounter обрабатывается обычными правилами.
9. Регистрировать доставку выбранных существующих учебных материалов как помощь/exposure, не как grade. Цена — дополнительная серверная запись; внешняя/incognito и неинструментированная помощь остаётся ненаблюдаемой.
10. Редактировать личную ассоциацию отдельно после явного atomic сохранения текущего draft, включая очистку. Старые operation fingerprints сохранены; новый save_note имеет свой payload. Цена — один необязательный переход, который сохраняет текст и работает без JS.

### Изменённые файлы

Полный список относительно согласованного base (включая документацию):

- `README.md`
- `apps/accounts/data_rights.py`
- `apps/api/views.py`
- `apps/core/context_processors.py`
- `apps/curriculum/views.py`
- `apps/learning/evidence.py`
- `apps/learning/management/commands/expire_trainer_drafts.py`
- `apps/learning/migrations/0013_vocabulary_trainer.py`
- `apps/learning/models.py`
- `apps/learning/services.py`
- `apps/learning/trainer_content.py`
- `apps/learning/trainer_scheduling.py`
- `apps/learning/trainer_service.py`
- `apps/learning/trainer_state.py`
- `apps/learning/trainer_views.py`
- `apps/learning/urls.py`
- `apps/learning/views.py`
- `apps/lessons/views.py`
- `apps/lexicon/views.py`
- `config/settings/base.py`
- `content/manifests/a1_vocabulary_trainer.json`
- `docs/qa/vocabulary-phrase-trainer-checkpoint.md`
- `docs/qa/vocabulary-phrase-trainer.md`
- `docs/superpowers/plans/2026-10-26-vocabulary-phrase-trainer.md`
- `docs/superpowers/specs/2026-10-26-vocabulary-phrase-trainer-design.md`
- `scripts/verify_vocabulary_trainer.cjs`
- `static/css/vocabulary-trainer.css`
- `static/js/vocabulary-trainer.js`
- `static/scss/vocabulary-trainer.scss`
- `templates/curriculum/week.html`
- `templates/learning/dashboard.html`
- `templates/learning/review.html`
- `templates/learning/trainer.html`
- `templates/lexicon/detail.html`
- `tests/js/vocabulary-trainer.test.cjs`
- `tests/test_vocabulary_trainer_concurrency.py`
- `tests/test_vocabulary_trainer_content.py`
- `tests/test_vocabulary_trainer_service.py`
- `tests/test_vocabulary_trainer_views.py`
