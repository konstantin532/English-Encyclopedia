# Роль базы данных с минимальными правами

Сейчас сайт может подключаться к Supabase владельцем таблиц (`postgres`). Если пароль из
`DATABASE_URL` украдут, злоумышленник сможет удалить таблицы. Отдельная роль `ee_app` умеет
только читать и писать строки: таблицы ей не удалить и не изменить.

## Один раз: создать роль (Supabase → SQL Editor)

```sql
create role ee_app login password 'ДЛИННЫЙ-СЛУЧАЙНЫЙ-ПАРОЛЬ';
-- Защита от зависших и тяжёлых запросов: один запрос не повесит сайт.
alter role ee_app set statement_timeout = '15s';
alter role ee_app set idle_in_transaction_session_timeout = '30s';
-- Новые таблицы из будущих миграций сразу получают права на данные.
alter default privileges in schema public grant select, insert, update, delete on tables to ee_app;
alter default privileges in schema public grant usage, select on sequences to ee_app;
```

## Миграции — владельцем, сайт — ролью ee_app

1. Миграции запускайте строкой подключения владельца и с именем роли сайта:
   ```powershell
   $env:DATABASE_URL="<строка владельца postgres>"; $env:APP_DB_ROLE="ee_app"; uv run python manage.py migrate
   ```
   После миграции каждая таблица получает права и политику RLS `ee_app_access` для `ee_app`
   (`apps/core/db_security.py`). Без этой политики RLS закрыл бы таблицы и от сайта.
2. В `.env` сайта (и в Render) укажите `DATABASE_URL` с пользователем `ee_app`.
   Через пулер Supabase имя пользователя пишется как `ee_app.<project-ref>`.

## Проверка
Войдите на сайт, ответьте на упражнение. Если видите ошибку «permission denied», значит
миграцию запустили без `APP_DB_ROLE=ee_app` — повторите шаг 1.
