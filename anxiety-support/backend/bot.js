const { Telegraf } = require('telegraf');
const cron = require('node-cron');
const { db } = require('./database');

let bot;

function miniAppUrl(section = 'home') {
  const base = process.env.APP_BASE_URL;
  if (!base) return null;
  const url = new URL(base);
  url.searchParams.set('section', section);
  return url.toString();
}

function buildMainKeyboard() {
  const webUrl = miniAppUrl('home');
  if (!webUrl) return { reply_markup: { remove_keyboard: true } };

  return {
    reply_markup: {
      inline_keyboard: [
        [{ text: 'Open Anxiety Support Mini App', web_app: { url: webUrl } }],
        [
          { text: 'Breathing', web_app: { url: miniAppUrl('breathe') } },
          { text: 'Grounding', web_app: { url: miniAppUrl('calm') } }
        ],
        [
          { text: 'Journal', web_app: { url: miniAppUrl('journal') } },
          { text: 'Daily Check-In', web_app: { url: miniAppUrl('home') } }
        ]
      ]
    }
  };
}

async function setupBot() {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  if (!token) {
    console.warn('TELEGRAM_BOT_TOKEN missing, bot disabled.');
    return null;
  }

  bot = new Telegraf(token);

  bot.start(async (ctx) => {
    const text = [
      `Hi ${ctx.from.first_name || ''} 🌿`,
      'I am your Anxiety Support companion.',
      'Use the Mini App for check-ins, breathing, grounding, CBT journaling, and progress tracking.'
    ].join('\n');
    await ctx.reply(text, buildMainKeyboard());
  });

  bot.command('tip', async (ctx) => {
    const tips = [
      'Try box breathing: inhale 4, hold 4, exhale 4, hold 4.',
      'Notice and name your worry, then challenge it with evidence.',
      'Use 5-4-3-2-1 grounding to reconnect to the present moment.'
    ];
    const tip = tips[Math.floor(Math.random() * tips.length)];
    await ctx.reply(`Quick tip: ${tip}`);
  });

  const sectionMap = { breathe: 'breathe', grounding: 'calm', journal: 'journal', checkin: 'home' };
  for (const [command, section] of Object.entries(sectionMap)) {
    bot.command(command, async (ctx) => {
      const url = miniAppUrl(section);
      if (!url) { await ctx.reply('Mini App URL is not configured yet.'); return; }
      await ctx.reply('Opening Mini App section:', {
        reply_markup: { inline_keyboard: [[{ text: `Open ${section}`, web_app: { url } }]] }
      });
    });
  }

  try {
    await bot.telegram.setMyCommands([
      { command: 'start', description: 'Open support bot and Mini App' },
      { command: 'tip', description: 'Get a quick anxiety tip' },
      { command: 'breathe', description: 'Open breathing exercises' },
      { command: 'grounding', description: 'Open grounding tools' },
      { command: 'journal', description: 'Open CBT journal prompts' },
      { command: 'checkin', description: 'Open daily check-in' }
    ]);

    if (process.env.APP_BASE_URL) {
      await bot.telegram.setChatMenuButton({
        menu_button: {
          type: 'web_app',
          text: 'Open Mini App',
          web_app: { url: miniAppUrl('home') }
        }
      });
    }
  } catch (err) {
    console.error('Bot command/menu setup failed:', err.message);
  }

  const reminderCron = process.env.REMINDER_CRON || '0 9 * * *';
  const reminderTz = process.env.REMINDER_TIMEZONE || 'UTC';

  cron.schedule(reminderCron, async () => {
    const users = db.prepare('SELECT telegram_id, first_name FROM users').all();
    for (const user of users) {
      try {
        const text = [
          `Hi ${user.first_name || 'there'} 🌿`,
          'Friendly reminder: complete your daily check-in and a 2-minute breathing reset.'
        ].join('\n');
        await bot.telegram.sendMessage(user.telegram_id, text, buildMainKeyboard());
      } catch (e) {
        console.error('Reminder send failed:', e.message);
      }
    }
  }, { timezone: reminderTz });

  return bot;
}

async function setWebhook() {
  if (!bot) return;
  const webhookUrl = process.env.BOT_WEBHOOK_URL;
  const secretToken = process.env.TELEGRAM_WEBHOOK_SECRET;
  if (!webhookUrl) return;

  try {
    await bot.telegram.setWebhook(webhookUrl, secretToken ? { secret_token: secretToken } : {});
    console.log('Webhook configured:', webhookUrl);
  } catch (err) {
    console.error('Failed to set webhook:', err.message);
  }
}

async function handleUpdate(req, res) {
  if (!bot) return res.status(503).send('Bot not configured');

  const expectedSecret = process.env.TELEGRAM_WEBHOOK_SECRET;
  const receivedSecret = req.headers['x-telegram-bot-api-secret-token'];

  if (expectedSecret && expectedSecret !== receivedSecret) {
    return res.status(401).send('Invalid secret token');
  }

  try {
    await bot.handleUpdate(req.body);
    res.sendStatus(200);
  } catch (err) {
    console.error('Webhook update error:', err.message);
    res.sendStatus(500);
  }
}

module.exports = {
  setupBot,
  setWebhook,
  handleUpdate,
};
