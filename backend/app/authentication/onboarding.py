# app/auth/onboarding.py
import secrets
from datetime import timedelta
from django.utils import timezone
from app.common.redis_client import get_redis

ONBOARDING_TTL_SEC = 60 * 30  # 30분


def _key(token: str) -> str:
    return f"onboarding:{token}"


def issue_onboarding_token(payload: dict) -> str:
    token = "ob_" + secrets.token_urlsafe(24)
    r = get_redis()
    data = payload.copy()
    data["issuedAt"] = timezone.now().isoformat()
    r.set(_key(token), str(data), ex=ONBOARDING_TTL_SEC)
    return token


def get_onboarding_payload(token: str) -> dict | None:
    if not token or not token.startswith("ob_"):
        return None
    r = get_redis()
    raw = r.get(_key(token))
    if not raw:
        return None
    # 해커톤: eval 대신 json 쓰는 게 정석인데, 빠르게 가려면 json으로 저장/로드 추천
    # 여기서는 raw가 str(dict)라고 가정하면 안 좋음 -> 아래 2)에서 json으로 바꿔줄게
    return None
