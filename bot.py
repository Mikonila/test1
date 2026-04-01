import logging
import os
import random

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import BotCommand, MenuButtonWebApp, Message, Update, WebAppInfo
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
WEBHOOK_PATH = "/telegram/webhook"

TIPS = [
    "Anxiety is a body alarm. Slow breathing helps your nervous system feel safe.",
    "Thoughts are not facts — pause and test before believing them.",
    "Name 5 things you can see to reconnect to the present moment.",
    "Self-compassion lowers stress. Speak to yourself kindly.",
    "Tiny actions reduce overwhelm. Choose one 2-minute task and start.",
]

bot: Bot | None = None
dp = Dispatcher()
tg_router = Router()
dp.include_router(tg_router)
webhook_router = APIRouter()


# ── Bot commands ──────────────────────────────────────────────────────────────

@tg_router.message(Command("start"))
async def cmd_start(message: Message):
    name = message.from_user.first_name or "there"
    app_url = _app_url()
    text = (
        f"Hi {name}! 🌿 I'm Serenity — your anxiety support companion.\n\n"
        "I use evidence-based techniques: CBT, breathing, grounding, and journaling "
        "to help you feel calmer.\n\n"
    )
    if app_url:
        text += "Tap the button below to open the app 👇"
    await message.answer(text)


@tg_router.message(Command("breathe"))
async def cmd_breathe(message: Message):
    await message.answer(
        "🌬 Box breathing (4-4-4-4):\n\n"
        "Inhale 4s → Hold 4s → Exhale 4s → Hold 4s\n\n"
        "Open the app for a guided session with a visual timer."
    )


@tg_router.message(Command("tip"))
async def cmd_tip(message: Message):
    await message.answer(f"💡 {random.choice(TIPS)}")


@tg_router.message(Command("journal"))
async def cmd_journal(message: Message):
    await message.answer("📓 Open the app → Journal tab to write with CBT prompts.")


# ── Setup helpers ─────────────────────────────────────────────────────────────

def _app_url() -> str:
    url = os.getenv("APP_BASE_URL", "").rstrip("/")
    if not url:
        domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
        if domain:
            url = f"https://{domain}"
    return url


async def setup_bot() -> None:
    global bot
    bot = Bot(token=BOT_TOKEN)
    await bot.set_my_commands([
        BotCommand(command="start",   description="Open anxiety support app"),
        BotCommand(command="breathe", description="Breathing exercise guide"),
        BotCommand(command="tip",     description="Get a quick CBT tip"),
        BotCommand(command="journal", description="Open journal"),
    ])
    url = _app_url()
    if url:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Open App", web_app=WebAppInfo(url=url))
        )
        logger.info("Menu button set to %s", url)


async def set_webhook() -> None:
    url = _app_url()
    if not url or not bot:
        logger.warning("APP_BASE_URL not set — webhook skipped")
        return
    webhook_url = url + WEBHOOK_PATH
    await bot.set_webhook(webhook_url, secret_token=WEBHOOK_SECRET)
    logger.info("Webhook registered: %s", webhook_url)


# ── Webhook endpoint ──────────────────────────────────────────────────────────

@webhook_router.post(WEBHOOK_PATH)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(default=""),
):
    if WEBHOOK_SECRET and x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    data = await request.json()
    update = Update(**data)
    await dp.feed_update(bot, update)
    return JSONResponse({"ok": True})
