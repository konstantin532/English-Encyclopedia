"""Regenerate preparation documentation from actual local evidence, not CI claims."""
import json
from pathlib import Path
import shlex
import re

P = Path(__file__).resolve().parent
results = json.loads((P / 'evidence/local/RESULTS.json').read_text())
qa = json.loads((P / 'evidence/local/QA_RESULTS.json').read_text())
runtime = json.loads((P / 'evidence/local/runtime-smoke.json').read_text())
validation = json.loads((P / 'extracts/PACKET_VALIDATION.json').read_text())
db = results['database']['path']

checks = ['# CHECKS — новые запуски и прежний CI отдельно', '',
          'Исходный учебный snapshot: `' + results['source_commit'] + '`.', '',
          'Ни production, ни удалённая база сайта не использовались. Новая SQLite: `' + db + '`.',
          'Все Python-команды нового baseline выполнялись с явными `DJANGO_SETTINGS_MODULE=config.settings.test`,',
          '`DATABASE_URL=sqlite:///' + db + '`, `TEST_DATABASE_URL=sqlite:///' + db + '`,',
          '`DJANGO_TEST_PROCESSES=4` и локальными allowed hosts. Фактический engine/path проверены до миграций.',
          'В тестовых runner Django/pytest создаются дополнительные тестовые SQLite; это не рабочая база сайта.', '',
          'Полные stdout/stderr, без сокращения: указанные `.log`; argv, exit codes, время и длительность: `evidence/local/RESULTS.json`.', '',
          '## Новые локальные команды', '',
          '| Проверка | Команда (при указанном выше окружении) | Статус | Exit | Секунды |',
          '|---|---|---|---:|---:|']
for c in results['checks']:
    cmd = shlex.join(c['argv']).replace('|', '\\|')
    checks.append(f"| {c['name']} | `{cmd}` | {c['status']} | {c.get('exit_code', '—')} | {c.get('duration_seconds', '—')} |")
summary_lines = []
for logname in ['django-full.log','pytest-full-retry.log']:
    logfile = P/'evidence/local'/logname
    if logfile.exists():
        summary_lines += [f'`{logname}`: '+line for line in logfile.read_text().splitlines()
                          if re.match(r'Ran \d+ tests in ',line) or line.startswith('OK (')
                          or (re.search(r'\d+ passed',line) and 'subtests' in line)]
checks += ['', '### Новые итоговые строки runner', '', *summary_lines, '']
checks += ['', '### Дополнительная проверка связанных поверхностей', '',
           '`build_packet.py` → `extracts/PACKET_VALIDATION.json`: ' + validation['status'] + ', ' + str(validation['full_snapshots_verified']) + ' полных файлов, ' + str(validation['snapshot_total_bytes']) + ' байт; SHA/размеры и сохранение всех исходных полей проверены. Это не оценка учебного языка.', '',
           'Точная runtime-команда после создания marker `REVIEW_DATABASE_ONLY` со SHA snapshot в каталоге тестовой БД:', '',
           '```bash',
           "env -u DATABASE_URL DJANGO_SETTINGS_MODULE=config.settings.test TEST_DATABASE_URL='sqlite:///" + db + "' DJANGO_ALLOWED_HOSTS='testserver,localhost,127.0.0.1' .venv/bin/python docs/review-preparation/a1-01-04/runtime_smoke.py --database '" + db + "'",
           '```', '',
           f"Exit 0; {runtime['status']}; {runtime['assertions']} assertions; temporary_rows_rolled_back={runtime['temporary_rows_rolled_back']}. Полный JSON: `evidence/local/runtime-smoke.json`, stderr: `runtime-smoke.stderr.log`.",
           'Проверены все явно записанные answer/accepted для 21 упражнения и 16 переводов; sentinel mismatch не является набором всех возможных грамматических ошибок. HTTP-клиент не заменяет визуальную приёмку.', '',
           '| QA-команда | Результат | Exit |', '|---|---|---:|']
for c in qa:
    checks.append('| `' + shlex.join(c['argv']) + '` | ' + c['status'] + ' | ' + str(c['exit_code']) + ' |')
checks += ['', 'Fuzz: 64 случая, seed=20261025, regular minimum budget. Mutation sentinels: 4/4 намеренно сломанных варианта обнаружены в одноразовой копии. Ни один из этих результатов не является полным mutation score.', '',
           '## Смысл зелёных диагностик', '',
           '- CSS: 17 stylesheet; JavaScript: 122 tests, 122 pass, 0 fail.',
           '- `audit_course`: ошибок нет, но A1+ = 547/550, повторение A1 в A1+=44% при цели 70%, 1004 единицы с неподтверждённым CEFR, предупреждения о длине историй 1–5 и опережающих collocations. Это не новые доказанные грамматические ошибки и не разрешение менять контент в этой подготовке.',
           '- `audit_cefr_evidence.py --strict` проверяет согласованность записанных свидетельств. Его PASS не означает независимую проверку CEFR всех слов. В A1 457 записей остаются `cefr_unverified`.',
           '- `audio_readiness.py` завершился с exit 0, но обнаружил **0/33** ожидаемых manifest. Это диагностический PASS команды; реальное прослушивание/сверка отсутствующего аудио **BLOCKED**.',
           '- Числа Django unittest и pytest могут различаться из-за правил discovery. Используйте итоги каждого журнала, не переносите число одного runner в другой.', '',
           '## Повторный полный pytest', '', 'Первый pytest-full оборвался без итоговой сводки и без полученного exit code. Процесс больше не работал; причина не установлена. Оригинальный частичный pytest-full.log сохранён, запись имеет BLOCKED. Повторный полный запуск выполняется отдельно и имеет собственный pytest-full-retry.log и строку результатов; его исход не переносится на первый запуск.', '', '## Согласованность выбранных материалов с runtime', '', 'Дополнительный read-only runtime_data_consistency.py выполнен на той же отмеченной изолированной SQLite, exit 0. Все 105 raw-карточек совпали с фактически собранным question_bank, четыре compiled guide совпали с основными объяснениями+scaffold, четыре active topic — с диалогом+repair+missions+twists. Загруженные ключи, accepted, подсказки, объяснения и review_of для всех 21 основного и 16 переводов совпали с выборками. Полный результат: evidence/local/runtime-data-consistency.json. Это проверка выбора и сборки источников, не языка.', '', '## Исторические GitHub Actions — не новые запуски', '',
           'Run `40111428333` на том же SHA повторно прочитан через GitHub API. Обе jobs completed/success. Полные журналы: `evidence/historical-sqlite.log`, `evidence/historical-postgres.log`.',
           '- SQLite CI: 806 passed, 2 skipped, 4948 subtests passed, 1061.00s.',
           '- PostgreSQL CI: 808 passed, 4948 subtests passed, 845.70s. Этот ранее непрочитанный журнал теперь получен; это всё равно исторический, не новый локальный PostgreSQL прогон.',
           '- Действующий CI/Quality Evolution на source SHA зелёный в ранее выполненных workflow. Deploy только прочитан как метаданные; в этой работе не запускался.', '',
           '## BLOCKED и не выполнявшееся', '',
           '- Новый PostgreSQL: серверные binaries PostgreSQL и Docker отсутствуют в окружении; тестируется локальный SQLite. Нельзя выдавать исторический postgres job за новый запуск.',
           '- Browser desktop/390px, keyboard, reduced motion: Playwright1.62.1 доступен, Chromium executable отсутствует. Штатная `playwright install chromium` завершилась exit1 (скачанный ZIP 0 MiB/обрезан, End of central directory record signature not found). `evidence/local/browser-launch.log` содержит отдельную полную диагностику отсутствующего executable; полный console-log неудачной загрузки не сохранён и не представлен как полный.',
           '- Coverage ratchet из отдельного Quality Evolution: `pytest-cov` отсутствует в lockfile/locked venv. Чтобы не добавлять неприкреплённую зависимость командой CI `--with pytest-cov`, новый coverage-report/ratchet не запускался. Fuzz и mutation этого workflow выполнены отдельно; весь Quality Evolution заново пройденным не называется.',
           '- Реальное аудио/голоса ОС и качество произношения не проверены. Отсутствие assets в checkout не доказывает отсутствие на рабочем сайте.',
           '- GPT-6 Pro / независимая языковая рецензия не запускались. Статус NOT_REVIEWED, а не VERIFIED.', '',
           'Версии среды: `evidence/local/ENVIRONMENT.json`. Lockfile hashes before/after: `RESULTS.json`. Исполняемый baseline helper: `run_baseline.py`; не запускайте команды из CI в случайно унаследованном production-окружении.', '']
(P / 'CHECKS.md').write_text('\n'.join(checks), encoding='utf-8')

pending = [c['name'] for c in results['checks'] if c['status'] == 'RUNNING']
failed = [c['name'] for c in results['checks'] if c['status'] == 'FAIL']
status = ['# STATUS — подготовка A1 1–4', '',
          '**Текстовый пакет: READY_FOR_REVIEW. Содержательная редактура: NOT_REVIEWED.**', '',
          'Источник: `8d3a41d9aa61cbf074caff602d53b22920ca3efa`; отдельная ветка `prepare/a1-01-04-review-20261025`. Начальный checkout main чистый; SHA сверён с GitHub. Перехода на старый коммит/отката нет.',
          'Открытые PR на начало: #110 (A1, уроки 9–12) и #115 (изоляция пилота); не применялись и не перезаписывались. Другой подготовки этой группы в ветках/документах репозитория не найдено.', '',
          '## Что завершено', '',
          '| Область | Статус | Доказательство |', '|---|---|---|',
          '| Три переданных документа | PASS полного получения | inputs/; 52/593/93 строки; 4818/49135/9172 байта |',
          '| Соответствие трёх YAML старого пакета текущему SHA | PASS | extracts/HISTORICAL_SOURCE_COMPARISON.json; кодовый блок восстановлен с конечным LF |',
          '| Инвентарь курса | PASS структуры | COURSE_MAP.json: 28 уроков A1 и 32 урока A1+; подробные связи только четырёх уроков |',
          f"| Исходники A1 1–4 и связанные записи | PASS полноты/целостности | {validation['full_snapshots_verified']} полных файла, {validation['snapshot_total_bytes']} байт; SOURCE_MANIFEST.json |",
          '| Поля/задания/словари | PASS полноты | 21 основное, 16 переводов, 105 отложенных карточек, 24 устные миссии, 8 поворотов, 74 словарные записи |',
          '| Неразрешённые явные LX/запрошенные source paths | PASS | Пустые списки в extracts/PACKET_VALIDATION.json |',
          '| Фактические URL/обработчики/нормализаторы | PASS трассировки | RUNTIME_LINKS.md, snapshot/ |',
          '| Зависимости по lockfile | PASS | uv sync --frozen; pnpm frozen; версии lock не менялись |',
          '| Миграции/загрузка/аудит | PASS команды | Только новая изолированная SQLite; полные evidence/local/*.log |',
          f"| Поверхности четырёх уроков/API | PASS ограниченного прогона | {runtime['assertions']} assertions; временные записи откатились; это не browser и не языковая рецензия |",
          '| Новые полные тесты | См. CHECKS.md | Два runner отдельно; не переносить результаты старого CI |',
          '| Визуальная и аудиоприёмка | BLOCKED | Chromium недоступен; аудио 0/33 manifest; подробнее CHECKS.md |',
          '| Новая проверка PostgreSQL/coverage ratchet | BLOCKED | Нет локального PG/Docker; pytest-cov не входит в locked env |',
          '| Язык/ясность/американское употребление | NOT_REVIEWED | Следующий шаг — рецензия подготовленного пакета в Pro |', '',
          '## Границы результата', '',
          'Учебные YAML/JSON, приложения, apps/accounts, авторизация, стабильные ID, маркеры/цвета, геометрия и миграционные файлы **не менялись**. SQLite создавалась только для проверок. Deploy, force push, merge в main не выполнялись.',
          'Пакет не подтверждает отсутствие грамматических ошибок, реальный успех ученика или качество произношения. Остальные 56 уроков имеют INVENTORY_ONLY/NOT_REVIEWED; это не завершённый аудит A1/A1+.',
          'Старые COURSE_MAP/MISSING_INPUTS/архив отдельно не получены; их отсутствие компенсировано новой сборкой из pinned Git, но они не объявлены прочитанными.',
          'Начните рецензию с REVIEW_PACKET.md и полных extract/snapshot-файлов. Подготовка завершает передачу исходников; массовых замен учебного текста нет.', '']
if pending:
    status += ['**Выполняется:** ' + ', '.join(pending) + '. Этот пункт пока не PASS.', '']
if failed:
    status += ['**Новые FAIL:** ' + ', '.join(failed) + '. Смотрите полные журналы.', '']
(P / 'STATUS.md').write_text('\n'.join(status), encoding='utf-8')
missing = {
    'source_commit': results['source_commit'], 'text_packet_complete': True,
    'missing_requested_source_paths': validation['missing_requested_source_paths'],
    'unresolved_explicit_uid_refs': validation['unresolved_explicit_uid_refs'],
    'not_provided_old_companions': ['old COURSE_MAP.json','old MISSING_INPUTS.json','old SOURCE_MANIFEST.json','old archive'],
    'replacement': 'New maps/snapshots regenerated from Git; old companion files not claimed received',
    'blocked': [
        {'check':'freshPostgreSQL','reason':'No PostgreSQL server binaries or Docker available'},
        {'check':'visualDesktop390KeyboardReducedMotion','reason':'Chromium unavailable; official download failed'},
        {'check':'realAudioPronunciation','reason':'Expected audio assets not in checkout;no real listening/OSvoice check'},
        {'check':'freshCoverageRatchet','reason':'pytest-cov not in locked environment; no unpinned dependency installed'},
    ],
    'interrupted_runs':[{'name':c['name'],'reason':c.get('reason'),'exit_code':c.get('exit_code')} for c in results['checks'] if c['status']=='BLOCKED'],
    'not_reviewed':['GPT-6 Pro editorial review','learner comprehension','other 56 lessons'],
}
(P / 'MISSING_INPUTS.json').write_text(json.dumps(missing, ensure_ascii=False, indent=2)+'\n')
print('STATUS/CHECKS/MISSING_INPUTS written; pending:', pending, 'fail:', failed)
