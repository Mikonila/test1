import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from bot import setup_bot, set_webhook, webhook_router
from routes.api import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await setup_bot()
    await set_webhook()
    yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)


@app.get("/health")
async def health():
    return {"ok": True, "service": "anxiety-support"}


app.include_router(webhook_router)
app.include_router(api_router, prefix="/api")

static_dir = Path(__file__).parent / "public"
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
