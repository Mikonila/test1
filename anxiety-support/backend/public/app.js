const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

const state = {
  selectedMood: 3,
  breathTimer: null,
  breathDurationSec: 120,
  initData: tg?.initData || '',
  userName: tg?.initDataUnsafe?.user?.first_name || 'Guest',
};

document.getElementById('userBadge').textContent = state.userName;

const api = {
  async request(path, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      'x-telegram-init-data': state.initData,
      ...options.headers,
    };

    if (!state.initData) {
      headers['x-dev-user-id'] = '999001';
    }

    const res = await fetch(`/api${path}`, {
      method: options.method || 'GET',
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || 'Request failed');
    }
    return res.json();
  },
};

function showToast(message) {
  const el = document.getElementById('toast');
  el.textContent = message;
  el.classList.remove('hidden');
  setTimeout(() => el.classList.add('hidden'), 2200);
}

function switchView(view) {
  document.querySelectorAll('.view').forEach((v) => v.classList.remove('active'));
  document.getElementById(`view-${view}`).classList.add('active');

  document.querySelectorAll('.bottom-nav button').forEach((b) => b.classList.remove('active'));
  document.querySelector(`.bottom-nav button[data-view="${view}"]`)?.classList.add('active');

  if (view === 'journal') loadJournals();
  if (view === 'progress') loadProgress();
}

document.querySelectorAll('.bottom-nav button').forEach((btn) => {
  btn.addEventListener('click', () => switchView(btn.dataset.view));
});

document.querySelectorAll('#moodPicker button').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#moodPicker button').forEach((x) => x.classList.remove('selected'));
    btn.classList.add('selected');
    state.selectedMood = Number(btn.dataset.mood);
  });
});

const anxietyInput = document.getElementById('anxietyLevel');
const energyInput = document.getElementById('energyLevel');
anxietyInput.addEventListener('input', () => document.getElementById('anxietyValue').textContent = anxietyInput.value);
energyInput.addEventListener('input', () => document.getElementById('energyValue').textContent = energyInput.value);

document.getElementById('saveCheckinBtn').addEventListener('click', async () => {
  try {
    await api.request('/checkin', {
      method: 'POST',
      body: {
        mood: state.selectedMood,
        anxietyLevel: Number(anxietyInput.value),
        energyLevel: Number(energyInput.value),
        sleepHours: Number(document.getElementById('sleepHours').value || 0),
        notes: document.getElementById('checkinNotes').value,
      }
    });
    showToast('Check-in saved 🌿');
  } catch (e) {
    showToast(e.message);
  }
});

document.getElementById('logReliefBtn').addEventListener('click', async () => {
  try {
    await api.request('/relief-session', {
      method: 'POST',
      body: {
        technique: 'quick-relief-2min',
        beforeLevel: Number(document.getElementById('beforeRelief').value),
        afterLevel: Number(document.getElementById('afterRelief').value),
      }
    });
    showToast('Relief session logged');
  } catch (e) {
    showToast(e.message);
  }
});

let breathLeft = state.breathDurationSec;
let phase = 0;
const phases = ['Inhale', 'Hold', 'Exhale', 'Hold'];

function updateBreathUI() {
  const circle = document.getElementById('breathCircle');
  const text = phases[phase % phases.length];
  circle.textContent = `${text}`;
  circle.classList.remove('expand', 'contract');
  if (text === 'Inhale') circle.classList.add('expand');
  if (text === 'Exhale') circle.classList.add('contract');
  document.getElementById('breathInstruction').textContent = `${text} • ${breathLeft}s left`;
}

document.getElementById('startBreathingBtn').addEventListener('click', () => {
  if (state.breathTimer) return;
  breathLeft = state.breathDurationSec;
  phase = 0;
  updateBreathUI();

  state.breathTimer = setInterval(async () => {
    breathLeft -= 1;
    if (breathLeft % 4 === 0) {
      phase += 1;
      updateBreathUI();
    }

    if (breathLeft <= 0) {
      clearInterval(state.breathTimer);
      state.breathTimer = null;
      document.getElementById('breathCircle').textContent = 'Done';
      document.getElementById('breathInstruction').textContent = 'Great work. Nervous system reset complete.';
      try {
        await api.request('/exercise-log', {
          method: 'POST',
          body: { type: 'box-breathing', durationSeconds: state.breathDurationSec, intensity: 2 }
        });
      } catch {}
      showToast('Breathing session complete');
    }
  }, 1000);
});

document.getElementById('stopBreathingBtn').addEventListener('click', async () => {
  if (state.breathTimer) {
    clearInterval(state.breathTimer);
    state.breathTimer = null;
    const done = state.breathDurationSec - breathLeft;
    if (done > 10) {
      try {
        await api.request('/exercise-log', {
          method: 'POST',
          body: { type: 'box-breathing-partial', durationSeconds: done, intensity: 1 }
        });
      } catch {}
    }
  }
  document.getElementById('breathCircle').textContent = 'Stopped';
  document.getElementById('breathInstruction').textContent = 'You can restart anytime';
});

document.getElementById('logGroundingBtn').addEventListener('click', async () => {
  try {
    await api.request('/exercise-log', {
      method: 'POST',
      body: { type: '5-4-3-2-1-grounding', durationSeconds: 120, intensity: 2 }
    });
    showToast('Grounding logged');
  } catch (e) {
    showToast(e.message);
  }
});

document.getElementById('saveCbtBtn').addEventListener('click', async () => {
  const thought = document.getElementById('cbtThought').value.trim();
  const evidence = document.getElementById('cbtEvidence').value.trim();
  const balanced = document.getElementById('cbtBalanced').value.trim();
  if (!thought || !balanced) {
    showToast('Please fill thought and balanced thought');
    return;
  }

  const prompt = 'CBT Thought Reframe';
  const response = `Thought: ${thought}\nEvidence against: ${evidence}\nBalanced thought: ${balanced}`;

  try {
    await api.request('/journal', {
      method: 'POST',
      body: { prompt, response, moodTag: 'cbt-reframe' }
    });
    showToast('CBT entry saved');
    document.getElementById('cbtThought').value = '';
    document.getElementById('cbtEvidence').value = '';
    document.getElementById('cbtBalanced').value = '';
  } catch (e) {
    showToast(e.message);
  }
});

async function loadPrompts() {
  try {
    const data = await api.request('/prompts');
    const select = document.getElementById('promptSelect');
    select.innerHTML = '';
    data.prompts.forEach((p) => {
      const opt = document.createElement('option');
      opt.value = p;
      opt.textContent = p;
      select.appendChild(opt);
    });
  } catch (e) {
    showToast(e.message);
  }
}

document.getElementById('saveJournalBtn').addEventListener('click', async () => {
  const prompt = document.getElementById('promptSelect').value;
  const response = document.getElementById('journalResponse').value.trim();
  if (!response) return showToast('Write a response first');

  try {
    await api.request('/journal', {
      method: 'POST',
      body: { prompt, response, moodTag: 'journal' }
    });
    document.getElementById('journalResponse').value = '';
    showToast('Journal saved');
    loadJournals();
  } catch (e) {
    showToast(e.message);
  }
});

async function loadJournals() {
  try {
    const data = await api.request('/journal');
    const list = document.getElementById('journalList');
    if (!data.items.length) {
      list.innerHTML = '<p>No entries yet.</p>';
      return;
    }

    list.innerHTML = data.items.map((item) => `
      <div class="list-item">
        <small>${new Date(item.created_at).toLocaleString()}</small>
        <strong>${item.prompt}</strong>
        <p>${item.response.replace(/</g, '&lt;').slice(0, 220)}</p>
      </div>
    `).join('');
  } catch (e) {
    showToast(e.message);
  }
}

function renderMoodChart(checkins = []) {
  const chart = document.getElementById('moodChart');
  chart.innerHTML = '';
  const last = checkins.slice(-10);
  if (!last.length) {
    chart.innerHTML = '<p>Not enough data yet.</p>';
    return;
  }

  last.forEach((item) => {
    const bar = document.createElement('div');
    bar.className = 'bar';
    bar.style.height = `${Math.max(12, item.mood * 22)}px`;
    bar.title = `${item.date_key}: mood ${item.mood}/5`;
    chart.appendChild(bar);
  });
}

async function loadProgress() {
  try {
    const data = await api.request('/progress');
    document.getElementById('totalCheckins').textContent = data.summary.totalCheckins;
    document.getElementById('avgAnxiety').textContent = data.summary.avgAnxiety ?? '-';
    document.getElementById('exercisesDone').textContent = data.summary.exercisesDone;
    document.getElementById('journalsDone').textContent = data.summary.journalsDone;
    renderMoodChart(data.checkins || []);
  } catch (e) {
    showToast(e.message);
  }
}

function applyDeepLinkSection() {
  const qs = new URLSearchParams(window.location.search);
  const section = qs.get('section');
  const allowed = ['home', 'breathe', 'calm', 'journal', 'progress'];
  if (section && allowed.includes(section)) {
    switchView(section);
  }
}

(async function init() {
  await loadPrompts();
  await loadProgress();
  applyDeepLinkSection();
})();
