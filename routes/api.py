import random
from datetime import date

from fastapi import APIRouter, Depends

from database import get_db
from middleware.auth import get_current_user

router = APIRouter()

TIPS = [
    "Anxiety is a body alarm. Slow breathing helps your nervous system feel safe.",
    "Thoughts are not facts — pause and test before believing them.",
    "Name 5 things you can see to reconnect to the present moment.",
    "Self-compassion lowers stress. Speak to yourself kindly.",
    "Tiny actions reduce overwhelm. Choose one 2-minute task and start.",
    "Sleep, movement, and connection are the three biggest anxiety reducers.",
    "Worry has a peak — if you ride it out, it always comes down.",
]

PROMPTS = [
    "What thought is making me feel anxious right now?",
    "What evidence supports this thought, and what challenges it?",
    "If my friend had this worry, what would I tell them?",
    "What is a more balanced thought I can choose?",
    "What is one small step I can take in the next 10 minutes?",
    "Is this thought based on facts or feelings?",
    "What would I think about this situation in a week?",
    "What does my anxiety most need from me right now?",
]


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    return user


@router.get("/tips")
async def get_tip():
    return {"tip": TIPS[date.today().weekday() % len(TIPS)]}


@router.get("/prompts")
async def get_prompts():
    return {"prompts": PROMPTS}


@router.post("/checkin")
async def save_checkin(data: dict, user=Depends(get_current_user)):
    db = get_db()
    today = date.today().isoformat()
    db.execute(
        """
        INSERT INTO checkins (user_id, date_key, mood, anxiety, energy, sleep, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, date_key) DO UPDATE SET
            mood    = excluded.mood,
            anxiety = excluded.anxiety,
            energy  = excluded.energy,
            sleep   = excluded.sleep,
            notes   = excluded.notes
        """,
        (
            user["db_id"], today,
            data.get("mood"), data.get("anxiety"),
            data.get("energy"), data.get("sleep"),
            data.get("notes", ""),
        ),
    )
    db.commit()
    return {"ok": True}


@router.get("/checkins")
async def get_checkins(user=Depends(get_current_user)):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM checkins WHERE user_id=? ORDER BY date_key DESC LIMIT 30",
        (user["db_id"],),
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("/journal")
async def save_journal(data: dict, user=Depends(get_current_user)):
    db = get_db()
    db.execute(
        "INSERT INTO journal_entries (user_id, prompt, response, tag) VALUES (?, ?, ?, ?)",
        (user["db_id"], data.get("prompt", ""), data.get("response", ""), data.get("tag", "journal")),
    )
    db.commit()
    return {"ok": True}


@router.get("/journal")
async def get_journal(user=Depends(get_current_user)):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM journal_entries WHERE user_id=? ORDER BY created_at DESC LIMIT 30",
        (user["db_id"],),
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("/exercise-log")
async def log_exercise(data: dict, user=Depends(get_current_user)):
    db = get_db()
    db.execute(
        "INSERT INTO exercise_logs (user_id, exercise_type, seconds) VALUES (?, ?, ?)",
        (user["db_id"], data.get("type", "unknown"), data.get("seconds", 0)),
    )
    db.commit()
    return {"ok": True}


@router.get("/progress")
async def get_progress(user=Depends(get_current_user)):
    db = get_db()
    uid = user["db_id"]

    recent = db.execute(
        "SELECT date_key, mood, anxiety FROM checkins WHERE user_id=? ORDER BY date_key DESC LIMIT 14",
        (uid,),
    ).fetchall()

    total_checkins = db.execute(
        "SELECT COUNT(*) AS c FROM checkins WHERE user_id=?", (uid,)
    ).fetchone()["c"]

    avg_row = db.execute(
        "SELECT AVG(anxiety) AS a FROM checkins WHERE user_id=?", (uid,)
    ).fetchone()
    avg_anxiety = round(avg_row["a"], 1) if avg_row["a"] is not None else None

    exercises = db.execute(
        "SELECT COUNT(*) AS c FROM exercise_logs WHERE user_id=?", (uid,)
    ).fetchone()["c"]

    journals = db.execute(
        "SELECT COUNT(*) AS c FROM journal_entries WHERE user_id=?", (uid,)
    ).fetchone()["c"]

    return {
        "total_checkins": total_checkins,
        "avg_anxiety": avg_anxiety,
        "exercises": exercises,
        "journals": journals,
        "recent_checkins": [dict(r) for r in recent],
    }
