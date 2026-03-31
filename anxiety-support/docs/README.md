# Serenity — GitHub Pages deployment

This folder is the **complete Telegram Mini App** — one HTML file, no server needed.
All data is stored in the user's browser `localStorage`.

## Deploy in 5 steps

### 1 — Push to GitHub
```bash
cd /home/angelina/Documents/AI_projects/Lesson_3_mini_apps/anxiety-support
git init
git add .
git commit -m "initial"
# replace with your repo URL:
git remote add origin https://github.com/YOUR_USERNAME/serenity.git
git branch -M main
git push -u origin main
```

### 2 — Enable GitHub Pages
1. Open repo on GitHub → **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: `main`, folder: **`/docs`** → Save

Your URL will be:
```
https://YOUR_USERNAME.github.io/serenity/
```
(appears in the Pages settings in ~1 minute)

### 3 — Set up the Mini App in BotFather
Open [@BotFather](https://t.me/BotFather) and run:
```
/newapp
```
Choose your bot → give the app a name → set the URL to:
```
https://YOUR_USERNAME.github.io/serenity/
```

You can also add a Menu Button so the app opens from the bot chat:
```
/mybots → Your bot → Bot Settings → Menu Button
```
Paste the same GitHub Pages URL.

### 4 — Test
Open your bot → tap the Menu button (or send /start) → the Mini App opens with full features.

### 5 — Deep-links (optional)
Each section can be linked directly:
```
https://YOUR_USERNAME.github.io/serenity/?section=breathe
https://YOUR_USERNAME.github.io/serenity/?section=journal
https://YOUR_USERNAME.github.io/serenity/?section=calm
https://YOUR_USERNAME.github.io/serenity/?section=progress
```

---

## Features (100% offline, localStorage)
| Screen | What it does |
|--------|-------------|
| 🏠 Home | Daily mood check-in, anxiety/energy/sleep sliders |
| 🌬 Breathe | 2-min guided box breathing (4-4-4-4) |
| 🌱 Calm | 5-4-3-2-1 grounding checklist + CBT thought reframe |
| 📓 Journal | 8 CBT prompts, unlimited entries |
| 📈 Progress | Stats + 14-day mood bar chart |
