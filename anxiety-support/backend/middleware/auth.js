const crypto = require('crypto');
const { upsertUser } = require('../database');

function verifyTelegramWebAppData(initData, botToken) {
  if (!initData || !botToken) return null;

  const params = new URLSearchParams(initData);
  const hash = params.get('hash');
  if (!hash) return null;

  params.delete('hash');
  const dataCheckString = [...params.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => `${key}=${value}`)
    .join('\n');

  const secretKey = crypto.createHmac('sha256', 'WebAppData').update(botToken).digest();
  const computedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

  if (computedHash !== hash) return null;

  const userRaw = params.get('user');
  if (!userRaw) return null;

  try {
    return JSON.parse(userRaw);
  } catch {
    return null;
  }
}

function authMiddleware(req, res, next) {
  const initData = req.headers['x-telegram-init-data'];
  const botToken = process.env.TELEGRAM_BOT_TOKEN;

  const telegramUser = verifyTelegramWebAppData(initData, botToken);

  if (!telegramUser) {
    if (process.env.NODE_ENV !== 'production' && req.headers['x-dev-user-id']) {
      const devUser = {
        id: req.headers['x-dev-user-id'],
        username: 'dev_user',
        first_name: 'Dev',
        last_name: 'User',
      };
      req.user = upsertUser(devUser);
      return next();
    }
    return res.status(401).json({ error: 'Unauthorized telegram session' });
  }

  req.user = upsertUser(telegramUser);
  next();
}

module.exports = authMiddleware;
