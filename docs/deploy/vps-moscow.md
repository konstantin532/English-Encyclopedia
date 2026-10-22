# Сайт на своём сервере (VPS в Москве)

Сайт, база и https живут на одном сервере в Docker. Обновление — само, после каждого слияния в `main`.
Резервная копия базы — каждую ночь, зашифрованная, хранится в GitHub (Actions → Database backup → Artifacts, 30 дней).

## Что внутри

| Часть | Что делает |
|---|---|
| `db` — PostgreSQL 17 | База: ученики, прогресс, правки из админки. Наружу не открыта. |
| `web` — Django + Gunicorn | Сайт. При запуске: миграции, `load_content --preserve-admin-edits`. |
| `caddy` | https (бесплатный сертификат Let's Encrypt, продлевается сам), файлы `/media/`. |

Файлы: `deploy/vps/` (Dockerfile, compose.yml, Caddyfile, setup.sh, update.sh, ssh-gate.sh).

## Один раз: настроить сервер

Нужен VPS с **Ubuntu 24.04**, 2 ядра, 2–4 ГБ памяти, 30+ ГБ диска. Не тот, где VPN.

1. Подключитесь к серверу (данные для входа — в письме или кабинете хостинга):
   на Windows откройте «Терминал» и наберите `ssh root@АДРЕС_СЕРВЕРА`, введите пароль.
2. Выполните две команды:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/konstantin532/English-Encyclopedia/main/deploy/vps/setup.sh -o setup.sh
   bash setup.sh
   ```
   Если у вас уже есть домен и он направлен на сервер — `bash setup.sh ваш-домен.ru`.
   Без домена адрес будет вида `https://1-2-3-4.sslip.io` (цифры — адрес сервера).
3. В конце скрипт покажет три значения. Добавьте их в GitHub:
   **Settings → Secrets and variables → Actions → New repository secret**:
   `VPS_HOST`, `VPS_KNOWN_HOSTS`, `VPS_SSH_KEY` (ключ — целиком, со строками BEGIN и END).
4. Добавьте ещё `BACKUP_PASSPHRASE` — длинный пароль для шифрования копий.
   **Сохраните его и у себя**: без него копию не открыть.
5. Проверка: **Actions → Deploy to VPS → Run workflow**, затем **Actions → Database backup → Run workflow**.
   Оба должны стать зелёными.

## Как это работает дальше

- Слили PR в `main` → прошёл CI → **Deploy to VPS** по SSH запускает `update.sh`:
  свежий код, сборка, перезапуск, проверка `/healthz/`. Если сайт не ответил — запуск красный, в журнале причина.
- Ключ GitHub на сервере ограничен (`/usr/local/bin/ee-ssh-gate`): умеет только `deploy` и `backup`,
  войти по нему в консоль нельзя.
- Пароли сайта и базы лежат только на сервере, в `deploy/vps/.env` (права 600).

## Если что-то пошло не так

Зайти на сервер и посмотреть журнал сайта:
```bash
cd /opt/english-encyclopedia
docker compose -f deploy/vps/compose.yml logs --tail 100 web
```
Перезапустить вручную: `sudo -u deploy /opt/english-encyclopedia/deploy/vps/update.sh`.

## Озвучка

В git её нет. Пока сайт работает без звука. Чтобы добавить: в `deploy/vps/.env` задать
`A1_AUDIO_ARCHIVE_URL` и `A1_AUDIO_ARCHIVE_SHA256` (см. `deploy/install_audio_archive.py`) и перезапустить `update.sh`.

## Восстановление из копии

Скачать `ee-db-….dump.gpg` из Actions → Database backup → Artifacts, затем на сервере:
```bash
gpg --decrypt ee-db-ДАТА.dump.gpg > db.dump
docker compose -f deploy/vps/compose.yml exec -T db pg_restore -U english -d english --clean --if-exists --no-owner < db.dump
```
Лучше сначала проверить копию на отдельной пустой базе, а не поверх рабочей.

## Почему не Supabase / Render

Данные учеников из России по 152-ФЗ должны храниться в России; российский сервер открывается без VPN
и оплачивается российской картой. Код по-прежнему работает с любым PostgreSQL через `DATABASE_URL`.
