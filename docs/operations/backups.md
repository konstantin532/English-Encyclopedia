# Резервные копии базы

Каждый день в 05:17 (Москва) GitHub Actions (`.github/workflows/backup.yml`) делает копию базы
(`pg_dump`), шифрует её (AES-256) и хранит 30 дней в Actions → Database backup → Artifacts.
Репозиторий публичный, поэтому без шифрования копию мог бы скачать любой.

## Один раз: включить
GitHub → Settings → Secrets and variables → Actions → New repository secret.

Источник базы — один из двух:
- **свой сервер** (`docs/deploy/vps-moscow.md`): `VPS_HOST`, `VPS_SSH_KEY`, `VPS_KNOWN_HOSTS` — их выдаёт `deploy/vps/setup.sh`;
- **любой PostgreSQL**: `BACKUP_DATABASE_URL` — строка подключения (для Supabase — Session pooler, порт 5432).

И всегда:
- `BACKUP_PASSPHRASE` — длинный случайный пароль. **Сохраните его ещё и у себя** (менеджер паролей):
  без него копии не расшифровать.

Проверка: Actions → Database backup → Run workflow. В конце появится файл `ee-db-….dump.gpg`.

## Восстановление
```bash
gpg --decrypt ee-db-2026-10-21T0217Z.dump.gpg > db.dump
pg_restore --no-owner --clean --if-exists --dbname "<строка подключения>" db.dump
```
Восстанавливать лучше сначала в новую пустую базу и проверить, а не поверх рабочей.

Пока источник не настроен, ночной запуск красный — это намеренно: отсутствие копии не должно быть незаметным.
