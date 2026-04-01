import hashlib
import hmac
import json
import os
from urllib.parse import parse_qsl, unquote

from fastapi import Header, HTTPException


def _verify_initdata(init_data: str) -> dict:
    """Verify Telegram WebApp initData and return the user dict."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    params = dict(parse_qsl(unquote(init_data), keep_blank_values=True))
    hash_val = params.pop("hash", "")

    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed = hmac.new(secret_key, data_check.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed, hash_val):
        raise HTTPException(status_code=401, detail="Invalid Telegram initData")

    return json.loads(params.get("user", "{}"))


async def get_current_user(
    x_telegram_initdata: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
) -> dict:
    """FastAPI dependency — resolves authenticated user."""
    from database import upsert_user

    app_env = os.getenv("APP_ENV", "development")

    if x_telegram_initdata:
        tg_user = _verify_initdata(x_telegram_initdata)
    elif app_env != "production" and x_dev_user_id:
        # Dev fallback: pass any numeric ID via x-dev-user-id header
        tg_user = {"id": int(x_dev_user_id), "first_name": "DevUser", "username": "dev"}
    else:
        raise HTTPException(status_code=401, detail="Unauthorized")

    db_id = upsert_user(tg_user)
    return {
        "db_id": db_id,
        "tg_id": tg_user["id"],
        "first_name": tg_user.get("first_name", ""),
        "username": tg_user.get("username", ""),
    }
