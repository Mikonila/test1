import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from bot import setup_bot, set_webhook, webhook_router
from database import init_db
from routes.api import router as api_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Database initialised")
    await setup_bot()
    await set_webhook()
    yield
    logger.info("Shutting down")


app = FastAPI(title="Serenity Anxiety Support", lifespan=lifespan)

app.include_router(webhook_router)
app.include_router(api_router, prefix="/api")

static_dir = Path(__file__).parent / "public"
static_dir.mkdir(exist_ok=True)
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
