#!/usr/bin/env bash
# Первичная настройка чистого сервера Ubuntu 24.04 (запускать один раз от root).
#   curl -fsSL https://raw.githubusercontent.com/konstantin532/English-Encyclopedia/main/deploy/vps/setup.sh -o setup.sh
#   bash setup.sh                 # адрес сайта будет вида 1-2-3-4.sslip.io
#   bash setup.sh english.ru      # если уже есть свой домен, направленный на этот сервер
set -Eeuo pipefail
[ "$(id -u)" = 0 ] || { echo "Запустите от root: sudo bash setup.sh"; exit 1; }

REPO=https://github.com/konstantin532/English-Encyclopedia.git
APP_DIR=/opt/english-encyclopedia

public_ip() { curl -fsS4 --max-time 10 https://api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}'; }

echo "== 1/6 Обновления и Docker"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq docker.io docker-compose-v2 git ufw unattended-upgrades curl openssl
systemctl enable --now docker

echo "== 2/6 Брандмауэр: открыты только SSH, 80 и 443"
ufw allow OpenSSH >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null

echo "== 3/6 Пользователь deploy"
id deploy >/dev/null 2>&1 || useradd --create-home --shell /bin/bash deploy
usermod -aG docker deploy

echo "== 4/6 Код проекта"
if [ ! -d "$APP_DIR/.git" ]; then
  git clone --quiet "$REPO" "$APP_DIR"
fi
chown -R deploy:deploy "$APP_DIR"
install -m 755 "$APP_DIR/deploy/vps/ssh-gate.sh" /usr/local/bin/ee-ssh-gate

echo "== 5/6 Настройки (.env)"
ENV_FILE="$APP_DIR/deploy/vps/.env"
if [ ! -f "$ENV_FILE" ]; then
  domain=${1:-}
  if [ -z "$domain" ]; then
    ip=$(public_ip)
    domain="${ip//./-}.sslip.io"
  fi
  umask 077
  cat > "$ENV_FILE" <<ENV
SITE_DOMAIN=$domain
DJANGO_SECRET_KEY=$(openssl rand -base64 48 | tr -d '\n/+=')
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d '\n/+=')
WEB_CONCURRENCY=2
ENV
  chown deploy:deploy "$ENV_FILE"
fi

echo "== 6/6 Ключ для GitHub Actions (только deploy и backup)"
KEY=/home/deploy/.ssh/github_actions
install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
if [ ! -f "$KEY" ]; then
  sudo -u deploy ssh-keygen -q -t ed25519 -N "" -C "github-actions@english-encyclopedia" -f "$KEY"
  echo "command=\"/usr/local/bin/ee-ssh-gate\",restrict $(cat "$KEY.pub")" >> /home/deploy/.ssh/authorized_keys
  chown deploy:deploy /home/deploy/.ssh/authorized_keys
  chmod 600 /home/deploy/.ssh/authorized_keys
fi

echo "== Запускаю сайт (первая сборка — несколько минут)"
sudo -u deploy "$APP_DIR/deploy/vps/update.sh"

. "$ENV_FILE"
cat <<INFO

=================================================================
Готово. Сайт: https://$SITE_DOMAIN
(сертификат https появляется в первую минуту после запуска)

Добавьте в GitHub: Settings → Secrets and variables → Actions → New repository secret
  VPS_HOST         = $(public_ip)
  VPS_KNOWN_HOSTS  = $(ssh-keyscan -t ed25519 localhost 2>/dev/null | sed "s/^localhost/$(public_ip)/")
  VPS_SSH_KEY      = всё содержимое файла ниже, вместе со строками BEGIN и END:
INFO
cat "$KEY"
cat <<INFO

Этот ключ умеет на сервере только две команды: обновить сайт и выдать копию базы.
После добавления секретов удалите его копию с экрана и из буфера обмена.
=================================================================
INFO
