const express = require('express');
const authMiddleware = require('../middleware/auth');
const { db } = require('../database');

const router = express.Router();

const CBT_PROMPTS = [
  'What thought is making me feel anxious right now?',
  'What evidence supports this thought, and what evidence challenges it?',
  'If my friend had this worry, what would I tell them?',
  'What is a more balanced thought I can choose?',
  'What is one small step I can take in the next 10 minutes?'
];

const PSYCHO_TIPS = [
  'Anxiety is a body alarm. Slow breathing helps your nervous system feel safe.',
  'Name 5 things you can see to reconnect to the present moment.',
  'Thoughts are not facts. Pause and test the thought before believing it.',
  'Tiny actions reduce overwhelm. Choose one 2-minute task and start there.',
  'Self-compassion lowers stress chemistry. Speak to yourself kindly.'
];

function todayKey() {
  return new Date().toISOString().slice(0, 10);
}

router.use(authMiddleware);

router.get('/me', (req, res) => {
  res.json({ user: req.user });
});

router.get('/prompts', (_req, res) => {
  const shuffled = [...CBT_PROMPTS].sort(() => Math.random() - 0.5);
  res.json({ prompts: shuffled });
});

router.get('/tips', (_req, res) => {
  res.json({ tips: PSYCHO_TIPS });
});

router.post('/checkin', (req, res) => {
  const { mood, anxietyLevel, energyLevel, sleepHours, notes } = req.body;

  if (!Number.isInteger(mood) || mood < 1 || mood > 5) {
    return res.status(400).json({ error: 'mood must be integer 1-5' });
  }
  if (!Number.isInteger(anxietyLevel) || anxietyLevel < 1 || anxietyLevel > 10) {
    return res.status(400).json({ error: 'anxietyLevel must be integer 1-10' });
  }

  const stmt = db.prepare(`
    INSERT INTO checkins (user_id, date_key, mood, anxiety_level, energy_level, sleep_hours, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(user_id, date_key) DO UPDATE SET
      mood = excluded.mood,
      anxiety_level = excluded.anxiety_level,
      energy_level = excluded.energy_level,
      sleep_hours = excluded.sleep_hours,
      notes = excluded.notes
  `);

  stmt.run(
    req.user.id,
    todayKey(),
    mood,
    anxietyLevel,
    Number.isInteger(energyLevel) ? energyLevel : null,
    typeof sleepHours === 'number' ? sleepHours : null,
    notes || null
  );

  res.json({ ok: true });
});

router.get('/checkins', (req, res) => {
  const days = Math.min(Number(req.query.days || 30), 90);
  const rows = db.prepare(`
    SELECT date_key, mood, anxiety_level, energy_level, sleep_hours, notes
    FROM checkins
    WHERE user_id = ?
      AND date(date_key) >= date('now', ?)
    ORDER BY date_key ASC
  `).all(req.user.id, `-${days} day`);

  res.json({ items: rows });
});

router.post('/journal', (req, res) => {
  const { prompt, response, moodTag } = req.body;
  if (!prompt || !response) {
    return res.status(400).json({ error: 'prompt and response are required' });
  }

  const result = db.prepare(`
    INSERT INTO journal_entries (user_id, prompt, response, mood_tag)
    VALUES (?, ?, ?, ?)
  `).run(req.user.id, prompt.slice(0, 500), response.slice(0, 2000), moodTag || null);

  res.json({ id: result.lastInsertRowid });
});

router.get('/journal', (req, res) => {
  const items = db.prepare(`
    SELECT id, prompt, response, mood_tag, created_at
    FROM journal_entries
    WHERE user_id = ?
    ORDER BY created_at DESC
    LIMIT 50
  `).all(req.user.id);

  res.json({ items });
});

router.post('/exercise-log', (req, res) => {
  const { type, durationSeconds, intensity } = req.body;
  if (!type || !Number.isInteger(durationSeconds) || durationSeconds <= 0) {
    return res.status(400).json({ error: 'type and durationSeconds are required' });
  }

  db.prepare(`
    INSERT INTO exercise_logs (user_id, type, duration_seconds, intensity)
    VALUES (?, ?, ?, ?)
  `).run(req.user.id, type.slice(0, 100), durationSeconds, Number.isInteger(intensity) ? intensity : null);

  res.json({ ok: true });
});

router.post('/relief-session', (req, res) => {
  const { technique, beforeLevel, afterLevel, notes } = req.body;
  if (!technique) {
    return res.status(400).json({ error: 'technique is required' });
  }

  db.prepare(`
    INSERT INTO relief_sessions (user_id, technique, before_level, after_level, notes)
    VALUES (?, ?, ?, ?, ?)
  `).run(
    req.user.id,
    technique.slice(0, 120),
    Number.isInteger(beforeLevel) ? beforeLevel : null,
    Number.isInteger(afterLevel) ? afterLevel : null,
    notes || null
  );

  res.json({ ok: true });
});

router.get('/progress', (req, res) => {
  const latestCheckins = db.prepare(`
    SELECT date_key, mood, anxiety_level
    FROM checkins
    WHERE user_id = ?
    ORDER BY date_key DESC
    LIMIT 30
  `).all(req.user.id);

  const sessionsDone = db.prepare(`
    SELECT COUNT(*) as total FROM relief_sessions WHERE user_id = ?
  `).get(req.user.id).total;

  const exercisesDone = db.prepare(`
    SELECT COUNT(*) as total FROM exercise_logs WHERE user_id = ?
  `).get(req.user.id).total;

  const journalsDone = db.prepare(`
    SELECT COUNT(*) as total FROM journal_entries WHERE user_id = ?
  `).get(req.user.id).total;

  const avgAnxiety = latestCheckins.length
    ? Number((latestCheckins.reduce((s, i) => s + i.anxiety_level, 0) / latestCheckins.length).toFixed(2))
    : null;

  const avgMood = latestCheckins.length
    ? Number((latestCheckins.reduce((s, i) => s + i.mood, 0) / latestCheckins.length).toFixed(2))
    : null;

  res.json({
    summary: {
      totalCheckins: latestCheckins.length,
      avgAnxiety,
      avgMood,
      sessionsDone,
      exercisesDone,
      journalsDone
    },
    checkins: latestCheckins.reverse()
  });
});

module.exports = router;
