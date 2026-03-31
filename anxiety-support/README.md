# Anxiety Support Telegram Solution (Bot + Mini App)

This project is a full Telegram anxiety-support solution with:
- Telegram Bot (entrypoint, reminders, quick tips, deep links)
- Telegram Mini App (main UI)
- Node.js + Express backend
- SQLite (`better-sqlite3`) for secure lightweight storage
- HTTPS deployment on server `187.124.172.66` via Nginx + Let's Encrypt

## Features

Mini App includes:
- Daily check-ins (mood, anxiety, energy, sleep, note)
- Mood tracking and progress view
- Guided breathing session (box breathing)
- Grounding exercise (5-4-3-2-1)
- CBT thought reframing form
- Journaling prompts and entry history
- Quick relief session logging

Bot includes:
- `/start`, `/tip`, `/breathe`, `/grounding`, `/journal`, `/checkin`
- Menu button opening the Mini App
- Daily reminder scheduler
- Deep-link style section open using query string

## Project structure

- `backend/` — API server, bot logic, SQLite DB, Mini App static frontend
- `deploy/` — deployment and DNS helper scripts

## Environment

Copy `backend/.env.example` to `.env` for local run.

## Local run

```bash
cd backend
npm install
npm run dev
```

Then open `http://localhost:3000`.

> In local browser mode (outside Telegram), API auth falls back to a development user header.

## Production deployment (automated script)

### 1) Free domain — no registration needed (sslip.io)

[sslip.io](https://sslip.io) maps any IP address to a hostname automatically.
For server IP `187.124.172.66` the domain is:

```
187-124-172-66.sslip.io
```

No sign-up, no DNS records to create. The deploy script derives this automatically.

### 2) Full deployment to server `187.124.172.66`

Run:

```bash
SERVER_IP=187.124.172.66 \
SERVER_USER=root \
SSH_KEY=~/.ssh/id_rsa \
BOT_TOKEN=123:abc \
BOT_USERNAME=your_bot_username \
WEBHOOK_SECRET=$(openssl rand -hex 20) \
./deploy/deploy.sh
```

The domain defaults to `187-124-172-66.sslip.io`. Override with `DOMAIN=...` if needed.

The script performs:
- server package install (Node.js, PM2, Nginx, Certbot)
- app upload and dependency install
- env config generation
- Nginx reverse-proxy config
- HTTPS certificate issuance
- PM2 startup config
- Telegram API setup (`setMyCommands`, `setChatMenuButton`, `setWebhook`)

## Important Telegram note

Creating a new bot itself is only possible through BotFather chat and cannot be created directly through standard Bot API methods. After obtaining bot token and username once, this project fully automates all programmable bot configuration.

## Security notes

- Telegram Mini App auth uses initData signature verification.
- Webhook endpoint supports secret token checking.
- Helmet + rate limiting enabled.
- SQLite stores data locally on server (`backend/data/anxiety_support.db`).

## Clinical note

This tool supports self-help techniques and is not a replacement for emergency or crisis care.
