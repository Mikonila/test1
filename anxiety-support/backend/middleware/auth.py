import hashlib
import hmac
import json
import os
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException
from database import upsert_user


def verify_init_data(init_data: str, bot_token: str) -> dict | None:
    if not init_data or not bot_token:
        return None
    params = dict(parse_qsl(init_data, strict_parsing=True))
    hash_ = params.pop("hash", None)
    if not hash_:
        return None
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed, hash_):
        return None
    user_raw = params.get("user")
    if not user_raw:
        return None
    try:
        return json.loads(user_raw)
    except Exception:
        return None


def get_current_user(
    x_telegram_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    tg_user = verify_init_data(x_telegram_init_data, token)

    if not tg_user:
        if os.getenv("APP_ENV") != "production" and x_dev_user_id:
            tg_user = {
                "id": x_dev_user_id,
                "username": "dev_user",
                "first_name": "Dev",
                "last_name": "User",
            }
        else:
            raise HTTPException(status_code=401, detail="Unauthorized telegram session")

    return upsert_user(tg_user)
