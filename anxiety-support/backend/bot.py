import asyncio
import logging
import os
import random
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    Update,
    WebAppInfo,
)
from fastapi import APIRouter, Header, Request
from fastapi.responses import Response

logger = logging.getLogger(__name__)

_bot: Bot | None = None
_dp: Dispatcher | None = None

tg_router = Router()
webhook_router = APIRouter()


def mini_app_url(section: str = "home") -> str:
    base = os.getenv("APP_BASE_URL", "").rstrip("/")
    return f"{base}?section={section}"


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌿 Open Anxiety Support", web_app=WebAppInfo(url=mini_app_url("home")))],
            [
                InlineKeyboardButton(text="🌬 Breathing", web_app=WebAppInfo(url=mini_app_url("breathe"))),
                InlineKeyboardButton(text="🌱 Grounding", web_app=WebAppInfo(url=mini_app_url("calm"))),
            ],
            [
                InlineKeyboardButton(text="📓 Journal", web_app=WebAppInfo(url=mini_app_url("journal"))),
                InlineKeyboardButton(text="✅ Check-In", web_app=WebAppInfo(url=mini_app_url("home"))),
            ],
        ]
    )


@tg_router.message(Command("start"))
async def cmd_start(message: Message):
    name = message.from_user.first_name or ""
    await message.answer(
        f"Hi {name} 🌿\n"
        "I'm your Anxiety Support companion.\n"
        "Use the Mini App for daily check-ins, breathing, grounding, CBT journaling, and progress tracking.",
        reply_markup=main_keyboard(),
    )


@tg_router.message(Command("tip"))
async def cmd_tip(message: Message):
    tips = [
        "Try box breathing: inhale 4s → hold 4s → exhale 4s → hold 4s.",
        "Notice and name your worry, then challenge it with evidence.",
        "Use 5-4-3-2-1 grounding to reconnect to the present moment.",
        "Self-compassion lowers stress. Speak to yourself kindly.",
        "Tiny actions reduce overwhelm — choose one 2-minute task.",
    ]
    await message.answer(f"💡 Quick tip: {random.choice(tips)}")


async def _open_section(message: Message, section: str, label: str):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=f"Open {label}", web_app=WebAppInfo(url=mini_app_url(section)))]]
    )
    await message.answer("Opening Mini App:", reply_markup=kb)


@tg_router.message(Command("breathe"))
async def cmd_breathe(message: Message):
    await _open_section(message, "breathe", "Breathing")


@tg_router.message(Command("grounding"))
async def cmd_grounding(message: Message):
    await _open_section(message, "calm", "Grounding")


@tg_router.message(Command("journal"))
async def cmd_journal(message: Message):
    await _open_section(message, "journal", "Journal")


@tg_router.message(Command("checkin"))
async def cmd_checkin(message: Message):
    await _open_section(message, "home", "Check-In")


async def _send_daily_reminders():
    if not _bot:
        return
    from database import get_db
    db = get_db()
    users = db.execute("SELECT telegram_id, first_name FROM users").fetchall()
    for user in users:
        try:
            name = user["first_name"] or "there"
            await _bot.send_message(
                chat_id=user["telegram_id"],
                text=f"Hi {name} 🌿\nFriendly reminder: complete your daily check-in and a 2-minute breathing reset.",
                reply_markup=main_keyboard(),
            )
        except Exception as e:
            logger.warning(f"Reminder failed for {user['telegram_id']}: {e}")


async def _reminder_loop():
    while True:
        now = datetime.now(timezone.utc)
        next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        await asyncio.sleep((next_run - now).total_seconds())
        await _send_daily_reminders()


async def setup_bot():
    global _bot, _dp
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set — bot disabled")
        return

    _bot = Bot(token=token)
    _dp = Dispatcher()
    _dp.include_router(tg_router)

    try:
        await _bot.set_my_commands([
            BotCommand(command="start",     description="Open support bot and Mini App"),
            BotCommand(command="tip",       description="Get a quick anxiety tip"),
            BotCommand(command="breathe",   description="Open breathing exercises"),
            BotCommand(command="grounding", description="Open grounding tools"),
            BotCommand(command="journal",   description="Open CBT journal prompts"),
            BotCommand(command="checkin",   description="Open daily check-in"),
        ])
        if os.getenv("APP_BASE_URL"):
            await _bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="Open Mini App",
                    web_app=WebAppInfo(url=mini_app_url("home")),
                )
            )
    except Exception as e:
        logger.error(f"Bot config error: {e}")

    asyncio.create_task(_reminder_loop())
    logger.info("Bot ready: @%s", (await _bot.get_me()).username)


async def set_webhook():
    if not _bot:
        return
    url = os.getenv("BOT_WEBHOOK_URL")
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if not url:
        return
    await _bot.set_webhook(url, secret_token=secret)
    logger.info("Webhook set: %s", url)


@webhook_router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(default=""),
):
    expected = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    if expected and x_telegram_bot_api_secret_token != expected:
        return Response(status_code=401)
    if not _dp or not _bot:
        return Response(status_code=503)
    update = Update.model_validate(await request.json())
    await _dp.feed_update(_bot, update)
    return Response(status_code=200)
