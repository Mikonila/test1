#!/usr/bin/env bash
set -euo pipefail

# Usage (no domain registration needed — sslip.io is used automatically):
#   SERVER_IP=187.124.172.66 \
#   SERVER_USER=root \
#   SSH_KEY=~/.ssh/id_rsa \
#   BOT_TOKEN=... BOT_USERNAME=... WEBHOOK_SECRET=... \
#   ./deploy/deploy.sh
#
# Optionally override the domain:
#   DOMAIN=custom.example.com ./deploy/deploy.sh ...

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

: "${SERVER_IP:?Missing SERVER_IP}"
: "${SERVER_USER:?Missing SERVER_USER}"
: "${BOT_TOKEN:?Missing BOT_TOKEN}"
: "${BOT_USERNAME:?Missing BOT_USERNAME}"
: "${WEBHOOK_SECRET:?Missing WEBHOOK_SECRET}"

# Auto-derive sslip.io domain from server IP (no registration required)
DOMAIN="${DOMAIN:-${SERVER_IP//./-}.sslip.io}"
echo "Using domain: ${DOMAIN}"

SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_rsa}"
APP_DIR="/opt/anxiety-support"

echo "[1/8] Packing project"
TMP_TAR="/tmp/anxiety-support.tgz"
tar --exclude='node_modules' --exclude='.git' -czf "$TMP_TAR" -C "$ROOT_DIR" .

echo "[2/8] Uploading files to server"
scp -i "$SSH_KEY" "$TMP_TAR" "${SERVER_USER}@${SERVER_IP}:/tmp/anxiety-support.tgz"

echo "[3/8] Installing system packages"
ssh -i "$SSH_KEY" "${SERVER_USER}@${SERVER_IP}" "
  set -e
  apt-get update
  apt-get install -y nginx curl git unzip ufw certbot python3-certbot-nginx
  if ! command -v node >/dev/null 2>&1; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
  fi
  npm i -g pm2
"

echo "[4/8] Deploying app files"
ssh -i "$SSH_KEY" "${SERVER_USER}@${SERVER_IP}" "
  set -e
  mkdir -p ${APP_DIR}
  tar -xzf /tmp/anxiety-support.tgz -C ${APP_DIR}
  cd ${APP_DIR}/backend
  npm install --omit=dev
  cat > .env <<EOF
NODE_ENV=production
PORT=3000
APP_BASE_URL=https://${DOMAIN}
TELEGRAM_BOT_TOKEN=${BOT_TOKEN}
TELEGRAM_BOT_USERNAME=${BOT_USERNAME}
TELEGRAM_WEBHOOK_SECRET=${WEBHOOK_SECRET}
BOT_WEBHOOK_URL=https://${DOMAIN}/telegram/webhook
REMINDER_CRON=0 9 * * *
REMINDER_TIMEZONE=UTC
JWT_SECRET=$(openssl rand -hex 24)
EOF
"

echo "[5/8] Configuring Nginx"
ssh -i "$SSH_KEY" "${SERVER_USER}@${SERVER_IP}" "
  set -e
  export DOMAIN=${DOMAIN}
  envsubst '\$DOMAIN' < ${APP_DIR}/deploy/nginx-anxiety-support.conf > /etc/nginx/sites-available/anxiety-support.conf
  ln -sf /etc/nginx/sites-available/anxiety-support.conf /etc/nginx/sites-enabled/anxiety-support.conf
  rm -f /etc/nginx/sites-enabled/default
  nginx -t
  systemctl restart nginx
"

echo "[6/8] Obtaining SSL certificate"
ssh -i "$SSH_KEY" "${SERVER_USER}@${SERVER_IP}" "
  set -e
  certbot --nginx -d ${DOMAIN} --non-interactive --agree-tos -m admin@${DOMAIN} --redirect
  systemctl reload nginx
"

echo "[7/8] Starting backend with PM2"
ssh -i "$SSH_KEY" "${SERVER_USER}@${SERVER_IP}" "
  set -e
  cd ${APP_DIR}/backend
  pm2 start ecosystem.config.js --env production || pm2 restart anxiety-support-backend
  pm2 save
  pm2 startup systemd -u root --hp /root || true
"

echo "[8/8] Verifying bot settings"
API_URL="https://api.telegram.org/bot${BOT_TOKEN}"
curl -s "${API_URL}/setMyCommands" -d 'commands=[{"command":"start","description":"Open support bot and Mini App"},{"command":"tip","description":"Get a quick anxiety tip"},{"command":"breathe","description":"Open breathing exercises"},{"command":"grounding","description":"Open grounding tools"},{"command":"journal","description":"Open CBT journal prompts"},{"command":"checkin","description":"Open daily check-in"}]' > /dev/null
curl -s "${API_URL}/setChatMenuButton" -d "menu_button={\"type\":\"web_app\",\"text\":\"Open Mini App\",\"web_app\":{\"url\":\"https://${DOMAIN}\"}}" > /dev/null
curl -s "${API_URL}/setWebhook" -d "url=https://${DOMAIN}/telegram/webhook" -d "secret_token=${WEBHOOK_SECRET}" > /dev/null

rm -f "$TMP_TAR"
echo "Deployment complete: https://${DOMAIN}"
