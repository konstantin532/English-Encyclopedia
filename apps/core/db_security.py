"""Защита данных на Supabase.

Supabase автоматически открывает схему public через Data API (PostgREST)
для ролей anon и authenticated. Django ходит в базу владельцем таблиц и
работает через собственную авторизацию, поэтому включаем RLS на всех
таблицах public без политик: Data API не видит ничего, Django — всё.
"""
from django.db import connection

SQL_TABLES_WITHOUT_RLS = """
select tablename from pg_tables
where schemaname = 'public' and rowsecurity = false
"""


def enable_rls_on_public_tables(sender=None, using="default", **kwargs):
    if connection.vendor != "postgresql" or getattr(sender, "label", None) != "core":
        return
    with connection.cursor() as cur:
        cur.execute(SQL_TABLES_WITHOUT_RLS)
        for (table,) in cur.fetchall():
            cur.execute(f'alter table public."{table}" enable row level security')
