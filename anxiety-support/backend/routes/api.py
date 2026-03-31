import random
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from database import get_db
from middleware.auth import get_current_user

router = APIRouter()

CBT_PROMPTS = [
    "What thought is making me feel anxious right now?",
    "What evidence supports this thought, and what challenges it?",
    "If my friend had this worry, what would I tell them?",
    "What is a more balanced thought I can choose?",
    "What is one small step I can take in the next 10 minutes?",
    "Is this thought based on facts or feelings?",
    "What would I think about this situation in a week?",
]

PSYCHO_TIPS = [
    "Anxiety is a body alarm. Slow breathing helps your nervous system feel safe.",
    "Name 5 things you can see to reconnect to the present moment.",
    "Thoughts are not facts. Pause and test the thought before believing it.",
    "Tiny actions reduce overwhelm. Choose one 2-minute task and start there.",
    "Self-compassion lowers stress chemistry. Speak to yourself kindly.",
]


class CheckinBody(BaseModel):
    mood: int = Field(..., ge=1, le=5)
    anxietyLevel: int = Field(..., ge=1, le=10)
    energyLevel: Optional[int] = Field(None, ge=1, le=10)
    sleepHours: Optional[float] = Field(None, ge=0, le=24)
    notes: Optional[str] = None


class JournalBody(BaseModel):
    prompt: str
    response: str
    moodTag: Optional[str] = None


class ExerciseBody(BaseModel):
    type: str
    durationSeconds: int = Field(..., gt=0)
    intensity: Optional[int] = None


class ReliefBody(BaseModel):
    technique: str
    beforeLevel: Optional[int] = None
    afterLevel: Optional[int] = None
    notes: Optional[str] = None


@router.get("/me")
def get_me(user=Depends(get_current_user)):
    return {"user": dict(user)}


@router.get("/prompts")
def get_prompts():
    shuffled = CBT_PROMPTS.copy()
    random.shuffle(shuffled)
    return {"prompts": shuffled}


@router.get("/tips")
def get_tips():
    return {"tips": PSYCHO_TIPS}


@router.post("/checkin")
def save_checkin(body: CheckinBody, user=Depends(get_current_user)):
    db = get_db()
    db.execute(
        """
        INSERT INTO checkins (user_id, date_key, mood, anxiety_level, energy_level, sleep_hours, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, date_key) DO UPDATE SET
            mood=excluded.mood, anxiety_level=excluded.anxiety_level,
            energy_level=excluded.energy_level, sleep_hours=excluded.sleep_hours,
            notes=excluded.notes
        """,
        (user["id"], date.today().isoformat(), body.mood, body.anxietyLevel,
         body.energyLevel, body.sleepHours, body.notes),
    )
    db.commit()
    return {"ok": True}


@router.get("/checkins")
def get_checkins(days: int = 30, user=Depends(get_current_user)):
    db = get_db()
    rows = db.execute(
        """SELECT date_key, mood, anxiety_level, energy_level, sleep_hours, notes
           FROM checkins WHERE user_id=? AND date(date_key)>=date('now',?)
           ORDER BY date_key ASC""",
        (user["id"], f"-{min(days,90)} day"),
    ).fetchall()
    return {"items": [dict(r) for r in rows]}


@router.post("/journal")
def save_journal(body: JournalBody, user=Depends(get_current_user)):
    db = get_db()
    cur = db.execute(
        "INSERT INTO journal_entries (user_id, prompt, response, mood_tag) VALUES (?,?,?,?)",
        (user["id"], body.prompt[:500], body.response[:2000], body.moodTag),
    )
    db.commit()
    return {"id": cur.lastrowid}


@router.get("/journal")
def get_journal(user=Depends(get_current_user)):
    db = get_db()
    rows = db.execute(
        "SELECT id,prompt,response,mood_tag,created_at FROM journal_entries WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
        (user["id"],),
    ).fetchall()
    return {"items": [dict(r) for r in rows]}


@router.post("/exercise-log")
def log_exercise(body: ExerciseBody, user=Depends(get_current_user)):
    db = get_db()
    db.execute(
        "INSERT INTO exercise_logs (user_id, type, duration_seconds, intensity) VALUES (?,?,?,?)",
        (user["id"], body.type[:100], body.durationSeconds, body.intensity),
    )
    db.commit()
    return {"ok": True}


@router.post("/relief-session")
def log_relief(body: ReliefBody, user=Depends(get_current_user)):
    db = get_db()
    db.execute(
        "INSERT INTO relief_sessions (user_id, technique, before_level, after_level, notes) VALUES (?,?,?,?,?)",
        (user["id"], body.technique[:120], body.beforeLevel, body.afterLevel, body.notes),
    )
    db.commit()
    return {"ok": True}


@router.get("/progress")
def get_progress(user=Depends(get_current_user)):
    db = get_db()
    checkins = db.execute(
        "SELECT date_key, mood, anxiety_level FROM checkins WHERE user_id=? ORDER BY date_key DESC LIMIT 30",
        (user["id"],),
    ).fetchall()
    rows = [dict(r) for r in checkins]

    sessions = db.execute("SELECT COUNT(*) as n FROM relief_sessions WHERE user_id=?", (user["id"],)).fetchone()["n"]
    exercises = db.execute("SELECT COUNT(*) as n FROM exercise_logs WHERE user_id=?", (user["id"],)).fetchone()["n"]
    journals = db.execute("SELECT COUNT(*) as n FROM journal_entries WHERE user_id=?", (user["id"],)).fetchone()["n"]

    avg_anxiety = round(sum(r["anxiety_level"] for r in rows) / len(rows), 2) if rows else None
    avg_mood = round(sum(r["mood"] for r in rows) / len(rows), 2) if rows else None

    return {
        "summary": {
            "totalCheckins": len(rows),
            "avgAnxiety": avg_anxiety,
            "avgMood": avg_mood,
            "sessionsDone": sessions,
            "exercisesDone": exercises,
            "journalsDone": journals,
        },
        "checkins": list(reversed(rows)),
    }
