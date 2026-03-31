#!/usr/bin/env bash
set -euo pipefail

# ─── Configuration ─────────────────────────────────────────────────────────────
SERVER_IP="187.124.172.66"
SERVER_USER="root"
DOMAIN="187-124-172-66.sslip.io"
APP_DIR="/opt/anxiety-support"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BOT_TOKEN="8768979164:AAHfGO-jXO-eDN1X_x6wxtxg5x-MXo5Xr4A"
BOT_USERNAME="dkmkdmvlbot"
WEBHOOK_SECRET="a8a0f3a6222f2a6165cf69bcfb17a882bbea26fbedb9b45f"
# ──────────────────────────────────────────────────────────────────────────────

SSH="ssh -o StrictHostKeyChecking=accept-new ${SERVER_USER}@${SERVER_IP}"
SCP="scp -o StrictHostKeyChecking=accept-new"

echo "==> Deploying to ${SERVER_USER}@${SERVER_IP}  (https://${DOMAIN})"

# ── 1. Pack ────────────────────────────────────────────────────────────────────
echo "[1/7] Packing project"
TMP_TAR="/tmp/anxiety-support.tgz"
tar --exclude='*/node_modules' --exclude='*/.git' --exclude='*/data' \
    --exclude='*/__pycache__' --exclude='*/venv' \
    -czf "$TMP_TAR" -C "$ROOT_DIR" .

# ── 2. Upload ──────────────────────────────────────────────────────────────────
echo "[2/7] Uploading to server"
$SCP "$TMP_TAR" "${SERVER_USER}@${SERVER_IP}:/tmp/anxiety-support.tgz"

# ── 3. System packages ─────────────────────────────────────────────────────────
echo "[3/7] Installing Python 3, Nginx, Certbot"
$SSH "
  set -e
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -q
  apt-get install -y -q python3 python3-pip python3-venv nginx certbot python3-certbot-nginx
"

# ── 4. Deploy app ──────────────────────────────────────────────────────────────
echo "[4/7] Deploying files, venv, .env"
$SSH "
  set -e
  mkdir -p ${APP_DIR}
  tar -xzf /tmp/anxiety-support.tgz -C ${APP_DIR}
  mkdir -p ${APP_DIR}/backend/data

  python3 -m venv ${APP_DIR}/venv
  ${APP_DIR}/venv/bin/pip install -q --upgrade pip
  ${APP_DIR}/venv/bin/pip install -q -r ${APP_DIR}/backend/requirements.txt

  cat > ${APP_DIR}/backend/.env <<'ENVEOF'
APP_ENV=production
APP_BASE_URL=https://${DOMAIN}
TELEGRAM_BOT_TOKEN=${BOT_TOKEN}
TELEGRAM_BOT_USERNAME=${BOT_USERNAME}
TELEGRAM_WEBHOOK_SECRET=${WEBHOOK_SECRET}
BOT_WEBHOOK_URL=https://${DOMAIN}/telegram/webhook
ENVEOF
"

# ── 5. Nginx ───────────────────────────────────────────────────────────────────
echo "[5/7] Configuring Nginx"
$SSH "
  set -e
  cat > /etc/nginx/sites-available/anxiety-support.conf <<'NGINXEOF'
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};
    client_max_body_size 2m;
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINXEOF
  ln -sf /etc/nginx/sites-available/anxiety-support.conf /etc/nginx/sites-enabled/anxiety-support.conf
  rm -f /etc/nginx/sites-enabled/default
  nginx -t && systemctl restart nginx
"

# ── 6. SSL ─────────────────────────────────────────────────────────────────────
echo "[6/7] Obtaining SSL certificate (Let's Encrypt)"
$SSH "
  certbot --nginx -d ${DOMAIN} --non-interactive --agree-tos -m admin@${DOMAIN} --redirect
  systemctl reload nginx
"

# ── 7. Systemd service ─────────────────────────────────────────────────────────
echo "[7/7] Starting app with systemd"
$SSH "
  set -e
  cat > /etc/systemd/system/anxiety-support.service <<'SVCEOF'
[Unit]
Description=Anxiety Support Backend
After=network.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}/backend
ExecStart=${APP_DIR}/venv/bin/uvicorn main:app --host 127.0.0.1 --port 3000 --log-level info
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
SVCEOF

  systemctl daemon-reload
  systemctl enable anxiety-support
  systemctl restart anxiety-support
  sleep 3
  systemctl is-active anxiety-support
"

# ── Bot API setup ──────────────────────────────────────────────────────────────
API="https://api.telegram.org/bot${BOT_TOKEN}"
curl -sf "${API}/setMyCommands" \
  -d 'commands=[{"command":"start","description":"Open support bot and Mini App"},{"command":"tip","description":"Get a quick anxiety tip"},{"command":"breathe","description":"Open breathing exercises"},{"command":"grounding","description":"Open grounding tools"},{"command":"journal","description":"Open CBT journal prompts"},{"command":"checkin","description":"Open daily check-in"}]' \
  > /dev/null
curl -sf "${API}/setChatMenuButton" -H 'Content-Type: application/json' \
  -d "{\"menu_button\":{\"type\":\"web_app\",\"text\":\"Open Mini App\",\"web_app\":{\"url\":\"https://${DOMAIN}\"}}}" \
  > /dev/null
curl -sf "${API}/setWebhook" \
  -d "url=https://${DOMAIN}/telegram/webhook" \
  -d "secret_token=${WEBHOOK_SECRET}" \
  > /dev/null

rm -f "$TMP_TAR"
echo ""
echo "✅  Done!"
echo "    Mini App : https://${DOMAIN}"
echo "    Bot      : @${BOT_USERNAME}"
echo "    Health   : https://${DOMAIN}/health"


echo "==> Deploying to ${SERVER_USER}@${SERVER_IP} (https://${DOMAIN})"

# ── 1. Pack ────────────────────────────────────────────────────────────────────
echo "[1/8] Packing project (excluding node_modules)"
TMP_TAR="/tmp/anxiety-support.tgz"
tar --exclude='*/node_modules' --exclude='*/.git' --exclude='*/data' \
    -czf "$TMP_TAR" -C "$ROOT_DIR" .

# ── 2. Upload ──────────────────────────────────────────────────────────────────
echo "[2/8] Uploading to server"
scp -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new \
    "$TMP_TAR" "${SERVER_USER}@${SERVER_IP}:/tmp/anxiety-support.tgz"

# ── 3. System packages ─────────────────────────────────────────────────────────
echo "[3/8] Installing system packages (Node.js 20, Nginx, Certbot, PM2)"
$SSH "
  set -e
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -q
  apt-get install -y -q curl nginx certbot python3-certbot-nginx ufw

  if ! command -v node >/dev/null 2>&1 || [[ \"\$(node -v)\" < \"v20\" ]]; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y -q nodejs
  fi

  npm install -g pm2 --silent
"

# ── 4. Deploy files ────────────────────────────────────────────────────────────
echo "[4/8] Deploying app files and writing .env"
$SSH "
  set -e
  mkdir -p ${APP_DIR}
  tar -xzf /tmp/anxiety-support.tgz -C ${APP_DIR}
  mkdir -p ${APP_DIR}/backend/data

  cd ${APP_DIR}/backend
  npm install --omit=dev --silent

  cat > ${APP_DIR}/backend/.env <<'ENVEOF'
NODE_ENV=production
PORT=3000
APP_BASE_URL=https://${DOMAIN}
TELEGRAM_BOT_TOKEN=${BOT_TOKEN}
TELEGRAM_BOT_USERNAME=${BOT_USERNAME}
TELEGRAM_WEBHOOK_SECRET=${WEBHOOK_SECRET}
BOT_WEBHOOK_URL=https://${DOMAIN}/telegram/webhook
JWT_SECRET=${JWT_SECRET}
REMINDER_CRON=0 9 * * *
REMINDER_TIMEZONE=UTC
ENVEOF
"

# ── 5. Nginx ───────────────────────────────────────────────────────────────────
echo "[5/8] Configuring Nginx"
$SSH "
  set -e
  cat > /etc/nginx/sites-available/anxiety-support.conf <<'NGINXEOF'
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};
    client_max_body_size 2m;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
}
NGINXEOF

  ln -sf /etc/nginx/sites-available/anxiety-support.conf \
         /etc/nginx/sites-enabled/anxiety-support.conf
  rm -f /etc/nginx/sites-enabled/default
  nginx -t
  systemctl restart nginx
"

# ── 6. SSL ─────────────────────────────────────────────────────────────────────
echo "[6/8] Obtaining Let's Encrypt SSL certificate"
$SSH "
  set -e
  certbot --nginx -d ${DOMAIN} \
    --non-interactive --agree-tos \
    -m admin@${DOMAIN} \
    --redirect
  systemctl reload nginx
"

# ── 7. PM2 ────────────────────────────────────────────────────────────────────
echo "[7/8] Starting backend with PM2"
$SSH "
  set -e
  cd ${APP_DIR}/backend
  pm2 delete anxiety-support-backend 2>/dev/null || true
  pm2 start ecosystem.config.js --env production
  pm2 save
  pm2 startup systemd -u root --hp /root 2>/dev/null | tail -1 | bash || true
"

# ── 8. Bot configuration ───────────────────────────────────────────────────────
echo "[8/8] Configuring Telegram bot (commands, menu button, webhook)"
API="https://api.telegram.org/bot${BOT_TOKEN}"

curl -sf "${API}/setMyCommands" \
  -d 'commands=[
    {"command":"start","description":"Open support bot and Mini App"},
    {"command":"tip","description":"Get a quick anxiety tip"},
    {"command":"breathe","description":"Open breathing exercises"},
    {"command":"grounding","description":"Open grounding tools"},
    {"command":"journal","description":"Open CBT journal prompts"},
    {"command":"checkin","description":"Open daily check-in"}
  ]' > /dev/null

curl -sf "${API}/setChatMenuButton" \
  -H 'Content-Type: application/json' \
  -d "{\"menu_button\":{\"type\":\"web_app\",\"text\":\"Open Mini App\",\"web_app\":{\"url\":\"https://${DOMAIN}\"}}}" \
  > /dev/null

curl -sf "${API}/setWebhook" \
  -d "url=https://${DOMAIN}/telegram/webhook" \
  -d "secret_token=${WEBHOOK_SECRET}" \
  -d "allowed_updates=[\"message\",\"callback_query\"]" \
  > /dev/null

# ── Done ───────────────────────────────────────────────────────────────────────
rm -f "$TMP_TAR"
echo ""
echo "✅  Deployment complete!"
echo "    Mini App URL : https://${DOMAIN}"
echo "    Bot          : @${BOT_USERNAME}"
echo "    Webhook      : https://${DOMAIN}/telegram/webhook"
echo "    Health check : https://${DOMAIN}/health"
