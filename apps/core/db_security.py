"""Защита данных на Supabase.

Supabase автоматически открывает схему public через Data API (PostgREST)
для ролей anon и authenticated. Включаем RLS на всех таблицах public без политик
для этих ролей: Data API не видит ничего.

Сайт может работать не владельцем таблиц, а отдельной ролью с минимальными правами
(APP_DB_ROLE, см. docs/operations/database-role.md). RLS закрывает таблицы и от неё,
поэтому для этой роли создаётся явная политика и выдаются только права на данные:
читать и писать строки, но не удалять и не менять таблицы.
"""
import os
import re

from django.db import connection

SQL_TABLES_WITHOUT_RLS = """
select tablename from pg_tables
where schemaname = 'public' and rowsecurity = false
"""
SQL_PUBLIC_TABLES = "select tablename from pg_tables where schemaname = 'public'"
POLICY = "ee_app_access"
ROLE_NAME = re.compile(r"[a-z_][a-z0-9_]{0,62}")


def app_role() -> str:
    role = os.getenv("APP_DB_ROLE", "").strip()
    if role and not ROLE_NAME.fullmatch(role):
        raise ValueError("APP_DB_ROLE: только строчные латинские буквы, цифры и _")
    return role


def enable_rls_on_public_tables(sender=None, using="default", **kwargs):
    if connection.vendor != "postgresql" or getattr(sender, "label", None) != "core":
        return
    with connection.cursor() as cur:
        cur.execute(SQL_TABLES_WITHOUT_RLS)
        for (table,) in cur.fetchall():
            cur.execute(f'alter table public."{table}" enable row level security')
    grant_app_role()


def grant_app_role(role: str | None = None) -> int:
    """Политика и права для роли сайта на каждой таблице public. Возвращает число таблиц."""
    role = app_role() if role is None else role
    if not role or connection.vendor != "postgresql":
        return 0
    with connection.cursor() as cur:
        cur.execute("select 1 from pg_roles where rolname = %s", [role])
        if cur.fetchone() is None:
            return 0
        cur.execute(SQL_PUBLIC_TABLES)
        tables = [t for (t,) in cur.fetchall()]
        cur.execute(f'grant usage on schema public to "{role}"')
        cur.execute(f'grant usage, select on all sequences in schema public to "{role}"')
        for table in tables:
            cur.execute(f'grant select, insert, update, delete on public."{table}" to "{role}"')
            cur.execute("select 1 from pg_policies where schemaname = 'public' and tablename = %s and policyname = %s",
                        [table, POLICY])
            if cur.fetchone() is None:
                cur.execute(f'create policy {POLICY} on public."{table}" for all to "{role}" using (true) with check (true)')
    return len(tables)
