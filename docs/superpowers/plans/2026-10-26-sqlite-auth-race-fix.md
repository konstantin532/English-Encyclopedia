# Исправление SQLite auth-read race после PR130

Основание: QualityEvolution40381948605, job121780216541 на a7a88e1:1failed,1039passed,2skipped;93%coverage. Ошибка реальная, threshold и тесты не ослаблять. PR130 уже автоматически слит вне этого сеанса; поэтому это отдельное корректирующее задание и один отдельный draftPR. Base main422bea8f31b961bc41c485d3030e29a977123e11, дерево совпадает с проверенным пилотом.

Симптом: `test_legacy_http_transaction_racing_trainer_preserves_queue_and_schedule` получает OperationalError(accounts_user) при разрешении `request.user.is_authenticated` в trainer_state.run_serialized **до** retry loop. Писатель уже держит SQLite user-table lock. Authentication остаётся до atomic, но его transient read failure не попадает в bounded retry. Это проверяемая гипотеза, не готовый результат исправления.

- [ ] Детерминированно воспроизвести раннее lazy-user чтение под реальной блокировкой / доказать точную границу RED.
- [ ] Минимально исправить подтверждённую границу retry, сохранив atomicity, nested transaction policy, ownership/auth/CSRF, anonymous paths и PostgreSQL row locking. Без схемы, зависимостей, UI, контента или алгоритма SRS.
- [ ] Проверить точный failing race под coverage, controlled regression, прочие real races, API atomic/auth/SRS/48h regressions и полный suite с неизменяемыми исходниками.
- [ ] Независимое scoped review; исправить только material findings. Сохранить изолированный worktree/историю.
- [ ] Один draftPR исправления от main, без auto-merge/merge/deploy; подтвердить remote tree/SHA и реальные CI jobs. При невозможности зелёной проверки сообщить FAIL, не выдавать rerun за исправление.

Пользователь уже разрешил реализацию и устранение ошибок CI. Новое окно разрешения требуется для production/рабочих migrations, secrets/permissions/платных действий; их здесь нет. Отдельный PR обусловлен внешним автослиянием исходного PR, а не дублированием реализации.
