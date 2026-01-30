import json
import secrets
from typing import Optional, Dict, Any

from app.common.redis_client import get_redis

ONBOARDING_TTL_SEC = 60 * 30  # 30분


def _ob_key(token: str) -> str:
    return f"onboarding:{token}"


def issue_onboarding_token(payload: dict) -> str:
    token = "ob_" + secrets.token_urlsafe(24)
    r = get_redis()
    r.set(
        _ob_key(token), json.dumps(payload, ensure_ascii=False), ex=ONBOARDING_TTL_SEC
    )
    return token


def read_onboarding_token(token: str) -> Optional[Dict[str, Any]]:
    if not token or not token.startswith("ob_"):
        return None
    r = get_redis()
    raw = r.get(_ob_key(token))
    if not raw:
        return None
    try:
        # redis_client가 decode_responses=False면 bytes일 수 있음
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        return json.loads(raw)
    except Exception:
        return None


def write_onboarding_token(token: str, payload: dict) -> None:
    r = get_redis()
    r.set(
        _ob_key(token), json.dumps(payload, ensure_ascii=False), ex=ONBOARDING_TTL_SEC
    )


def delete_onboarding_token(token: str) -> None:
    r = get_redis()
    r.delete(_ob_key(token))
